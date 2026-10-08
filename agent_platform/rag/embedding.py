import hashlib
import json
import threading

import numpy as np


class QwenEmbedding:
    """Pinned local weights, never an embedding API or implicit download."""

    dimensions = 1024

    def __init__(self, model_dir):
        from reasoning_agent.strategy_retrieval import ensure_model_weights
        self.model_dir = model_dir.resolve()
        weights = ensure_model_weights(self.model_dir)
        digest = hashlib.sha256()
        with weights.open("rb") as source:
            for part in iter(lambda: source.read(8 * 1024 * 1024), b""):
                digest.update(part)
        self.weights_hash = digest.hexdigest()
        configuration = {path.relative_to(self.model_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted(self.model_dir.rglob("*.json")) if "parts" not in path.name}
        bundle = {"weights": self.weights_hash, "configuration": configuration,
                  "implementation": "sentence-transformers-5.1.1-transformers-4.57.6",
                  "dimension": 1024, "max_sequence_length": 512, "query_prompt": "query"}
        self.identity = "qwen3-embedding-0.6b:" + hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest()
        self.lock, self.model = threading.Lock(), None

    def encode(self, texts, *, query=False):
        with self.lock:
            if self.model is None:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(str(self.model_dir), device="cpu", local_files_only=True, trust_remote_code=False)
                self.model.max_seq_length = 512
            vectors = self.model.encode(texts, prompt_name="query" if query else None,
                normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, batch_size=4)
            vectors = np.asarray(vectors, dtype=np.float32)
            if vectors.shape != (len(texts), self.dimensions) or not np.isfinite(vectors).all():
                raise ValueError("invalid_embeddings")
            if np.any(np.linalg.norm(vectors, axis=1) < .99):
                raise ValueError("zero_embeddings")
            return vectors.tolist()
