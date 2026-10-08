"""Retrieve the most relevant ReasonFlux strategies for a problem statement.

Example:
    python scripts/query_strategy_index.py \
      "How many integers are divisible by 3 or 5 below 100?" --top-k 5
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "strategy_data"
DEFAULT_MODEL_DIR = REPO_ROOT / "strategyrag" / "Qwen3-Embedding-0.6B"


def preferred_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Problem statement to retrieve strategies for")
    parser.add_argument("--top-k", "-k", type=int, default=5)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--device", default=preferred_device())
    parser.add_argument(
        "--include-steps",
        action="store_true",
        help="Include the detailed strategy steps in human-readable output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of formatted text",
    )
    return parser.parse_args()


def load_index(data_dir: Path) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    embeddings_path = data_dir / "strategy_embeddings.npy"
    metadata_path = data_dir / "strategy_meta.json"
    index_path = data_dir / "strategy_index.json"
    missing = [str(path) for path in (embeddings_path, metadata_path, index_path) if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing strategy index files: " + ", ".join(missing))

    vectors = np.load(embeddings_path, mmap_mode="r")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if vectors.ndim != 2 or vectors.dtype != np.float32:
        raise ValueError("strategy_embeddings.npy must be a two-dimensional float32 array")
    if len(metadata) != vectors.shape[0] or index.get("num_strategies") != vectors.shape[0]:
        raise ValueError("Embedding, metadata, and index row counts do not match")
    return vectors, metadata, index


def encode_query(model: SentenceTransformer, query: str) -> np.ndarray:
    embedding = model.encode(
        [query],
        prompt_name="query",
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    embedding = np.asarray(embedding[0], dtype=np.float32)
    norm = np.linalg.norm(embedding)
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("Query embedding is non-finite or zero")
    return embedding / norm


def retrieve(
    vectors: np.ndarray,
    metadata: list[dict[str, Any]],
    query_embedding: np.ndarray,
    top_k: int,
) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("--top-k must be positive")
    if query_embedding.shape != (vectors.shape[1],):
        raise ValueError(
            f"Query dimension {query_embedding.shape} does not match index dimension {vectors.shape[1]}"
        )
    count = min(top_k, vectors.shape[0])
    scores = np.asarray(vectors @ query_embedding)
    candidate_indices = np.argpartition(scores, -count)[-count:]
    ordered_indices = candidate_indices[np.argsort(scores[candidate_indices])[::-1]]
    results: list[dict[str, Any]] = []
    for row in ordered_indices:
        item = dict(metadata[int(row)])
        item["score"] = float(scores[int(row)])
        results.append(item)
    return results


def print_results(results: list[dict[str, Any]], *, include_steps: bool) -> None:
    for rank, item in enumerate(results, start=1):
        print(f"#{rank}  score={item['score']:.6f}  id={item['id']}")
        print(f"{item.get('name', '')}")
        print(f"Tags: {', '.join(item.get('tags', []))}")
        print(f"Description: {item.get('description', '')}")
        print("Applicable when: " + "; ".join(item.get("applicability", [])))
        if include_steps:
            print("Steps:")
            for step in item.get("steps", []):
                print(f"  - {step.get('step', '')}: {step.get('detail', '')}")
        print()


def main() -> None:
    args = parse_args()
    if not args.query.strip():
        raise ValueError("query must not be empty")
    vectors, metadata, _ = load_index(args.data_dir)
    if not args.model.is_dir():
        raise FileNotFoundError(f"Embedding model not found: {args.model}")
    model = SentenceTransformer(str(args.model), device=args.device)
    results = retrieve(vectors, metadata, encode_query(model, args.query), args.top_k)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_results(results, include_steps=args.include_steps)


if __name__ == "__main__":
    main()
