"""Analyze a problem through the local runner client, then retrieve strategies.

This is a local demonstration.  Production code should call
``StrategyRetriever.retrieve_for_problem(injected_client, problem)`` with the
platform-provided client rather than constructing a new client.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm_client import InternChatClient
from scripts.local_env import load_local_env
from reasoning_agent.strategy_retrieval import (
    RAW_SCORE_WEIGHT,
    STRUCTURE_SCORE_WEIGHT,
    StructuredRetrievalOutputError,
    StrategyRetriever,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problem", help="Raw mathematical problem")
    parser.add_argument("--top-k", "-k", type=int, default=5)
    args = parser.parse_args()
    load_local_env()
    client = InternChatClient()
    try:
        retrieved = StrategyRetriever().retrieve_for_problem(
            client, args.problem, top_k=args.top_k
        )
    except StructuredRetrievalOutputError as exc:
        print("Original problem:")
        print(args.problem)
        print("\nStructured model output (parse failed):")
        print(exc.raw_output)
        raise
    print("Original problem:")
    print(args.problem)
    print("\nStructured model output:")
    print(retrieved["structured_model_output"])
    print("Retrieval text:")
    print(retrieved["retrieval_text"])
    print(
        "\nScoring: "
        f"{RAW_SCORE_WEIGHT:.1f} × raw_score + "
        f"{STRUCTURE_SCORE_WEIGHT:.1f} × structure_score"
    )
    print("\nTop strategies:")
    for rank, item in enumerate(retrieved["results"], start=1):
        complete_item = {
            "rank": rank,
            "idx": item["id"],
            "score": item["score"],
            "strategy": item,
        }
        print(json.dumps(complete_item, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
