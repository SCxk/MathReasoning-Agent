"""Actual offline embedding/indexing with a clearly fake answer for chat QA only."""

import argparse
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn

from agent_platform.app import create_app
from agent_platform.rag.embedding import QwenEmbedding
from agent_platform.rag.service import DocumentService
from agent_platform.redis_store import RedisTaskStore
from agent_platform.runtime import RuntimeResult
from serve_platform_m5_demo import RAGProtocolDemo


class ChatRAGDemo(RAGProtocolDemo):
    async def run(self, context):
        await super().run(context)
        chunks = [part for call in context.tool_calls.values()
                  for part in (call.get("result") or {}).get("value", {}).get("passages", [])]
        citation = f" [{chunks[0]['chunk_id']}]" if chunks else ""
        return RuntimeResult("Fake answer: citation display fixture, not a mathematical solution."
                             + citation + "\n\n$x^2$: formula rendering fixture.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8008)
    parser.add_argument("--rag-dir", type=Path, required=True)
    parser.add_argument("--embedding-model-dir", type=Path, default=Path("strategyrag/Qwen3-Embedding-0.6B"))
    parser.add_argument("--redis-url-env", required=True)
    parser.add_argument("--namespace", required=True)
    args = parser.parse_args()
    import torch
    from redis import Redis
    torch.set_num_threads(4)
    documents = DocumentService(args.rag_dir, QwenEmbedding(args.embedding_model_dir))
    store = RedisTaskStore(Redis.from_url(os.environ[args.redis_url_env], decode_responses=True,
                                         socket_timeout=1), namespace=args.namespace)
    uvicorn.run(create_app(store=store, documents=documents, runtime=ChatRAGDemo(documents),
                          rate_limits=False), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
