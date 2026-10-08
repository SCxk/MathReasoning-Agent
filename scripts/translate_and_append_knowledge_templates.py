"""Translate abstract Chinese strategy notes and append them to StrategyRAG.

The script is resumable: completed translations are kept in JSONL before any
embedding work begins.  ``--replace-existing`` precisely removes the previous
translations from both metadata and their aligned embedding rows, then rebuilds
them from the source.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_client import InternChatClient
from scripts.local_env import load_local_env
from reasoning_agent.strategy_retrieval import DEFAULT_MODEL_DIR, preferred_device
from scripts.build_strategy_embeddings import build_strategy_text


DATA_DIR = ROOT / "strategy_data"
DEFAULT_TRANSLATIONS = DATA_DIR / "translated_knowledge_templates.jsonl"
DEFAULT_TEMPLATES = DATA_DIR / "translated_knowledge_templates.json"

TRANSLATION_PROMPT = """You are curating a reusable mathematical strategy library.

Translate the Chinese module below into ONE complete English mathematical
strategy record.  It will be embedded for semantic retrieval by a math solver.

Preserve every mathematically meaningful detail from the source: formulas,
parameterized closed forms, dimensions, parity and boundary conditions,
small-scale calibration values, hypotheses, proof routes, implementation
requirements, caveats, and stated scope.  Translate faithfully; do not
generalize away a formula merely because it contains parameters or numbers.
Do not invent material absent from the source, and do not solve any new
problem beyond translating the strategy note.

Return ONLY one valid JSON object in exactly this shape:
{
  "name": "short English strategy name",
  "tags": ["2 to 6 concise English tags"],
  "description": "complete English translation of the core method, including formulas when present",
  "applicability": ["faithful English translation of each stated applicability signal"],
  "steps": [{"step": "English step", "detail": "complete translated detail, formulas included"}],
  "example": {"problem": "", "solution": ""}
}

Rules:
- English only in all generated fields, except mathematical notation.
- Preserve source-specific parameter values and symbolic expressions exactly
  when they are part of the strategy (for example a formula valid for a
  stated board dimension).  Do not omit calibration examples or a stated
  closed form.
- Do not mention this translation request or the Chinese source.
- Keep all stated warnings and restrictions in the description or steps.

Chinese module:
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Chinese knowledge-note text")
    parser.add_argument("--translations-jsonl", type=Path, default=DEFAULT_TRANSLATIONS)
    parser.add_argument("--templates-json", type=Path, default=DEFAULT_TEMPLATES)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument(
        "--replace-existing", action="store_true",
        help="Remove prior translations from this source class before rebuilding them",
    )
    return parser.parse_args()


def split_modules(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^##\s*模块速查：\s*(.+?)\s*$", text, flags=re.MULTILINE))
    if not matches:
        raise ValueError("No '## 模块速查：' headings found in source")
    modules: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(1).strip()
        body = text[match.end() : end].strip()
        if body:
            modules.append((title, body))
    return modules


def extract_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1)
    else:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end < start:
            raise ValueError("model response did not contain a JSON object")
        candidate = candidate[start : end + 1]
    result = json.loads(candidate)
    if not isinstance(result, dict):
        raise ValueError("model response JSON must be an object")
    return result


def validate_template(item: dict[str, Any]) -> dict[str, Any]:
    fields = ("name", "description", "tags", "applicability", "steps")
    missing = [field for field in fields if not item.get(field)]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))
    for field in ("name", "description"):
        if not isinstance(item[field], str):
            raise ValueError(f"{field} must be a string")
    for field in ("tags", "applicability", "steps"):
        if not isinstance(item[field], list):
            raise ValueError(f"{field} must be a list")
    item["tags"] = [str(value).strip() for value in item["tags"] if str(value).strip()]
    item["applicability"] = [str(value).strip() for value in item["applicability"] if str(value).strip()]
    item["steps"] = [
        {"step": str(step.get("step", "")).strip(), "detail": str(step.get("detail", "")).strip()}
        for step in item["steps"] if isinstance(step, dict)
    ]
    item["example"] = {"problem": "", "solution": ""}
    return item


def read_completed(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    completed: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") == "ok" and isinstance(row.get("template"), dict):
            completed[str(row["module_title_zh"])] = row["template"]
    return completed


def remove_existing_translations() -> int:
    """Remove exactly rows introduced by this script and their aligned vectors."""
    meta_path = DATA_DIR / "strategy_meta.json"
    vector_path = DATA_DIR / "strategy_embeddings.npy"
    index_path = DATA_DIR / "strategy_index.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    vectors = np.load(vector_path)
    if len(meta) != vectors.shape[0]:
        raise ValueError("strategy metadata and embedding matrix have different row counts")
    retained_indices = [
        index for index, item in enumerate(meta)
        if item.get("source") != "translated_chinese_knowledge_note"
    ]
    removed = len(meta) - len(retained_indices)
    if not removed:
        return 0
    retained_meta = [meta[index] for index in retained_indices]
    for index, item in enumerate(retained_meta):
        item["id"] = index
    np.save(vector_path, vectors[retained_indices].astype(np.float32))
    meta_path.write_text(json.dumps(retained_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["num_strategies"] = len(retained_meta)
    index.pop("translated_chinese_knowledge_templates", None)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return removed


def translate_one(title: str, body: str) -> tuple[str, dict[str, Any]]:
    raw = ""
    try:
        client = InternChatClient()
        raw = str(client.chat([{"role": "user", "content": TRANSLATION_PROMPT + body}], temperature=0.1, max_tokens=1800, thinking_mode=False))
        template = validate_template(extract_json_object(raw))
        template["source"] = "translated_chinese_knowledge_note"
        template["source_module_title_zh"] = title
        return title, {"module_title_zh": title, "status": "ok", "template": template}
    except Exception as exc:  # Keep the failed item resumable and visible.
        return title, {"module_title_zh": title, "status": "error", "error": f"{type(exc).__name__}: {exc}", "raw_model_output": raw}


def translate_modules(modules: list[tuple[str, str]], output_path: Path, max_concurrency: int) -> list[dict[str, Any]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = read_completed(output_path)
    pending = [(title, body) for title, body in modules if title not in completed]
    for position, (title, _) in enumerate(modules, start=1):
        if title in completed:
            print(f"[{position}/{len(modules)}] Reusing English translation: {title}", flush=True)
    positions = {title: position for position, (title, _) in enumerate(modules, start=1)}
    with output_path.open("a", encoding="utf-8") as output:
        with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            futures = [executor.submit(translate_one, title, body) for title, body in pending]
            for future in as_completed(futures):
                title, record = future.result()
                print(f"[{positions[title]}/{len(modules)}] Translation completed: {title}", flush=True)
                if record["status"] == "ok":
                    completed[title] = record["template"]
                    print(json.dumps(record["template"], ensure_ascii=False, indent=2), flush=True)
                else:
                    print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                output.flush()
    return [completed[title] for title, _ in modules if title in completed]


def append_embeddings(templates: list[dict[str, Any]], batch_size: int) -> int:
    meta_path = DATA_DIR / "strategy_meta.json"
    vector_path = DATA_DIR / "strategy_embeddings.npy"
    index_path = DATA_DIR / "strategy_index.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    vectors = np.load(vector_path)
    existing_sources = {str(item.get("source_module_title_zh", "")) for item in meta}
    new_templates = [item for item in templates if str(item.get("source_module_title_zh", "")) not in existing_sources]
    if not new_templates:
        print("Every translated strategy is already in the offline index; no vectors added.")
        return 0
    enriched = [{"id": len(meta) + index, **item} for index, item in enumerate(new_templates)]
    model = SentenceTransformer(str(DEFAULT_MODEL_DIR), device=preferred_device())
    encoded = model.encode(
        [build_strategy_text(item) for item in enriched], batch_size=batch_size,
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True,
    )
    new_vectors = np.asarray(encoded, dtype=np.float32)
    new_vectors /= np.linalg.norm(new_vectors, axis=1, keepdims=True)
    np.save(vector_path, np.vstack((vectors, new_vectors)).astype(np.float32))
    meta_path.write_text(json.dumps(meta + enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["num_strategies"] = len(meta) + len(enriched)
    index["translated_chinese_knowledge_templates"] = sum(
        item.get("source") == "translated_chinese_knowledge_note"
        for item in meta + enriched
    )
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Appended {len(enriched)} translated strategies; index now has {index['num_strategies']} rows.")
    return len(enriched)


def main() -> None:
    args = parse_args()
    if args.batch_size < 1 or args.max_concurrency < 1:
        raise ValueError("--batch-size and --max-concurrency must be positive")
    load_local_env()
    if args.replace_existing:
        removed = remove_existing_translations()
        for path in (args.translations_jsonl, args.templates_json):
            if path.exists():
                path.unlink()
        print(f"Removed {removed} previous translated strategies and their vectors.", flush=True)
    modules = split_modules(args.source.read_text(encoding="utf-8"))
    print(f"Found {len(modules)} Chinese strategy modules.", flush=True)
    templates = translate_modules(modules, args.translations_jsonl, args.max_concurrency)
    args.templates_json.parent.mkdir(parents=True, exist_ok=True)
    args.templates_json.write_text(json.dumps(templates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(templates)} successful English templates to {args.templates_json}", flush=True)
    append_embeddings(templates, args.batch_size)


if __name__ == "__main__":
    main()
