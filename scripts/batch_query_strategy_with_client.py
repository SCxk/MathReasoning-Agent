"""Run structured-query StrategyRAG retrieval for a JSONL problem set.

Each input line must contain at least ``idx`` and ``problem``.  Results are
printed to stdout only; no raw prompts, model responses, or retrieval logs are
persisted to disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm_client import InternChatClient
from scripts.local_env import load_local_env
from reasoning_agent.strategy_retrieval import (
    StructuredRetrievalOutputError,
    StrategyRetriever,
    analyze_problem_structure_with_raw,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument(
        "--exclude-jsonl", type=Path,
        help="Exclude every idx present in this JSONL file",
    )
    parser.add_argument(
        "--output-jsonl", type=Path,
        help="Append complete per-problem retrieval records to this file",
    )
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--max-concurrency", type=int, default=4)
    return parser.parse_args()


def load_problems(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row.get("problem"), str) or not row["problem"].strip():
            raise ValueError(f"Line {line_number} has no non-empty problem")
        rows.append(row)
    return rows


def analyze_one(row: dict[str, Any]) -> tuple[int, str, str | None, str | None]:
    client = InternChatClient()
    try:
        raw_output, retrieval_text = analyze_problem_structure_with_raw(client, row["problem"])
        return int(row["idx"]), raw_output, retrieval_text, None
    except StructuredRetrievalOutputError as exc:
        return int(row["idx"]), exc.raw_output, None, str(exc)
    except Exception as exc:  # Preserve one result line per input problem.
        return int(row["idx"]), "", None, f"{type(exc).__name__}: {exc}"


def main() -> None:
    args = parse_args()
    if args.top_k < 1 or args.max_concurrency < 1:
        raise ValueError("--top-k and --max-concurrency must be positive")
    load_local_env()
    rows = load_problems(args.input_jsonl)
    if args.exclude_jsonl:
        excluded = {int(row["idx"]) for row in load_problems(args.exclude_jsonl)}
        rows = [row for row in rows if int(row["idx"]) not in excluded]
    print(f"Retrieving Top-{args.top_k} strategies for {len(rows)} problems...", flush=True)

    output_file = None
    if args.output_jsonl:
        args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        output_file = args.output_jsonl.open("w", encoding="utf-8")
    retriever = StrategyRetriever()
    with ThreadPoolExecutor(max_workers=args.max_concurrency) as executor:
        futures = [executor.submit(analyze_one, row) for row in rows]
        for future in as_completed(futures):
            idx, raw_output, retrieval_text, error = future.result()
            print(f"Structured analysis completed: idx={idx}", flush=True)
            row = next(item for item in rows if int(item["idx"]) == idx)
            record: dict[str, Any] = {
                "idx": idx, "original_problem": row["problem"],
                "structured_model_output": raw_output, "retrieval_text": retrieval_text,
                "error": error, "results": [],
            }
            if not error and retrieval_text is not None:
                record["results"] = retriever.retrieve_hybrid(
                    row["problem"], retrieval_text, top_k=args.top_k
                )
            if output_file:
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                output_file.flush()
    if output_file:
        output_file.close()


if __name__ == "__main__":
    main()
