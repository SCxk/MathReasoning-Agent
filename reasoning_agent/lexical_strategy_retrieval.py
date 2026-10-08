"""Dependency-free lexical retrieval for local strategy cards."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "strategy_data"
INDEX_NAME = "strategy_lexical_index.json"
MANIFEST_NAME = "strategy_lexical_manifest.json"
LEXICAL_RULES_VERSION = "1"
_ENGLISH = re.compile(r"[a-z][a-z0-9_\\-]*|\\d+(?:\\.\\d+)?|\\\\[a-z]+|[=+*/^<>|]+", re.I)
_CHINESE = re.compile(r"[\u4e00-\u9fff]{2,}")
_ALIAS_GROUPS = (("dp", "dynamic", "programming"), ("hamiltonian",), ("bijection", "bijective"))


def tokenize(text: str) -> Counter[str]:
    """Return deterministic English/math tokens plus Chinese 2--4 grams."""
    normalized = unicodedata.normalize("NFKC", str(text)).lower()
    tokens = [match.group(0) for match in _ENGLISH.finditer(normalized)]
    for phrase in _CHINESE.findall(normalized):
        for size in range(2, min(4, len(phrase)) + 1):
            tokens.extend(phrase[start:start + size] for start in range(len(phrase) - size + 1))
    present = set(tokens)
    for group in _ALIAS_GROUPS:
        if any(term in present for term in group):
            tokens.extend(f"alias:{term}" for term in group)
    return Counter(token for token in tokens if len(token) > 1)


def cards_digest(cards: list[dict[str, Any]]) -> str:
    payload = json.dumps(cards, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def card_text(card: dict[str, Any]) -> str:
    fields: list[str] = []
    for key in ("name", "description", "tags", "applicability", "steps"):
        value = card.get(key, "")
        fields.append(json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value))
    return "\n".join(fields)


def normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    low, high = min(scores), max(scores)
    if high <= low:
        return [1.0 if high > 0 else 0.0 for _ in scores]
    return [(score - low) / (high - low) for score in scores]


class LexicalStrategyRetriever:
    """Load a verified BM25/TF-IDF index and rank cards without ML dependencies."""

    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.index, self.manifest = self._load()
        self.cards: list[dict[str, Any]] = self.index["cards"]
        self.idf: dict[str, float] = self.index["idf"]
        self.postings: dict[str, list[list[int]]] = self.index["postings"]
        self.docs: list[dict[str, Any]] = self.index["documents"]
        self.avgdl = float(self.index["avgdl"])

    def _load(self) -> tuple[dict[str, Any], dict[str, Any]]:
        index_path, manifest_path = self.data_dir / INDEX_NAME, self.data_dir / MANIFEST_NAME
        if not index_path.is_file() or not manifest_path.is_file():
            raise FileNotFoundError("lexical strategy index is missing")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cards = json.loads((self.data_dir / "strategy_meta.json").read_text(encoding="utf-8"))
        expected_ids = [card.get("id") for card in cards]
        if (
            manifest.get("rules_version") != LEXICAL_RULES_VERSION
            or manifest.get("cards_digest") != cards_digest(cards)
            or manifest.get("card_ids") != expected_ids
            or index.get("card_ids") != expected_ids
            or index.get("rules_version") != LEXICAL_RULES_VERSION
        ):
            raise ValueError("lexical strategy index does not match strategy cards")
        return index, manifest

    def retrieve_for_structure(
        self, raw_problem: str, retrieval_text: str | None, *, top_k: int = 5,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        raw = self._lexical_scores(raw_problem)
        structured = self._lexical_scores(retrieval_text or "") if retrieval_text else None
        raw_norm = normalize_scores(raw[0])
        structured_norm = normalize_scores(structured[0]) if structured else [0.0] * len(self.cards)
        structured_allowed = bool(retrieval_text) and not self._conflicts(raw_problem, retrieval_text)
        final: list[float] = []
        for row in range(len(self.cards)):
            score = 0.4 * raw_norm[row] + (0.6 * structured_norm[row] if structured_allowed else 0.0)
            score += self._metadata_bonus(row, metadata)
            final.append(score)
        order = sorted(range(len(final)), key=lambda row: (-final[row], str(self.cards[row].get("id", ""))))[:top_k]
        results = []
        for row in order:
            item = dict(self.cards[row])
            item.update(score=float(final[row]), raw_score=float(raw_norm[row]), structure_score=float(structured_norm[row]))
            results.append(item)
        return {
            "retrieval_text": retrieval_text or "",
            "results": results,
            "index_version": str(self.manifest.get("version", "unknown")),
            "structured_query_used": structured_allowed,
        }

    def _lexical_scores(self, query: str) -> tuple[list[float], list[float], list[float]]:
        query_counts = tokenize(query)
        bm25 = [0.0] * len(self.docs)
        dot = [0.0] * len(self.docs)
        query_sq = 0.0
        for term, qtf in query_counts.items():
            idf = self.idf.get(term)
            if idf is None:
                continue
            qweight = qtf * idf
            query_sq += qweight * qweight
            for row, tf in self.postings.get(term, []):
                doc = self.docs[row]
                denom = tf + 1.2 * (1.0 - 0.75 + 0.75 * float(doc["length"]) / max(1.0, self.avgdl))
                bm25[row] += idf * (tf * 2.2) / denom
                dot[row] += qweight * (float(doc["tf"][term]) * idf)
        tfidf = [dot[row] / (math.sqrt(query_sq) * float(doc["norm"])) if query_sq and doc["norm"] else 0.0 for row, doc in enumerate(self.docs)]
        normalized_bm25, normalized_tfidf = normalize_scores(bm25), normalize_scores(tfidf)
        return ([0.5 * a + 0.5 * b for a, b in zip(normalized_bm25, normalized_tfidf)], bm25, tfidf)

    def _metadata_bonus(self, row: int, metadata: dict[str, Any] | None) -> float:
        if not metadata:
            return 0.0
        requested = tokenize(" ".join(str(value) for value in metadata.values() if isinstance(value, (str, int, float))))
        if not requested:
            return 0.0
        card_terms = tokenize(card_text(self.cards[row]))
        return 0.05 if set(requested).intersection(card_terms) else 0.0

    @staticmethod
    def _conflicts(problem: str, structure: str) -> bool:
        """Conservatively suppress a generated query with incompatible directionality."""
        raw, summary = problem.lower(), structure.lower()
        directed_raw = bool(re.search(r"\b(directed|from .+ to|ordered)\b|有向|从.+到|有序", raw))
        undirected_summary = bool(re.search(r"directionality:\s*undirected|无向", summary))
        undirected_raw = bool(re.search(r"\b(undirected|symmetric)\b|无向|对称", raw))
        directed_summary = bool(re.search(r"directionality:\s*directed|有向", summary))
        return (directed_raw and undirected_summary) or (undirected_raw and directed_summary)


_SHARED: dict[Path, LexicalStrategyRetriever] = {}


def get_shared_lexical_strategy_retriever(*, data_dir: Path = DEFAULT_DATA_DIR) -> LexicalStrategyRetriever:
    key = Path(data_dir).resolve()
    if key not in _SHARED:
        _SHARED[key] = LexicalStrategyRetriever(key)
    return _SHARED[key]

