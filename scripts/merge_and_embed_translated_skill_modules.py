"""Merge completed skill-module translations and append their local embeddings."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.translate_and_append_knowledge_templates import DATA_DIR, append_embeddings


def successful_templates(path: Path) -> list[dict]:
    result: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") == "ok" and isinstance(row.get("template"), dict):
            result.append(row["template"])
    return result


def main() -> None:
    remote = successful_templates(DATA_DIR / "translated_skill_module_templates.jsonl")
    dialogue = successful_templates(DATA_DIR / "dialogue_translated_remaining_templates.jsonl")
    by_key: dict[str, dict] = {}
    for template in remote + dialogue:
        key = str(template.get("source_module_title_zh", ""))
        if not key:
            raise ValueError("A template has no source_module_title_zh")
        if key in by_key:
            raise ValueError(f"Duplicate translation key: {key}")
        by_key[key] = template
    templates = list(by_key.values())
    if len(templates) != 108:
        raise ValueError(f"Expected 108 translated non-discrete modules, found {len(templates)}")
    output = DATA_DIR / "translated_skill_module_templates.json"
    output.write_text(json.dumps(templates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Merged {len(remote)} client and {len(dialogue)} dialogue translations.")
    append_embeddings(templates, batch_size=16)


if __name__ == "__main__":
    main()
