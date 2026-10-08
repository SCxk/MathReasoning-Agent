"""Translate and embed AUTO-KNOWLEDGE module notes from a skill directory.

This intentionally leaves a supplied relative path out (for example the
already-indexed discrete-mathematics skill) so a prior source is never asked of
the client or appended twice.  Every successful response is persisted as JSONL
before its vector is generated, allowing safe restart after interruptions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.local_env import load_local_env
from scripts.translate_and_append_knowledge_templates import (
    DEFAULT_TEMPLATES,
    DEFAULT_TRANSLATIONS,
    append_embeddings,
    read_completed,
    translate_one,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument(
        "--exclude-relative", action="append", default=[],
        help="Relative *skill.md path to leave untouched; repeatable",
    )
    parser.add_argument(
        "--translations-jsonl", type=Path,
        default=DEFAULT_TRANSLATIONS.parent / "translated_skill_module_templates.jsonl",
    )
    parser.add_argument(
        "--templates-json", type=Path,
        default=DEFAULT_TEMPLATES.parent / "translated_skill_module_templates.json",
    )
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args()


def extract_modules(path: Path, root: Path) -> list[tuple[str, str, str]]:
    text = path.read_text(encoding="utf-8")
    marker = "<!-- AUTO-KNOWLEDGE-BEGIN"
    if marker not in text:
        return []
    tail = text[text.index(marker) :]
    end_marker = "<!-- AUTO-KNOWLEDGE-END"
    if end_marker in tail:
        tail = tail[:tail.index(end_marker)]
    matches = list(re.finditer(r"^##\s*模块速查：\s*(.+?)\s*$", tail, flags=re.MULTILINE))
    relative = path.relative_to(root).as_posix()
    result: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(tail)
        title = match.group(1).strip()
        body = tail[match.end() : end].strip()
        if body:
            # The key is source-qualified to prevent collisions between subjects.
            key = f"{relative} :: {title}"
            result.append((key, title, body))
    return result


def load_modules(root: Path, excluded: set[str]) -> list[tuple[str, str, str]]:
    modules: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*skill.md")):
        if path.relative_to(root).as_posix() not in excluded:
            modules.extend(extract_modules(path, root))
    return modules


def run_translations(
    modules: list[tuple[str, str, str]], output_path: Path, max_concurrency: int
) -> list[dict[str, Any]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = read_completed(output_path)
    pending = [(key, title, body) for key, title, body in modules if key not in completed]
    positions = {key: number for number, (key, _, _) in enumerate(modules, start=1)}
    print(f"Reusing {len(modules) - len(pending)} completed translations; requesting {len(pending)}.", flush=True)
    with output_path.open("a", encoding="utf-8") as output:
        with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            futures = [
                executor.submit(
                    translate_one, key,
                    f"Source module title: {title}\n\n{body}",
                )
                for key, title, body in pending
            ]
            for future in as_completed(futures):
                key, record = future.result()
                print(f"[{positions[key]}/{len(modules)}] Translation completed: {key}", flush=True)
                if record["status"] == "ok":
                    completed[key] = record["template"]
                    record["template"]["source_document"] = key.split(" :: ", 1)[0]
                    print(json.dumps(record["template"], ensure_ascii=False, indent=2), flush=True)
                else:
                    print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                output.flush()
    return [completed[key] for key, _, _ in modules if key in completed]


def main() -> None:
    args = parse_args()
    if args.max_concurrency < 1 or args.batch_size < 1:
        raise ValueError("--max-concurrency and --batch-size must be positive")
    load_local_env()
    root = args.source_dir.resolve()
    modules = load_modules(root, set(args.exclude_relative))
    if not modules:
        raise ValueError("No AUTO-KNOWLEDGE module headings found after exclusions")
    print(f"Found {len(modules)} modules to translate.", flush=True)
    templates = run_translations(modules, args.translations_jsonl, args.max_concurrency)
    args.templates_json.parent.mkdir(parents=True, exist_ok=True)
    args.templates_json.write_text(json.dumps(templates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(templates)} successful English templates to {args.templates_json}", flush=True)
    append_embeddings(templates, args.batch_size)


if __name__ == "__main__":
    main()
