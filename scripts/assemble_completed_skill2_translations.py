"""Assemble only fully checkpointed skill2 translations without model calls."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "strategy_data" / "skill2_translation_checkpoint.jsonl"
OUTPUT = ROOT / "skill2_en"


def main() -> None:
    groups: dict[tuple[str, str], dict[int, str]] = defaultdict(dict)
    for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") != "ok":
            continue
        match = re.fullmatch(r"(.+):([0-9a-f]+):(\d+)", str(row["key"]))
        if not match:
            continue
        relative, digest, index = match.groups()
        groups[(relative, digest)][int(index)] = str(row["translation"])
    written = 0
    for (relative, _), chunks in groups.items():
        indices = sorted(chunks)
        if indices != list(range(len(indices))):
            continue
        destination = OUTPUT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("".join(chunks[index] for index in indices), encoding="utf-8")
        written += 1
        print(f"Assembled: {relative}")
    print(f"Assembled {written} fully checkpointed document(s).")


if __name__ == "__main__":
    main()
