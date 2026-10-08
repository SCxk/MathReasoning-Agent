"""Build the checked-in dependency-free lexical strategy index."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reasoning_agent.lexical_strategy_retrieval import LEXICAL_RULES_VERSION, card_text, cards_digest, tokenize


def atomic_json(path: Path, value: object) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        handle.flush(); os.fsync(handle.fileno()); temporary = Path(handle.name)
    temporary.replace(path)


def build(data_dir: Path) -> None:
    cards = json.loads((data_dir / "strategy_meta.json").read_text(encoding="utf-8"))
    docs = [tokenize(card_text(card)) for card in cards]
    df: Counter[str] = Counter(term for doc in docs for term in doc)
    total = len(docs)
    idf = {term: math.log(1.0 + (total - count + 0.5) / (count + 0.5)) for term, count in sorted(df.items())}
    postings: dict[str, list[list[int]]] = defaultdict(list)
    packed_docs = []
    for row, doc in enumerate(docs):
        for term, tf in doc.items(): postings[term].append([row, tf])
        norm = math.sqrt(sum((tf * idf[term]) ** 2 for term, tf in doc.items()))
        packed_docs.append({"length": sum(doc.values()), "norm": norm, "tf": dict(sorted(doc.items()))})
    ids = [card.get("id") for card in cards]
    index = {"rules_version": LEXICAL_RULES_VERSION, "card_ids": ids, "cards": cards, "idf": idf,
             "postings": dict(sorted(postings.items())), "documents": packed_docs,
             "avgdl": sum(doc["length"] for doc in packed_docs) / max(1, total)}
    manifest = {"version": "1", "rules_version": LEXICAL_RULES_VERSION, "cards_digest": cards_digest(cards),
                "card_ids": ids, "document_count": total, "vocabulary_size": len(idf),
                "bm25": {"k1": 1.2, "b": 0.75}, "tfidf": {"l2_normalized": True}}
    atomic_json(data_dir / "strategy_lexical_index.json", index)
    atomic_json(data_dir / "strategy_lexical_manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "strategy_data")
    build(parser.parse_args().data_dir)

