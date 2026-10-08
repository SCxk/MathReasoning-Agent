import argparse
import importlib
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the math reasoning Web backend.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--runtime", choices=("fake", "langgraph"), default="fake")
    parser.add_argument("--client-provider", help="Trusted module:function returning the injected chat client")
    parser.add_argument("--client-identity", help="Versioned provider/model identity for checkpoint compatibility")
    parser.add_argument("--redis-url-env", help="Environment variable containing the Redis URL")
    parser.add_argument("--namespace", default="maths:m3")
    parser.add_argument("--mcp-tools", action="store_true", help="Use the private SDK stdio server for search and verification")
    parser.add_argument("--function-calling", choices=("auto", "native", "json", "off"), default="auto")
    parser.add_argument("--rag-dir", help="Private durable document directory (single process)")
    parser.add_argument("--embedding-model-dir", help="Offline Qwen3-Embedding-0.6B weights")
    parser.add_argument("--embedding-threads", type=int, default=4, help="CPU threads for local embeddings")
    parser.add_argument("--question-dir", help="Private durable question-attachment directory (single owner)")
    args = parser.parse_args()
    from agent_platform.app import create_app

    runtime, store, documents = None, None, None
    if args.rag_dir:
        if not args.embedding_model_dir:
            parser.error("RAG requires --embedding-model-dir")
        if not 1 <= args.embedding_threads <= 16:
            parser.error("embedding threads must be between 1 and 16")
        import torch
        torch.set_num_threads(args.embedding_threads)
        from pathlib import Path
        from agent_platform.rag.embedding import QwenEmbedding
        from agent_platform.rag.service import DocumentService
        documents = DocumentService(args.rag_dir, QwenEmbedding(Path(args.embedding_model_dir)))
    if args.runtime == "langgraph":
        if not args.client_provider:
            parser.error("langgraph requires an explicitly injected --client-provider")
        from agent_platform.graph_runtime import LangGraphRuntime

        try:
            module, function = args.client_provider.split(":", 1)
            client = getattr(importlib.import_module(module), function)()
        except Exception:
            parser.error("client provider failed")
        from agent_platform.tools.registry import ToolRegistry
        from agent_platform.tools.local import LocalTools
        mcp = None
        if args.mcp_tools:
            from agent_platform.tools.mcp_client import SdkMCPClient
            mcp = SdkMCPClient()
        runtime = LangGraphRuntime(client=client, client_identity=args.client_identity,
                                   tools=ToolRegistry(LocalTools(documents=documents), mcp=mcp), function_calling=args.function_calling)
    if args.redis_url_env:
        from redis import Redis
        from agent_platform.redis_store import RedisTaskStore

        url = os.environ.get(args.redis_url_env)
        if not url:
            parser.error("Redis URL environment variable is not set")
        store = RedisTaskStore(Redis.from_url(url, decode_responses=True,
                                            socket_timeout=1, socket_connect_timeout=1),
                               namespace=args.namespace)
    uvicorn.run(create_app(runtime=runtime, store=store, documents=documents, question_dir=args.question_dir), host="127.0.0.1", port=args.port,
                access_log=False)


if __name__ == "__main__":
    main()
