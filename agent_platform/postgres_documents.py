"""PostgreSQL document authority and cross-process snapshot reader/writer fencing."""

from contextlib import contextmanager
from datetime import datetime, timezone
import threading

from sqlalchemy import and_, delete, func, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from agent_platform.database import lock_id
from agent_platform.models import PlatformError
from agent_platform.rag.models import Document
from agent_platform.history import cursor_parts, member, page_cursor


class AdvisoryIndexLock:
    def __init__(self, engine, namespace, *, shared=False):
        self.engine, self.key, self.shared = engine, lock_id(namespace, "rag-index"), shared
        self.local = threading.local()

    def __enter__(self):
        if getattr(self.local, "depth", 0):
            self.local.depth += 1
            return self
        self.local.connection = self.engine.connect()
        try:
            function = "pg_advisory_xact_lock_shared" if self.shared else "pg_advisory_xact_lock"
            self.local.connection.execute(text(f"SELECT {function}(:key)"), {"key": self.key})
            self.local.depth = 1
            return self
        except BaseException:
            self.local.connection.close()
            raise

    def __exit__(self, *args):
        self.local.depth -= 1
        if not self.local.depth:
            self.local.connection.close()


class PostgresDocumentCatalog:
    def __init__(self, engine, metadata, *, read_only=False):
        self.engine, self.metadata = engine, metadata
        self.namespace = metadata.schema
        self.index_lock = AdvisoryIndexLock(engine, self.namespace, shared=read_only)

    def table(self, name):
        return self.metadata.tables[f"{self.namespace}.{name}"]

    def close(self):
        pass  # The deployment owns the shared engine lifecycle.

    @contextmanager
    def transaction(self):
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": lock_id(self.namespace, "documents")},
                )
                yield connection
        except SQLAlchemyError:
            raise PlatformError("document_storage_unavailable", 503) from None

    def reserve(self, document):
        table = self.table("documents")
        with self.transaction() as connection:
            if (
                connection.execute(
                    select(func.count()).select_from(table).where(table.c.status == "indexing")
                ).scalar_one()
                >= 16
            ):
                raise PlatformError("ingestion_capacity_exceeded", 429)
            try:
                connection.execute(
                    table.insert().values(
                        id=document.id,
                        session_id=document.session_id,
                        content_hash=document.content_hash,
                        status=document.status,
                        data=document.model_dump(),
                    )
                )
            except IntegrityError:
                raise PlatformError("duplicate_document", 409) from None

    def get(self, session_id, document_id):
        table = self.table("documents")
        with self.engine.connect() as connection:
            data = connection.execute(
                select(table.c.data).where(
                    and_(table.c.session_id == session_id, table.c.id == document_id)
                )
            ).scalar()
        if data is None:
            raise PlatformError("document_not_found", 404)
        return Document.model_validate(data)

    def documents(self, session_id=None, status=None):
        table = self.table("documents")
        query = select(table.c.data).order_by(table.c.id)
        if session_id is not None:
            query = query.where(table.c.session_id == session_id)
        if status is not None:
            query = query.where(table.c.status == status)
        with self.engine.connect() as connection:
            documents = [
                Document.model_validate(data) for data in connection.execute(query).scalars()
            ]
        if status == "ready":
            documents = [
                doc
                for doc in documents
                if datetime.fromisoformat(doc.expires_at) > datetime.now(timezone.utc)
            ]
        return documents

    def list_page(self, session_id, limit, cursor=None):
        scope = "documents:" + session_id
        boundary = cursor_parts(cursor, scope)
        table = self.table("documents")
        created = table.c.data["created_at"].as_string()
        query = select(table.c.data).where(table.c.session_id == session_id)
        if boundary:
            query = query.where(tuple_(created, table.c.id) < (boundary[0].isoformat(), boundary[1]))
        query = query.order_by(created.desc(), table.c.id.desc()).limit(limit + 1)
        try:
            with self.engine.connect() as connection:
                rows = [Document.model_validate(row) for row in connection.execute(query).scalars()]
            return rows[:limit], page_cursor([member(datetime.fromisoformat(row.created_at), row.id) for row in rows], limit, scope)
        except SQLAlchemyError:
            raise PlatformError("document_storage_unavailable", 503) from None

    def fail(self, document, code):
        document.status, document.error_code = "failed", code
        table = self.table("documents")
        with self.transaction() as connection:
            connection.execute(
                update(table)
                .where(
                    and_(
                        table.c.id == document.id,
                        table.c.session_id == document.session_id,
                        table.c.status == "indexing",
                    )
                )
                .values(status="failed", data=document.model_dump())
            )

    def chunk_records(self, session_id):
        ready = [doc.id for doc in self.documents(session_id, "ready")]
        chunks = self.table("chunks")
        with self.engine.connect() as connection:
            return [
                (row[0], row[1])
                for row in connection.execute(
                    select(chunks.c.data, chunks.c.vector)
                    .where(chunks.c.document_id.in_(ready))
                    .order_by(chunks.c.id)
                )
            ]

    def activate(self, document, chunks, vectors, collection, version, corpus_hash, page_count):
        table = self.table("documents")
        with self.transaction() as connection:
            status = connection.execute(
                select(table.c.status).where(
                    and_(table.c.id == document.id, table.c.session_id == document.session_id)
                )
            ).scalar()
            if status != "indexing":
                raise PlatformError("stale_ingestion", 409)
            for chunk, vector in zip(chunks, vectors, strict=True):
                statement = insert(self.table("chunks")).values(
                    id=chunk["id"], document_id=document.id, data=chunk, vector=vector
                )
                connection.execute(
                    statement.on_conflict_do_update(
                        index_elements=["id"], set_={"data": chunk, "vector": vector}
                    )
                )
            document.status, document.chunk_count, document.page_count = (
                "ready",
                len(chunks),
                page_count,
            )
            document.parser_version = chunks[0]["source_metadata"]["parser_version"]
            document.index_version = version
            connection.execute(
                update(table)
                .where(table.c.id == document.id)
                .values(status="ready", data=document.model_dump())
            )
            values = dict(
                session_id=document.session_id,
                collection=collection,
                index_version=version,
                corpus_hash=corpus_hash,
            )
            statement = insert(self.table("snapshots")).values(**values)
            connection.execute(
                statement.on_conflict_do_update(index_elements=["session_id"], set_=values)
            )

    def snapshot(self, session_id):
        table = self.table("snapshots")
        with self.engine.connect() as connection:
            row = connection.execute(
                select(table.c.collection, table.c.index_version, table.c.corpus_hash).where(
                    table.c.session_id == session_id
                )
            ).first()
        return tuple(row) if row else None

    def collections(self):
        with self.engine.connect() as connection:
            return set(connection.execute(select(self.table("snapshots").c.collection)).scalars())

    def expire(self, document):
        document.status = "expired"
        with self.transaction() as connection:
            connection.execute(
                update(self.table("documents"))
                .where(self.table("documents").c.id == document.id)
                .values(status="expired", data=document.model_dump())
            )
            connection.execute(
                delete(self.table("chunks")).where(
                    self.table("chunks").c.document_id == document.id
                )
            )

    def referenced_blobs(self):
        return {document.storage_key for document in self.documents()}


class ReadOnlyDocuments:
    def __init__(self, index, *, concurrency=8):
        self.index = index
        self.permits = threading.BoundedSemaphore(concurrency)

    @property
    def identity(self):
        return self.index.version

    async def search(self, arguments):
        import asyncio

        while not self.permits.acquire(blocking=False):
            await asyncio.sleep(0.01)

        def search():
            try:
                return self.index.search(arguments)
            finally:
                self.permits.release()

        return await asyncio.to_thread(search)
