"""SQLite reference document authority; PostgreSQL production authority is M6."""

import json
import sqlite3
import threading
from datetime import datetime, timezone

from agent_platform.models import PlatformError
from agent_platform.rag.models import Document
from agent_platform.history import cursor_parts, member, page_cursor


class DocumentCatalog:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL, content_hash TEXT NOT NULL,
                status TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(session_id, content_hash));
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL, data TEXT NOT NULL, vector TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshots (
                session_id TEXT PRIMARY KEY, collection TEXT NOT NULL, index_version TEXT NOT NULL,
                corpus_hash TEXT NOT NULL);
        """)

    def close(self):
        with self.lock:
            self.connection.close()

    def reserve(self, document):
        with self.lock, self.connection:
            count = self.connection.execute("SELECT count(*) FROM documents WHERE status='indexing'").fetchone()[0]
            if count >= 16:
                raise PlatformError("ingestion_capacity_exceeded", 429)
            try:
                self.connection.execute("INSERT INTO documents VALUES (?,?,?,?,?)", (
                    document.id, document.session_id, document.content_hash, document.status, document.model_dump_json()))
            except sqlite3.IntegrityError:
                raise PlatformError("duplicate_document", 409) from None

    def get(self, session_id, document_id):
        with self.lock:
            row = self.connection.execute("SELECT data FROM documents WHERE session_id=? AND id=?",
                                          (session_id, document_id)).fetchone()
        if not row:
            raise PlatformError("document_not_found", 404)
        return Document.model_validate_json(row[0])

    def list_page(self, session_id, limit, cursor=None):
        scope = "documents:" + session_id
        boundary = cursor_parts(cursor, scope)
        query = "SELECT data FROM documents WHERE session_id=?"
        args = [session_id]
        if boundary:
            query += " AND (json_extract(data,'$.created_at'),id) < (?,?)"
            args.extend([boundary[0].isoformat(), boundary[1]])
        query += " ORDER BY json_extract(data,'$.created_at') DESC,id DESC LIMIT ?"
        args.append(limit + 1)
        with self.lock:
            rows = [Document.model_validate_json(row[0]) for row in self.connection.execute(query, args)]
        return rows[:limit], page_cursor([member(datetime.fromisoformat(row.created_at), row.id) for row in rows], limit, scope)

    def documents(self, session_id=None, status=None):
        conditions, args = [], []
        for key, value in (("session_id", session_id), ("status", status)):
            if value is not None:
                conditions.append(f"{key}=?")
                args.append(value)
        query = "SELECT data FROM documents" + (" WHERE " + " AND ".join(conditions) if conditions else "") + " ORDER BY id"
        with self.lock:
            documents = [Document.model_validate_json(row[0]) for row in self.connection.execute(query, args)]
        if status == "ready":
            documents = [doc for doc in documents if datetime.fromisoformat(doc.expires_at) > datetime.now(timezone.utc)]
        return documents

    def fail(self, document, code):
        with self.lock, self.connection:
            # Failed documents never replace the last complete Session snapshot.
            document.status, document.error_code = "failed", code
            self.connection.execute("UPDATE documents SET status=?,data=? WHERE id=? AND session_id=? AND status='indexing'",
                (document.status, document.model_dump_json(), document.id, document.session_id))

    def chunk_records(self, session_id):
        ready = {doc.id for doc in self.documents(session_id, "ready")}
        with self.lock:
            rows = self.connection.execute("""SELECT c.data,c.vector FROM chunks c JOIN documents d ON d.id=c.document_id
                WHERE d.session_id=? AND d.status='ready' ORDER BY c.id""", (session_id,)).fetchall()
        records = [(json.loads(row[0]), json.loads(row[1])) for row in rows]
        return [record for record in records if record[0]["document_id"] in ready]

    def expire(self, document):
        with self.lock, self.connection:
            document.status = "expired"
            self.connection.execute("UPDATE documents SET status=?,data=? WHERE id=?", (
                "expired", document.model_dump_json(), document.id))
            self.connection.execute("DELETE FROM chunks WHERE document_id=?", (document.id,))

    def collections(self):
        with self.lock:
            return {row[0] for row in self.connection.execute("SELECT collection FROM snapshots")}

    def activate(self, document, chunks, vectors, collection, version, corpus_hash, page_count):
        with self.lock, self.connection:
            current = self.get(document.session_id, document.id)
            if current.status != "indexing":
                raise PlatformError("stale_ingestion", 409)
            for chunk, vector in zip(chunks, vectors, strict=True):
                self.connection.execute("INSERT OR REPLACE INTO chunks VALUES (?,?,?,?)", (
                    chunk["id"], document.id, json.dumps(chunk, allow_nan=False), json.dumps(vector, allow_nan=False)))
            document.status, document.chunk_count, document.page_count = "ready", len(chunks), page_count
            document.parser_version = chunks[0]["source_metadata"]["parser_version"]
            document.index_version = version
            self.connection.execute("UPDATE documents SET status=?,data=? WHERE id=?", ("ready", document.model_dump_json(), document.id))
            self.connection.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?)", (
                document.session_id, collection, version, corpus_hash))

    def snapshot(self, session_id):
        with self.lock:
            row = self.connection.execute("SELECT collection,index_version,corpus_hash FROM snapshots WHERE session_id=?", (session_id,)).fetchone()
        return row

    def referenced_blobs(self):
        return {document.storage_key for document in self.documents()}
