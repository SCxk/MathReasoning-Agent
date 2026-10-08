"""Append local supplemental strategy templates to the existing StrategyRAG index."""
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

DATA = ROOT / "strategy_data"

def main() -> None:
    meta_path, vec_path, index_path = DATA / "strategy_meta.json", DATA / "strategy_embeddings.npy", DATA / "strategy_index.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")); vectors = np.load(vec_path)
    extras = json.loads((DATA / "additional_strategies.json").read_text(encoding="utf-8"))
    existing_names = {str(item.get("name", "")) for item in meta}
    extras = [item for item in extras if item["name"] not in existing_names]
    if not extras:
        print("All supplemental strategies are already present; no changes made.")
        return
    start = len(meta)
    enriched = [{"id": start + i, **item} for i, item in enumerate(extras)]
    model = SentenceTransformer(str(DEFAULT_MODEL_DIR), device=preferred_device())
    extra_vectors = np.asarray(model.encode([build_strategy_text(item) for item in enriched], batch_size=16, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True), dtype=np.float32)
    extra_vectors /= np.linalg.norm(extra_vectors, axis=1, keepdims=True)
    np.save(vec_path, np.vstack((vectors, extra_vectors)).astype(np.float32))
    meta_path.write_text(json.dumps(meta + enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    index = json.loads(index_path.read_text(encoding="utf-8")); index["num_strategies"] = len(meta) + len(enriched); index["supplemental_templates"] = len(enriched)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Appended {len(enriched)} strategies; index now has {index['num_strategies']} rows.")
if __name__ == "__main__": main()
