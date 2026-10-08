"""Trusted deployment bootstrap; model clients are exclusively injected providers."""

import importlib
from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Any, cast

from redis import Redis
from redis.exceptions import RedisError

from agent_platform.app import create_app
from agent_platform.database import database, migrate
from agent_platform.distributed import RedisModelPermits, RedisRateLimiter
from agent_platform.event_transport import EventTransport
from agent_platform.metrics import install_metrics
from agent_platform.models import PlatformError
from agent_platform.operations import OperationalMonitor
from agent_platform.postgres_store import PostgresTaskStore
from agent_platform.queue_service import QueueTaskService
from agent_platform.runtime import AgentRuntime, FakeRuntime


def trusted_provider(spec):
    if not spec or ":" not in spec:
        raise ValueError("injected_client_provider_required")
    module, function = spec.split(":", 1)
    return getattr(importlib.import_module(module), function)()


class Deployment:
    def __init__(self, *, worker=False):
        self.namespace = os.environ.get("MATHS_NAMESPACE", "maths")
        self.engine, self.metadata = database(os.environ["MATHS_DATABASE_URL"], self.namespace)
        self.store = PostgresTaskStore(self.engine, self.metadata)
        self.redis = Redis.from_url(
            os.environ["MATHS_REDIS_URL"],
            decode_responses=True,
            socket_timeout=1,
            socket_connect_timeout=1,
        )
        self.documents: Any = None
        self.runtime: AgentRuntime
        from qdrant_client import QdrantClient

        self.qdrant = QdrantClient(url=os.environ["MATHS_QDRANT_URL"], timeout=5)
        if os.environ.get("MATHS_RAG_ENABLED", "false").lower() == "true":
            from agent_platform.postgres_documents import PostgresDocumentCatalog, ReadOnlyDocuments
            from agent_platform.rag.embedding import QwenEmbedding
            from agent_platform.rag.index import HybridIndex
            from agent_platform.rag.service import DocumentService

            catalog = PostgresDocumentCatalog(self.engine, self.metadata, read_only=worker)
            encoder = QwenEmbedding(Path(os.environ["MATHS_EMBEDDING_MODEL_DIR"]))
            if worker:
                self.documents = ReadOnlyDocuments(
                    HybridIndex(self.qdrant, catalog, encoder, lock=catalog.index_lock)
                )
            else:
                self.documents = DocumentService(
                    os.environ["MATHS_RAG_DIR"], encoder, client=self.qdrant, catalog=catalog
                )
        mode = os.environ.get("MATHS_RUNTIME", "fake")
        if mode == "langgraph":
            from agent_platform.graph_runtime import LangGraphRuntime
            from agent_platform.tools.local import LocalTools
            from agent_platform.tools.registry import ToolRegistry
            from agent_platform.tools.mcp_client import SdkMCPClient

            client = trusted_provider(os.environ.get("MATHS_CLIENT_PROVIDER"))
            identity = os.environ.get("MATHS_CLIENT_IDENTITY")
            if not identity:
                raise ValueError("versioned_client_identity_required")
            mcp = (
                SdkMCPClient()
                if os.environ.get("MATHS_MCP_TOOLS", "false").lower() == "true"
                else None
            )
            graph = LangGraphRuntime(
                client,
                client_identity=identity,
                tools=ToolRegistry(LocalTools(documents=self.documents), mcp=mcp),
                function_calling=os.environ.get("MATHS_FUNCTION_CALLING", "auto"),
            )
            graph.permits = RedisModelPermits(
                self.redis,
                self.namespace,
                reserve_recovery=os.environ.get("MATHS_WORKER_GROUP", "reasoning") != "recovery",
            )
            self.runtime = graph
        elif mode == "fake":
            self.runtime = FakeRuntime()
        else:
            raise ValueError("invalid_runtime")

    def ready(self, *, workers=False):
        self.store.ready()
        try:
            self.redis.ping()
            if (
                cast(dict, self.redis.info("persistence")).get("aof_enabled") != 1
                or cast(dict, self.redis.info("persistence")).get("aof_last_write_status") != "ok"
                or cast(dict, self.redis.config_get("appendfsync")).get("appendfsync") != "always"
            ):
                raise PlatformError("redis_aof_always_required", 503)
            if workers and any(
                not self.redis.exists(f"{self.namespace}:worker:{group}")
                for group in ("reasoning", "recovery")
            ):
                raise PlatformError("workers_unavailable", 503)
            if self.qdrant:
                self.qdrant.get_collections()
        except RedisError:
            raise PlatformError("redis_unavailable", 503) from None
        except PlatformError:
            raise
        except Exception:
            raise PlatformError("vector_store_unavailable", 503) from None


def application():
    from agent_platform.celery_worker import celery_app

    deployment = Deployment()
    transport = EventTransport(deployment.redis, deployment.store, deployment.namespace)
    service = QueueTaskService(deployment.store, deployment.runtime, celery_app, transport)
    operations = OperationalMonitor(service,
        document_root=deployment.documents.root if deployment.documents is not None else None,
        prometheus_url=os.environ.get("MATHS_PROMETHEUS_URL") or None)
    app = create_app(
        store=deployment.store,
        runtime=deployment.runtime,
        task_service=service,
        documents=deployment.documents,
        limiter=RedisRateLimiter(deployment.redis, deployment.namespace),
        event_transport=transport,
        readiness=lambda: deployment.ready(workers=True),
        operational_health=operations.summary,
    )
    install_metrics(app, deployment.store, operations=operations)
    app.state.operations = operations
    app.state.deployment = deployment
    lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def resources(app):
        try:
            async with lifespan(app):
                await operations.start()
                yield
        finally:
            await operations.stop()
            deployment.qdrant.close()
            deployment.redis.close()
            deployment.engine.dispose()

    app.router.lifespan_context = resources
    return app


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("migrate", "api"))
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "migrate":
        engine, metadata = database(
            os.environ["MATHS_DATABASE_URL"], os.environ.get("MATHS_NAMESPACE", "maths")
        )
        try:
            migrate(engine, metadata)
        finally:
            engine.dispose()
    else:
        import uvicorn

        uvicorn.run(application(), host="0.0.0.0", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
