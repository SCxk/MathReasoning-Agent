"""Single-owner, restartable ingestion with atomic snapshot publication."""

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import shutil
import threading
from uuid import uuid4

from pydantic import ValidationError

from agent_platform.models import PlatformError
from agent_platform.safety import sanitize, sanitize_text
from agent_platform.rag.catalog import DocumentCatalog
from agent_platform.rag.isolation import ParserFailure, isolated_parse
from agent_platform.rag.models import Document, MAX_BYTES


class DocumentService:
    def __init__(self, root, embedder, *, client=None, parser=isolated_parse, catalog=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        # An OS lock is held until every indexing thread has actually finished.
        self.owner = (self.root / "owner.lock").open("a+b")
        if (self.root / "owner.lock").stat().st_size == 0:
            self.owner.write(b"0")
            self.owner.flush()
        self.owner.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.owner.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.owner.close()
            raise ValueError("document_store_already_owned") from None
        try:
            from qdrant_client import QdrantClient
            from agent_platform.rag.index import HybridIndex
            self.catalog = catalog or DocumentCatalog(self.root / "catalog.sqlite")
            self.client = client or QdrantClient(path=str(self.root / "qdrant"))
            self.index = HybridIndex(self.client, self.catalog, embedder,
                                     lock=getattr(self.catalog,'index_lock',None))
        except BaseException:
            if hasattr(self, 'catalog'):
                self.catalog.close()
            self.owner.close()
            raise
        self.parser = parser
        self.accepting = False
        self.stopping = False
        self.worker = None
        self.signal = asyncio.Event()
        self.permits = threading.BoundedSemaphore(8)

    @property
    def identity(self):
        return self.index.version

    async def start(self):
        await asyncio.to_thread(self.maintenance)
        self.accepting = True
        self.worker = asyncio.create_task(self._work())

    async def stop(self):
        self.accepting, self.stopping = False, True
        self.signal.set()
        if self.worker:
            await self.worker
        # Search callers retain permits until their underlying threads exit.
        for _ in range(8):
            await asyncio.to_thread(self.permits.acquire)
        self.client.close()
        self.catalog.close()
        self.owner.close()

    def maintenance(self):
        now = datetime.now(timezone.utc)
        for document in self.catalog.documents():
            if datetime.fromisoformat(document.expires_at) <= now:
                self.catalog.expire(document)
                self.index.purge(document.id)
                (self.root / document.storage_key).unlink(missing_ok=True)
        referenced = self.catalog.referenced_blobs()
        for folder in (self.root / "blobs", self.root / "quarantine"):
            if folder.exists():
                for path in folder.rglob("*"):
                    if path.is_file() and not path.is_symlink() and (
                            path.relative_to(self.root).as_posix() not in referenced
                            and now.timestamp() - path.stat().st_mtime > 3600):
                        path.unlink()
        self.index.reconcile()

    async def upload(self, session_id, file, *, domain=None, problem_type=None, source=None):
        if not self.accepting:
            raise PlatformError("document_service_unavailable", 503)
        suffix = Path(file.filename or "").suffix.lower()
        expected = {".pdf": "application/pdf", ".md": "text/markdown", ".markdown": "text/markdown"}.get(suffix)
        if expected is None:
            raise PlatformError("unsupported_media_type", 415)
        if file.content_type != expected:
            raise PlatformError("media_mismatch", 400)
        if shutil.disk_usage(self.root).free < MAX_BYTES + 64 * 1024 * 1024:
            raise PlatformError("storage_capacity_exceeded", 503)
        identifier = str(uuid4())
        temporary = self.root / "quarantine" / identifier
        temporary.parent.mkdir(exist_ok=True)
        digest, size, signature = hashlib.sha256(), 0, b""
        try:
            with temporary.open("xb") as output:
                while part := await file.read(64 * 1024):
                    size += len(part)
                    if size > MAX_BYTES:
                        raise PlatformError("file_too_large", 413)
                    signature = (signature + part)[:1024]
                    digest.update(part)
                    output.write(part)
                output.flush()
                os.fsync(output.fileno())
            if not size:
                raise PlatformError("empty_document", 400)
            is_pdf = signature.startswith(b"%PDF-")
            if (expected == "application/pdf" and not is_pdf) or (
                    expected == "text/markdown" and (is_pdf or b"\x00" in signature or signature.startswith(b"PK\x03\x04"))):
                raise PlatformError("media_mismatch", 400)
            now = datetime.now(timezone.utc)
            key = f"blobs/{session_id}/{digest.hexdigest()}"
            try:
                document = Document(id=identifier, session_id=session_id,
                    original_name=sanitize_text((file.filename or "document").replace("\\", "/").split("/")[-1])[:200],
                    media_type=expected, size_bytes=size, content_hash=digest.hexdigest(), storage_key=key,
                    domain=sanitize_text(domain) if isinstance(domain, str) else domain,
                    problem_type=sanitize_text(problem_type) if isinstance(problem_type, str) else problem_type,
                    source=sanitize_text(source) if isinstance(source, str) else source,
                    created_at=now.isoformat(), expires_at=(now + timedelta(days=90)).isoformat())
            except ValidationError:
                raise PlatformError("invalid_document_metadata", 400) from None
            final = self.root / key
            final.parent.mkdir(parents=True, exist_ok=True)
            # Same-content replay cannot overwrite a live blob; the unique row rejects it.
            if not final.exists():
                temporary.replace(final)
            self.catalog.reserve(document)
            self.signal.set()
            return sanitize(document.projection())
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, session_id, document_id):
        return self._projection(self.catalog.get(session_id, document_id))

    @staticmethod
    def _projection(document):
        item = document.projection()
        if datetime.fromisoformat(document.expires_at) <= datetime.now(timezone.utc):
            item["status"] = "expired"
        return sanitize(item)

    def list(self, session_id, limit, cursor=None):
        rows, following = self.catalog.list_page(session_id, limit, cursor)
        return {"items": [self._projection(row) for row in rows], "next_cursor": following}

    async def search(self, arguments):
        while not self.permits.acquire(blocking=False):
            if not self.accepting:
                raise ValueError("document_service_unavailable")
            await asyncio.sleep(.01)
        def search():
            try:
                if not self.accepting:
                    raise ValueError("document_service_unavailable")
                return self.index.search(arguments)
            finally:
                self.permits.release()
        return await asyncio.to_thread(search)

    async def _work(self):
        while not self.stopping:
            self.signal.clear()
            for document in self.catalog.documents(status="indexing"):
                if self.stopping:
                    break
                try:
                    if datetime.fromisoformat(document.expires_at) <= datetime.now(timezone.utc):
                        self.catalog.expire(document)
                        continue
                    path = self.root / document.storage_key
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != document.content_hash:
                        raise ParserFailure("blob_integrity_failed")
                    parsed = await self.parser(path, document.media_type)
                    await asyncio.to_thread(self.index.ingest, document, parsed)
                except ParserFailure as exc:
                    self.catalog.fail(document, str(exc))
                except Exception:
                    self.catalog.fail(document, "indexing_failed")
            try:
                await asyncio.wait_for(self.signal.wait(), 10)
            except TimeoutError:
                try:
                    await asyncio.to_thread(self.maintenance)
                except Exception:
                    self.accepting = False
                    self.stopping = True
