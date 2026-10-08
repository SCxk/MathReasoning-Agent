"""Shadow snapshots: Qdrant dense + BM25L sparse, then the accepted D-6 reranker."""

from collections import Counter
import hashlib
import json
import re
import threading
import unicodedata
from uuid import NAMESPACE_URL, uuid5

import numpy as np
from qdrant_client import models as qm
from rank_bm25 import BM25L

from agent_platform.rag.models import CHUNKER_VERSION, PARSER_VERSION, SPARSE_VERSION, RERANK_VERSION, Passage


def tokens(text):
    text = unicodedata.normalize("NFKC", text).lower()
    found = re.findall(r"\\[a-z]+|[a-z][a-z0-9_]*|\d+(?:\.\d+)?|[=+*/^<>-]", text)
    for phrase in re.findall(r"[\u3400-\u9fff]+", text):
        found.extend(phrase[index:index+2] for index in range(max(1, len(phrase)-1)))
    return found


def formula_tokens(text):
    return set(re.findall(r"\\[A-Za-z]+|[=+*/^<>]|\b[A-Za-z]\b", text))


def token_id(token):
    return int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big")


def sparse_vector(counts):
    # Collisions are merged deterministically; vectors use Qdrant's uint32 indices.
    values = {}
    for token, weight in counts.items():
        index = token_id(token)
        values[index] = values.get(index, 0.0) + float(weight)
    return qm.SparseVector(indices=sorted(values), values=[values[index] for index in sorted(values)])


class HybridIndex:
    def __init__(self, client, catalog, embedder, *, lock=None):
        self.client, self.catalog, self.embedder = client, catalog, embedder
        self.lock = lock or threading.RLock()
        bundle = [embedder.identity, PARSER_VERSION, CHUNKER_VERSION, SPARSE_VERSION, RERANK_VERSION]
        self.version = "rag-v1-" + hashlib.sha256(json.dumps(bundle).encode()).hexdigest()

    def ingest(self, document, parsed):
        with self.lock:
            if self.catalog.get(document.session_id, document.id).status != "indexing":
                return
            if any(doc.index_version != self.version for doc in self.catalog.documents(document.session_id, "ready")):
                raise ValueError("reindex_required")
            chunks = []
            for ordinal, part in enumerate(parsed.chunks):
                digest = hashlib.sha256(part.text.encode()).hexdigest()
                identifier = str(uuid5(NAMESPACE_URL, f"{document.id}:{self.version}:{ordinal}:{digest}"))
                chunks.append({"id": identifier, "session_id": document.session_id, "document_id": document.id,
                    "ordinal": ordinal, "text": part.text, "page_start": part.page_start, "page_end": part.page_end,
                    "domain": document.domain, "problem_type": document.problem_type, "source": document.source,
                    "index_version": self.version, "source_metadata": {
                        "title": document.original_name, "heading": part.heading, "domain": document.domain,
                        "problem_type": document.problem_type, "source": document.source,
                        "parser_version": PARSER_VERSION, "index_version": self.version, "content_hash": digest}})
            vectors = self.embedder.encode([part.text for part in parsed.chunks])
            matrix = np.asarray(vectors)
            if matrix.shape != (len(chunks), self.embedder.dimensions) or not np.isfinite(matrix).all():
                raise ValueError("invalid_embeddings")
            records = self.catalog.chunk_records(document.session_id) + list(zip(chunks, vectors, strict=True))
            records.sort(key=lambda pair: pair[0]["id"])
            corpus = [tokens(chunk["text"]) or ["__empty_math_document__"] for chunk, _ in records]
            bm25 = BM25L(corpus)
            corpus_hash = hashlib.sha256(json.dumps([chunk["id"] for chunk, _ in records]).encode()).hexdigest()
            name = "maths_rag_" + hashlib.sha256((document.session_id + self.version + corpus_hash).encode()).hexdigest()
            # Idempotent crash recovery replaces only an unactivated shadow collection.
            if self.client.collection_exists(name):
                if name in self.catalog.collections():
                    raise ValueError("active_snapshot_conflict")
                self.client.delete_collection(name)
            self.client.create_collection(name, vectors_config={"dense": qm.VectorParams(
                size=self.embedder.dimensions, distance=qm.Distance.COSINE)}, sparse_vectors_config={"sparse": qm.SparseVectorParams()})
            try:
                for start in range(0, len(records), 64):
                    points = []
                    for position in range(start, min(start+64, len(records))):
                        chunk, dense = records[position]
                        frequency = Counter(corpus[position])
                        weights = {}
                        for token, tf in frequency.items():
                            ctd = tf / (1 - bm25.b + bm25.b * bm25.doc_len[position] / bm25.avgdl)
                            weights[token] = bm25.idf[token] * tf * (bm25.k1 + 1) * (ctd + bm25.delta) / (bm25.k1 + ctd + bm25.delta)
                        points.append(qm.PointStruct(id=chunk["id"], vector={"dense": dense, "sparse": sparse_vector(weights)}, payload=chunk))
                    self.client.upsert(name, points, wait=True)
                if self.client.count(name, exact=True).count != len(records):
                    raise ValueError("index_count_mismatch")
                self.catalog.activate(document, chunks, vectors, name, self.version, corpus_hash, parsed.page_count)
            except BaseException:
                # Keep the previous catalog pointer; the shadow never becomes visible.
                raise

    def reconcile(self):
        with self.lock:
            active = self.catalog.collections()
            for collection in self.client.get_collections().collections:
                if collection.name.startswith("maths_rag_") and collection.name not in active:
                    self.client.delete_collection(collection.name)

    def purge(self, document_id):
        with self.lock:
            for name in self.catalog.collections():
                if self.client.collection_exists(name):
                    self.client.delete(name, points_selector=qm.FilterSelector(filter=qm.Filter(must=[
                        qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))])), wait=True)

    def search(self, arguments):
        with self.lock:
            snapshot = self.catalog.snapshot(arguments["session_id"])
            if not snapshot:
                return {"passages": []}
            name, version, _ = snapshot
            if version != self.version:
                raise ValueError("reindex_required")
            ready = self.catalog.documents(arguments["session_id"], "ready")
            documents = {doc.id for doc in ready}
            if arguments.get("document_ids") is not None:
                documents.intersection_update(arguments["document_ids"])
            if not documents:
                return {"passages": []}
            must = [qm.FieldCondition(key="session_id", match=qm.MatchValue(value=arguments["session_id"])),
                    qm.FieldCondition(key="document_id", match=qm.MatchAny(any=sorted(documents))),
                    qm.FieldCondition(key="index_version", match=qm.MatchValue(value=self.version))]
            for key in ("domain", "problem_type", "source"):
                if arguments.get(key) is not None:
                    must.append(qm.FieldCondition(key=key, match=qm.MatchValue(value=arguments[key])))
            filtered = qm.Filter(must=must)
            query = arguments["query"]
            vector = self.embedder.encode([query], query=True)[0]
            dense = self.client.query_points(name, query=vector, using="dense", query_filter=filtered, limit=20).points
            sparse_query = sparse_vector(Counter(tokens(query)))
            sparse = (self.client.query_points(name, query=sparse_query, using="sparse", query_filter=filtered, limit=20).points
                      if sparse_query.indices else [])
            candidates, ranks, raw = {}, {"dense": {}, "sparse": {}}, {}
            for channel, hits in (("dense", dense), ("sparse", sparse)):
                for rank, hit in enumerate(sorted(hits, key=lambda hit: (-hit.score, str(hit.id))), 1):
                    payload = hit.payload
                    if (payload["session_id"] != arguments["session_id"] or payload["document_id"] not in documents
                            or payload["index_version"] != self.version):
                        raise ValueError("retrieval_scope_violation")
                    key = str(hit.id)
                    candidates[key] = payload
                    ranks[channel][key] = 61 / (60 + rank)
                    raw.setdefault(key, {})[channel] = float(hit.score)
            formula = formula_tokens(query)
            scored = []
            for key, payload in candidates.items():
                other = formula_tokens(payload["text"])
                overlap = len(formula & other) / len(formula | other) if formula | other else 0
                supplied = [field for field in ("domain", "problem_type", "source") if arguments.get(field)]
                matches = sum(payload.get(field) == arguments[field] for field in supplied)
                metadata = 1.0 if supplied and matches == len(supplied) else .5 if matches else 0.0
                score = .45*ranks["dense"].get(key, 0) + .35*ranks["sparse"].get(key, 0) + .1*overlap + .1*metadata
                scored.append((score, key, payload))
            scored.sort(key=lambda item: (-item[0], item[1]))
            passages = []
            for score, key, payload in scored[:arguments["top_k"]]:
                passage = Passage(chunk_id=key, document_id=payload["document_id"], rank=len(passages)+1,
                    text=payload["text"], page_start=payload["page_start"], page_end=payload["page_end"],
                    source_metadata=payload["source_metadata"], scores={**raw[key], "rerank": score}).model_dump()
                if len(json.dumps({"passages": passages + [passage]}, ensure_ascii=False).encode()) > 60000:
                    break
                passages.append(passage)
            return {"passages": passages}
