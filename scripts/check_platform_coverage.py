"""Enforce pure branch coverage per critical group, not statement/branch averages."""

import argparse
import json
from pathlib import Path


GROUPS = {
    "question_attachments": [
        "agent_platform/questions_parser.py",
        "agent_platform/question_batches.py",
    ],
    "routing": ["agent_platform/graph_runtime.py"],
    "checkpoint": [
        "agent_platform/storage.py",
        "agent_platform/redis_store.py",
        "agent_platform/postgres_store.py",
    ],
    "tool_error": [
        "agent_platform/tools/registry.py",
        "agent_platform/tools/function_calling.py",
        "agent_platform/tools/local.py",
        "agent_platform/tools/mcp_client.py",
    ],
    "answer_recovery": ["reasoning_agent/custom2/staged_answer_extractor.py"],
    "api": [
        "agent_platform/app.py",
        "agent_platform/service.py",
        "agent_platform/queue_service.py",
    ],
}


def check(raw, threshold=90):
    files = {name.replace("\\", "/"): value for name, value in raw["files"].items()}
    result = {}
    for group, names in GROUPS.items():
        summaries = [files[name]["summary"] for name in names]
        branches = sum(row["num_branches"] for row in summaries)
        covered = sum(row["covered_branches"] for row in summaries)
        percent = 100 * covered / branches if branches else 0
        result[group] = {
            "covered": covered,
            "branches": branches,
            "percent": percent,
            "pass": percent >= threshold,
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = check(json.loads(args.report.read_text(encoding="utf8")))
    print(json.dumps(result, indent=2))
    if not all(row["pass"] for row in result.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
