"""Structured-query retrieval over the local ReasonFlux strategy index.

This module deliberately accepts an already-injected chat client.  It never
creates a model client or reads credentials, so the same code works in the
official evaluator and with the local runner's client.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

if os.name == "nt":
    import msvcrt
else:
    import fcntl

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "strategy_data"
DEFAULT_MODEL_DIR = REPO_ROOT / "strategyrag" / "Qwen3-Embedding-0.6B"
EMBEDDING_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIM = 1024
MODEL_WEIGHTS_NAME = "model.safetensors"
MODEL_PARTS_MANIFEST = "model.safetensors.parts.json"
RAW_SCORE_WEIGHT = 0.35
STRUCTURE_SCORE_WEIGHT = 0.65
STRUCTURE_ANALYSIS_PROMPT = """You are a mathematical problem analyzer.

Your task is to analyze the given mathematical problem and extract a concise structural representation that can be used to retrieve appropriate mathematical problem-solving strategies.

Do NOT solve the problem.
Do NOT provide intermediate reasoning.
Do NOT recommend or name specific solution methods, theorems, inequalities, tactics, or strategies unless they are explicitly stated in the problem.
Do NOT guess the intended solution.

Focus only on describing what the problem is.

Return ONLY the following retrieval text format. Keep one concise line for the first five fields and use bullet points under Structure:

Domain: <primary mathematical domain>
Goal: <what the problem asks to establish or compute>
Objects: <main mathematical objects>
Constraints: <explicit assumptions and relations>
Directionality: <directed | undirected | mixed | unspecified; state the exact ordered transition rule when relevant>
Structure:
- <structural characteristic>
- <structural characteristic>

Use a concise domain such as algebra, number theory, geometry, combinatorics, inequality, probability, calculus, sequences, or functional equations.  Describe structures as mathematical form rather than methods.

Additional requirements:

1. Keep every field concise.
2. Do not include the final answer.
3. Do not derive new equations unless they are immediate restatements of the given conditions.
4. Do not include candidate methods such as Cauchy-Schwarz, AM-GM, induction, contradiction, substitution, modular arithmetic, or similar solution strategies unless the problem explicitly mentions them.
5. Prefer structural descriptions that are useful for semantic retrieval.
6. If multiple mathematical domains are involved, choose the dominant one for "domain" and represent secondary characteristics in "structures".
7. Output only the retrieval text. Do not add explanations before or after it.
8. For sequence-adjacency, coordinate-difference, ordered-pair, graph-edge, or transition rules, preserve the
   relation from the current item to the next item exactly. State whether each relevant transition is directed,
   undirected, or mixed in ``Directionality``. Do not infer reverse reachability from a periodic vertex set.
9. If multiple listed coordinate differences are congruent modulo a stated period, say that they encode the same
   directed orientation. Do not describe such a relation as “adjacent x-values”, “left/right moves”, or an
   undirected Cartesian product unless the original problem explicitly permits both orientations.
10. Do not use notation such as ``C_n × P_k`` by itself for an ordered transition problem: if it is useful,
    qualify it as directed and state the exact allowed orientation.

Mathematical Problem:

{problem}"""

_SHARED_RETRIEVERS: dict[tuple[Path, Path, str], "StrategyRetriever"] = {}
_SHARED_RETRIEVERS_LOCK = threading.Lock()


@contextmanager
def _exclusive_file_lock(path: Path):
    """Serialize model reconstruction across evaluator processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as lock_file:
        if os.name == "nt":
            # msvcrt.locking locks a byte range and requires the byte to exist.
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def ensure_model_weights(model_dir: Path) -> Path:
    """Rebuild a Git-friendly split checkpoint on its first runtime use."""
    target = model_dir / MODEL_WEIGHTS_NAME
    if target.is_file():
        return target

    manifest_path = model_dir / MODEL_PARTS_MANIFEST
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Missing {target} and reconstruction manifest {manifest_path}"
        )

    with _exclusive_file_lock(model_dir / ".model-rebuild.lock"):
        if target.is_file():
            return target
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parts = manifest.get("parts")
        expected_size = manifest.get("size")
        expected_sha256 = manifest.get("sha256")
        if (
            manifest.get("target") != MODEL_WEIGHTS_NAME
            or not isinstance(parts, list)
            or not parts
            or not all(isinstance(name, str) and Path(name).name == name for name in parts)
            or not isinstance(expected_size, int)
            or expected_size <= 0
            or not isinstance(expected_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        ):
            raise ValueError(f"Invalid model-parts manifest: {manifest_path}")

        temporary = model_dir / f".{MODEL_WEIGHTS_NAME}.{os.getpid()}.tmp"
        digest = hashlib.sha256()
        written = 0
        try:
            with temporary.open("wb") as output:
                for name in parts:
                    part_path = model_dir / name
                    if not part_path.is_file():
                        raise FileNotFoundError(f"Missing model part: {part_path}")
                    with part_path.open("rb") as part:
                        while chunk := part.read(8 * 1024 * 1024):
                            output.write(chunk)
                            digest.update(chunk)
                            written += len(chunk)
                output.flush()
                os.fsync(output.fileno())
            if written != expected_size or digest.hexdigest() != expected_sha256:
                raise ValueError("Reconstructed embedding model failed integrity validation")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


class StructuredRetrievalOutputError(ValueError):
    """A parse error that retains the model text for console inspection."""

    def __init__(self, message: str, raw_output: str) -> None:
        super().__init__(message)
        self.raw_output = raw_output


def preferred_device() -> str:
    """Use CPU unless a caller deliberately requests another device.

    The official Docker environment may expose CUDA libraries without a usable
    device. Choosing CPU by default keeps strategy retrieval non-blocking and
    lets explicit local callers opt into ``cuda`` or ``mps`` when appropriate.
    """
    return "cpu"


def build_structure_messages(problem: str) -> list[dict[str, str]]:
    """Build the single, deterministic analysis request for an injected client."""
    return [{"role": "user", "content": STRUCTURE_ANALYSIS_PROMPT.replace("{problem}", problem)}]


def get_shared_strategy_retriever(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    model_dir: Path = DEFAULT_MODEL_DIR,
    device: str | None = None,
) -> "StrategyRetriever":
    """Return one immutable-index retriever per process/resource/device.

    Local runners solve multiple items concurrently in threads. Reusing the
    embedding model prevents concurrent 0.6B model loads; retrieval itself is
    serialized by the retriever's encoding lock because MPS command buffers
    are not safe for simultaneous SentenceTransformer calls here.
    """
    selected_device = device or preferred_device()
    key = (data_dir.resolve(), model_dir.resolve(), selected_device)
    with _SHARED_RETRIEVERS_LOCK:
        retriever = _SHARED_RETRIEVERS.get(key)
        if retriever is None:
            retriever = StrategyRetriever(
                data_dir=data_dir, model_dir=model_dir, device=selected_device,
            )
            _SHARED_RETRIEVERS[key] = retriever
        return retriever


def analyze_problem_structure(client: Any, problem: str) -> str:
    """Request a structural retrieval text from the supplied platform client."""
    _, retrieval_text = analyze_problem_structure_with_raw(client, problem)
    return retrieval_text


def analyze_problem_structure_with_raw(client: Any, problem: str) -> tuple[str, str]:
    """Return both the unmodified model output and validated retrieval text."""
    if not callable(getattr(client, "chat", None)):
        raise TypeError("client must expose a callable chat method")
    response = client.chat(
        messages=build_structure_messages(problem),
        temperature=0.0,
        thinking_mode=False,
        tools=None,
        max_tokens=512,
    )
    content = response if isinstance(response, str) else response.get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Structure analysis client response is empty")
    try:
        return content, normalize_retrieval_text(content)
    except ValueError as exc:
        raise StructuredRetrievalOutputError(str(exc), content) from exc


def normalize_retrieval_text(content: str) -> str:
    """Validate and normalize model output without changing its semantics."""
    lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
    values: dict[str, str] = {}
    structure_items: list[str] = []
    constraint_items: list[str] = []
    in_structure = False
    in_constraints = False
    for line in lines:
        # Models sometimes use Markdown emphasis or synonymous field labels
        # despite the requested template.  These are formatting variations,
        # not grounds to abandon an otherwise useful retrieval request.
        line = line.strip().strip("*").strip()
        matched = re.match(
            r"^(Domain|Goal|Objects|Constraints|Conditions|Assumptions|Directionality|Direction|"
            r"Structure|Structures):\*{0,2}\s*(.*)$",
            line,
            re.I,
        )
        if matched:
            label, value = matched.groups()
            normalized_label = {
                "conditions": "constraints",
                "assumptions": "constraints",
                "direction": "directionality",
                "structures": "structure",
            }.get(label.lower(), label.lower())
            if normalized_label == "structure":
                in_structure = True
                in_constraints = False
                if value.strip():
                    structure_items.append(value.strip())
            else:
                values[normalized_label] = value.strip()
                in_constraints = normalized_label == "constraints"
                in_structure = False
            continue
        if in_structure and line.startswith("-"):
            item = line[1:].strip()
            if item:
                structure_items.append(item)
        elif in_constraints and line.startswith("-"):
            item = line[1:].strip()
            if item:
                constraint_items.append(item)
    # A problem can genuinely have no standalone constraints.  More often,
    # this field is simply omitted by a concise model response.  Preserve the
    # usable domain/goal/object signal and state the absence explicitly.
    if constraint_items:
        existing = values.get("constraints", "")
        values["constraints"] = "; ".join(
            part for part in ([existing] if existing else []) + constraint_items
        )
    if not values.get("constraints"):
        values["constraints"] = "No explicit constraints extracted."
    if not values.get("directionality"):
        values["directionality"] = "Unspecified; preserve any ordered relation from the raw problem."
    missing = [field for field in ("domain", "goal", "objects") if not values.get(field)]
    if missing:
        raise ValueError("Structured retrieval text is missing: " + ", ".join(missing))
    if not structure_items:
        structure_items.append("No additional structural description extracted.")
    return "\n".join(
        [
            f"Domain: {values['domain']}",
            f"Goal: {values['goal']}",
            f"Objects: {values['objects']}",
            f"Constraints: {values['constraints']}",
            f"Directionality: {values['directionality']}",
            "Structure:",
            *(f"- {item}" for item in structure_items),
        ]
    )


class StrategyRetriever:
    """One model-analysis call followed by two-channel NumPy retrieval."""

    def __init__(
        self,
        *,
        data_dir: Path = DEFAULT_DATA_DIR,
        model_dir: Path = DEFAULT_MODEL_DIR,
        device: str | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.device = device or preferred_device()
        self._model: Any | None = None
        self._encode_lock = threading.RLock()
        self._vectors, self._metadata = self._load_index()

    def retrieve_for_problem(self, client: Any, problem: str, *, top_k: int = 5) -> dict[str, Any]:
        raw_model_output, retrieval_text = analyze_problem_structure_with_raw(client, problem)
        results = self.retrieve_hybrid(problem, retrieval_text, top_k=top_k)
        return {
            "structured_model_output": raw_model_output,
            "retrieval_text": retrieval_text,
            "results": results,
        }

    def retrieve_for_structure(
        self, raw_problem: str, retrieval_text: str, *, top_k: int = 5
    ) -> dict[str, Any]:
        """Retrieve after a caller has budgeted the structure-analysis call.

        Action Graph uses this path so all model calls remain inside its wall
        clock and stage accounting, while the query normalization and hybrid
        ranking remain identical to :meth:`retrieve_for_problem`.
        """
        normalized = normalize_retrieval_text(retrieval_text)
        return {
            "retrieval_text": normalized,
            "results": self.retrieve_hybrid(raw_problem, normalized, top_k=top_k),
        }

    def retrieve_text(self, retrieval_text: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve from a pre-built structured text alone."""
        if top_k < 1:
            raise ValueError("top_k must be positive")
        with self._encode_lock:
            query_vector = self._encode(normalize_retrieval_text(retrieval_text))
            scores = np.asarray(self._vectors @ query_vector)
        return self._rank(scores, top_k=top_k, raw_scores=None, structure_scores=scores)

    def retrieve_hybrid(
        self, raw_problem: str, retrieval_text: str, *, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Rank by 0.35 × raw-problem score + 0.65 × structured-query score."""
        if top_k < 1:
            raise ValueError("top_k must be positive")
        with self._encode_lock:
            raw_vector = self._encode(raw_problem)
            structure_vector = self._encode(normalize_retrieval_text(retrieval_text))
            raw_scores = np.einsum("ij,j->i", self._vectors, raw_vector.astype(np.float64))
            structure_scores = np.einsum(
                "ij,j->i", self._vectors, structure_vector.astype(np.float64)
            )
            mixed_scores = (
                RAW_SCORE_WEIGHT * raw_scores
                + STRUCTURE_SCORE_WEIGHT * structure_scores
            )
        return self._rank(
            mixed_scores,
            top_k=top_k,
            raw_scores=raw_scores,
            structure_scores=structure_scores,
        )

    def _rank(
        self,
        scores: np.ndarray,
        *,
        top_k: int,
        raw_scores: np.ndarray | None,
        structure_scores: np.ndarray,
    ) -> list[dict[str, Any]]:
        count = min(top_k, len(scores))
        candidates = np.argpartition(scores, -count)[-count:]
        ordered = candidates[np.argsort(scores[candidates])[::-1]]
        results: list[dict[str, Any]] = []
        for row in ordered:
            item = dict(self._metadata[int(row)])
            item["score"] = float(scores[int(row)])
            if raw_scores is not None:
                item["raw_score"] = float(raw_scores[int(row)])
            item["structure_score"] = float(structure_scores[int(row)])
            results.append(item)
        return results

    def _load_index(self) -> tuple[np.ndarray, list[dict[str, Any]]]:
        vector_path = self.data_dir / "strategy_embeddings.npy"
        metadata_path = self.data_dir / "strategy_meta.json"
        index_path = self.data_dir / "strategy_index.json"
        if not all(path.is_file() for path in (vector_path, metadata_path, index_path)):
            raise FileNotFoundError(f"Incomplete strategy index under {self.data_dir}")
        # The matrix is only about 13 MB.  Loading it eagerly avoids sporadic
        # invalid BLAS results observed with a float32 memory-map on NumPy 2.
        vectors = np.asarray(np.load(vector_path), dtype=np.float64)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        index = json.loads(index_path.read_text(encoding="utf-8"))
        if index.get("embedding_model") != EMBEDDING_MODEL_NAME:
            raise ValueError("Strategy index embedding model is inconsistent")
        if int(index.get("embedding_dim", -1)) != EMBEDDING_DIM:
            raise ValueError("Strategy index embedding dimension is inconsistent")
        if vectors.shape != (len(metadata), EMBEDDING_DIM):
            raise ValueError("Strategy index vectors and metadata are inconsistent")
        return vectors, metadata

    def _encode(self, text: str) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            ensure_model_weights(self.model_dir)
            self._model = SentenceTransformer(str(self.model_dir), device=self.device)
        vector = self._model.encode(
            [text], prompt_name="query", normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False,
        )
        vector = np.asarray(vector[0], dtype=np.float32)
        if vector.shape != (EMBEDDING_DIM,):
            raise ValueError("Strategy query embedding dimension is inconsistent")
        norm = np.linalg.norm(vector)
        if not np.isfinite(norm) or norm == 0:
            raise ValueError("Query embedding is non-finite or zero")
        return vector / norm
