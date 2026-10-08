"""Replace answer-bearing scoring references with generic formula-guidance vectors."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reasoning_agent.strategy_retrieval import DEFAULT_MODEL_DIR, preferred_device
from scripts.build_strategy_embeddings import build_strategy_text

DATA_DIR = ROOT / "strategy_data"
REPLACED_SOURCES = {"exact_scoring_reference", "formula_guidance_reference"}
SOURCE = "formula_guidance_reference"


def main() -> None:
    meta_path = DATA_DIR / "strategy_meta.json"
    vector_path = DATA_DIR / "strategy_embeddings.npy"
    index_path = DATA_DIR / "strategy_index.json"
    templates_path = DATA_DIR / "formula_guidance_strategies.json"

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    vectors = np.load(vector_path)
    templates = json.loads(templates_path.read_text(encoding="utf-8"))
    if len(metadata) != vectors.shape[0]:
        raise ValueError("strategy metadata and embedding matrix have different row counts")

    kept_indices = [index for index, item in enumerate(metadata) if item.get("source") not in REPLACED_SOURCES]
    retained_metadata = [metadata[index] for index in kept_indices]
    retained_vectors = vectors[kept_indices]
    existing_names = {str(item.get("name", "")) for item in retained_metadata}
    additions = [item for item in templates if item["name"] not in existing_names]
    enriched = [{"id": len(retained_metadata) + offset, **item} for offset, item in enumerate(additions)]

    model = SentenceTransformer(str(DEFAULT_MODEL_DIR), device=preferred_device())
    encoded = model.encode(
        [build_strategy_text(item) for item in enriched],
        batch_size=8,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    new_vectors = np.asarray(encoded, dtype=np.float32)
    norms = np.linalg.norm(new_vectors, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms == 0):
        raise ValueError("new embedding rows contain a non-finite or zero norm")
    new_vectors /= norms

    merged_metadata = retained_metadata + enriched
    for index, item in enumerate(merged_metadata):
        item["id"] = index
    merged_vectors = np.vstack((retained_vectors, new_vectors)).astype(np.float32)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["num_strategies"] = len(merged_metadata)
    index.pop("exact_scoring_reference_templates", None)
    index["formula_guidance_reference_templates"] = sum(
        item.get("source") == SOURCE for item in merged_metadata
    )

    np.save(vector_path, merged_vectors)
    meta_path.write_text(json.dumps(merged_metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Replaced {len(metadata) - len(retained_metadata)} answer-bearing rows with "
        f"{len(enriched)} formula-guidance strategies; index now has {len(merged_metadata)} rows."
    )


if __name__ == "__main__":
    main()
