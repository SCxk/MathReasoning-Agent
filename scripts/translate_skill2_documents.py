"""Faithfully translate all Markdown documents under skill2 into skill2_en.

Original files are read-only.  Translated chunks are checkpointed to JSONL and
assembled into matching paths only after all chunks of an individual document
have completed, so the process can be restarted safely.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import InternChatClient
from scripts.local_env import load_local_env


PROMPT = """Translate the following Markdown segment from Chinese to English.

This is a faithful technical and mathematical translation, not a summary or a
rewrite. Preserve every mathematical formula, symbolic expression, parameter,
numeric value, dimension, calibration value, hypothesis, boundary condition,
algorithmic requirement, computational limitation, warning, and common pitfall.
Never generalize away a source-specific formula or replace it with a vague
description. Preserve Markdown structure, headings, lists, tables, links,
inline code, code fences, LaTex delimiters and the contents of code blocks.
Translate prose only. Do not add, remove, reorder, summarize, solve, or infer
anything. Return ONLY the translated Markdown segment, with no code fence around
the whole response and no commentary.

Markdown segment:
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "skill2")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "skill2_en")
    parser.add_argument(
        "--checkpoint", type=Path,
        default=ROOT / "strategy_data" / "skill2_translation_checkpoint.jsonl",
    )
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--max-concurrency", type=int, default=2)
    return parser.parse_args()


def split_markdown(text: str, maximum: int) -> list[str]:
    """Split only at line boundaries, avoiding an open fenced-code block."""
    lines = text.splitlines(keepends=True)
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    fenced = False
    for line in lines:
        is_fence = line.lstrip().startswith("```") or line.lstrip().startswith("~~~")
        if current and length + len(line) > maximum and not fenced:
            chunks.append("".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line)
        if is_fence:
            fenced = not fenced
    if current:
        chunks.append("".join(current))
    return chunks


def clean_response(response: str) -> str:
    value = response.strip()
    if value.startswith("```") and value.endswith("```"):
        value = value.split("\n", 1)[1] if "\n" in value else ""
        value = value.rsplit("```", 1)[0]
    return value


def load_completed(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") == "ok":
            result[str(row["key"])] = str(row["translation"])
    return result


def translate_one(key: str, segment: str) -> tuple[str, dict]:
    try:
        client = InternChatClient()
        response = str(client.chat(
            [{"role": "user", "content": PROMPT + segment}],
            temperature=0.0, max_tokens=7000, thinking_mode=False,
        ))
        translation = clean_response(response)
        if not translation:
            raise ValueError("empty translation")
        return key, {"key": key, "status": "ok", "translation": translation}
    except Exception as exc:
        return key, {"key": key, "status": "error", "error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    args = parse_args()
    if args.max_chars < 500 or args.max_concurrency < 1:
        raise ValueError("invalid chunk/concurrency configuration")
    load_local_env()
    source = args.source_dir.resolve()
    files = sorted(source.rglob("*.md"))
    tasks: list[tuple[str, Path, int, str]] = []
    all_chunks: dict[Path, list[str]] = {}
    for path in files:
        chunks = split_markdown(path.read_text(encoding="utf-8"), args.max_chars)
        all_chunks[path] = chunks
        relative = path.relative_to(source).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        for number, chunk in enumerate(chunks):
            tasks.append((f"{relative}:{digest}:{number}", path, number, chunk))

    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    completed = load_completed(args.checkpoint)
    pending = [(key, path, number, chunk) for key, path, number, chunk in tasks if key not in completed]
    print(f"Documents={len(files)}, chunks={len(tasks)}, reusing={len(tasks)-len(pending)}, requesting={len(pending)}", flush=True)
    with args.checkpoint.open("a", encoding="utf-8") as checkpoint:
        with ThreadPoolExecutor(max_workers=args.max_concurrency) as executor:
            futures = [executor.submit(translate_one, key, chunk) for key, _, _, chunk in pending]
            for future in as_completed(futures):
                key, row = future.result()
                if row["status"] == "ok":
                    completed[key] = row["translation"]
                print(f"{'Translated' if row['status'] == 'ok' else 'Failed'}: {key}", flush=True)
                checkpoint.write(json.dumps(row, ensure_ascii=False) + "\n")
                checkpoint.flush()

    written = 0
    for path, chunks in all_chunks.items():
        relative = path.relative_to(source).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        keys = [f"{relative}:{digest}:{number}" for number in range(len(chunks))]
        if not all(key in completed for key in keys):
            continue
        destination = args.output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("".join(completed[key] for key in keys), encoding="utf-8")
        written += 1
    print(f"Assembled {written}/{len(files)} translated documents in {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
