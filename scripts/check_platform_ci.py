"""Parallel local CI gate with an explicit 240-second check budget."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import time


def run(arguments):
    return subprocess.run([sys.executable, *arguments], timeout=240).returncode


def main():
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(
            pool.map(
                run,
                [
                    [
                        "-m",
                        "ruff",
                        "check",
                        "agent_platform",
                        "scripts/check_platform_ci.py",
                        "scripts/check_platform_coverage.py",
                        "scripts/smoke_platform_m6.py",
                    ],
                    ["-m", "mypy"],
                    [
                        "-m",
                        "coverage",
                        "run",
                        "--branch",
                        "--source=agent_platform,reasoning_agent.custom2.staged_answer_extractor",
                        "-m",
                        "pytest",
                        "-q",
                    ],
                ],
            )
        )
    if any(results) or time.monotonic() - started > 240:
        raise SystemExit(1)
    Path("sample_outputs").mkdir(exist_ok=True)
    if run(["-m", "coverage", "json", "-o", "sample_outputs/platform_ci_coverage.json"]):
        raise SystemExit(1)
    raise SystemExit(
        run(
            [
                "scripts/check_platform_coverage.py",
                "--report",
                "sample_outputs/platform_ci_coverage.json",
            ]
        )
    )


if __name__ == "__main__":
    main()
