"""Single-owner durable question batches dispatch into the existing Task service."""

import asyncio
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import threading
from functools import wraps
from uuid import uuid4

from agent_platform.history import cursor_parts, member, page_cursor
from agent_platform.models import PlatformError, TERMINAL_STATUSES, TaskStatus, utc_now
from agent_platform.presentation import RESPONSE_STYLE_KEY, RESPONSE_STYLES
from agent_platform.questions_parser import SOURCE_KEY, INSTRUCTION_KEY
from agent_platform.rag.isolation import ParserFailure, isolated_parse
from agent_platform.rag.models import MAX_BYTES
from agent_platform.safety import sanitize, sanitize_text


ACTIVE = {"parsing", "solving"}


def synchronized(method):
    @wraps(method)
    def locked(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return locked


class QuestionCatalog:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL, content_hash TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, data TEXT NOT NULL,
                UNIQUE(session_id,content_hash));
            CREATE INDEX IF NOT EXISTS batches_session_order ON batches(session_id,created_at,id);
            CREATE INDEX IF NOT EXISTS batches_status ON batches(status);
        """)

    @synchronized
    def close(self):
        self.connection.close()

    @synchronized
    def duplicate(self, session_id, digest):
        row = self.connection.execute("SELECT data FROM batches WHERE session_id=? AND content_hash=?", (session_id, digest)).fetchone()
        return json.loads(row[0]) if row else None

    @synchronized
    def create(self, item):
        with self.connection:
            if self.connection.execute("SELECT count(*) FROM batches WHERE status IN ('parsing','solving')").fetchone()[0] >= 16:
                raise PlatformError("question_capacity_exceeded", 429)
            if self.connection.execute("SELECT count(*) FROM batches WHERE session_id=? AND status IN ('parsing','solving')", (item["session_id"],)).fetchone()[0]:
                raise PlatformError("question_batch_active", 409)
            self.connection.execute("INSERT INTO batches VALUES (?,?,?,?,?,?)", (
                item["id"], item["session_id"], item["content_hash"], item["status"], item["created_at"], json.dumps(item, ensure_ascii=False)))

    @synchronized
    def save(self, item):
        with self.connection:
            self.connection.execute("UPDATE batches SET status=?,data=? WHERE id=? AND session_id=?", (
                item["status"], json.dumps(item, ensure_ascii=False), item["id"], item["session_id"]))

    @synchronized
    def activate(self, session_id, identifier, instruction, style):
        with self.connection:
            item = self.get(session_id, identifier)
            if item["status"] != "ready":
                if item.get("instruction") == instruction and item.get("start_style") == style:
                    return item
                raise PlatformError("question_not_ready" if item["status"] == "parsing" else "question_start_conflict", 409)
            if self.connection.execute("SELECT count(*) FROM batches WHERE status IN ('parsing','solving')").fetchone()[0] >= 16:
                raise PlatformError("question_capacity_exceeded", 429)
            if self.connection.execute("SELECT count(*) FROM batches WHERE session_id=? AND status IN ('parsing','solving')", (session_id,)).fetchone()[0]:
                raise PlatformError("question_batch_active", 409)
            item.update(status="solving", instruction=instruction, start_style=style)
            self.connection.execute("UPDATE batches SET status=?,data=? WHERE id=? AND session_id=?", (
                item["status"], json.dumps(item, ensure_ascii=False), identifier, session_id))
            return item

    @synchronized
    def get(self, session_id, identifier):
        row = self.connection.execute("SELECT data FROM batches WHERE session_id=? AND id=?", (session_id, identifier)).fetchone()
        if not row:
            raise PlatformError("question_batch_not_found", 404)
        return json.loads(row[0])

    @synchronized
    def active(self):
        return [json.loads(row[0]) for row in self.connection.execute("""SELECT data FROM batches
            WHERE status IN ('parsing','solving') OR (status='cancelled' AND coalesce(json_extract(data,'$.cancel_reconciled'),0)=0)
            ORDER BY created_at,id LIMIT 32""")]

    @synchronized
    def page(self, session_id, limit, cursor=None):
        scope = "question-batches:" + session_id
        boundary = cursor_parts(cursor, scope)
        query = "SELECT data FROM batches WHERE session_id=?"
        args = [session_id]
        if boundary:
            query += " AND (created_at,id) < (?,?)"
            args.extend([boundary[0].isoformat(), boundary[1]])
        query += " ORDER BY created_at DESC,id DESC LIMIT ?"
        args.append(limit + 1)
        rows = [json.loads(row[0]) for row in self.connection.execute(query, args)]
        following = page_cursor([member(datetime.fromisoformat(row["created_at"]), row["id"]) for row in rows], limit, scope)
        return rows[:limit], following


class QuestionBatchService:
    def __init__(self, root, tasks, *, parser=isolated_parse, poll_seconds=.5):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.owner = (self.root / "owner.lock").open("a+b")
        if (self.root / "owner.lock").stat().st_size == 0:
            self.owner.write(b"0")
            self.owner.flush()
        self.owner.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(self.owner.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.catalog = QuestionCatalog(self.root / "batches.sqlite")
        except BaseException:
            self.owner.close()
            raise
        self.tasks, self.parser, self.poll_seconds = tasks, parser, poll_seconds
        self.worker = None
        self.accepting = False

    async def start(self):
        self.accepting = True
        self.worker = asyncio.create_task(self._work())

    async def stop(self):
        self.accepting = False
        if self.worker:
            self.worker.cancel()
            await asyncio.gather(self.worker, return_exceptions=True)
        self.catalog.close()
        self.owner.close()

    async def upload(self, session_id, file, options):
        if not self.accepting:
            raise PlatformError("question_service_unavailable", 503)
        expected = {".pdf": "application/pdf", ".md": "text/markdown", ".markdown": "text/markdown"}.get(Path(file.filename or "").suffix.lower())
        if not expected:
            raise PlatformError("unsupported_media_type", 415)
        if file.content_type != expected:
            raise PlatformError("media_mismatch", 400)
        if shutil.disk_usage(self.root).free < MAX_BYTES + 64 * 1024 * 1024:
            raise PlatformError("storage_capacity_exceeded", 503)
        identifier = str(uuid4())
        temporary = self.root / (identifier + ".upload")
        digest, size, signature = hashlib.sha256(), 0, b""
        try:
            with temporary.open("xb") as output:
                while part := await file.read(65536):
                    size += len(part)
                    if size > MAX_BYTES:
                        raise PlatformError("file_too_large", 413)
                    digest.update(part)
                    signature = (signature + part)[:1024]
                    output.write(part)
                output.flush()
                os.fsync(output.fileno())
            if not size:
                raise PlatformError("empty_document", 400)
            pdf = signature.startswith(b"%PDF-")
            if ((expected == "application/pdf" and not pdf) or (expected == "text/markdown" and
                    (pdf or b"\x00" in signature or signature.startswith(b"PK\x03\x04")))):
                raise PlatformError("media_mismatch", 400)
            previous = self.catalog.duplicate(session_id, digest.hexdigest())
            if previous:
                if previous["options"] != options:
                    raise PlatformError("question_upload_conflict", 409)
                return previous
            key = "blobs/" + identifier
            final = self.root / key
            final.parent.mkdir(exist_ok=True)
            temporary.replace(final)
            item = {"id": identifier, "session_id": session_id, "status": "parsing",
                "original_name": sanitize_text((file.filename or "questions").replace("\\", "/").split("/")[-1])[:200],
                "media_type": expected, "size_bytes": size, "content_hash": digest.hexdigest(),
                "storage_key": key, "created_at": utc_now().isoformat(), "questions": [],
                "options": options, "error_code": None, "page_count": None, "split_method": None}
            try:
                self.catalog.create(item)
            except BaseException:
                final.unlink(missing_ok=True)
                raise
            return item
        finally:
            temporary.unlink(missing_ok=True)

    async def _work(self):
        while self.accepting:
            try:
                for item in self.catalog.active():
                    try:
                        if item["status"] == "cancelled":
                            self._cancel_tasks(item)
                        else:
                            await self._advance(item)
                    except PlatformError as exc:
                        if exc.status_code not in {429, 503}:
                            current = self.catalog.get(item["session_id"], item["id"])
                            current.update(status="failed", error_code=exc.code)
                            self.catalog.save(current)
                    except sqlite3.Error:
                        pass  # Replay the idempotent submission after a catalog outage.
                    except Exception:
                        current = self.catalog.get(item["session_id"], item["id"])
                        current.update(status="failed", error_code="question_processing_failed")
                        self.catalog.save(current)
            except Exception:
                pass  # Storage outages retry discovery; accepted records stay authoritative.
            await asyncio.sleep(self.poll_seconds)

    async def _advance(self, item):
        session, identifier = item["session_id"], item["id"]
        self.tasks.store.get_session(session)
        if item["status"] == "parsing":
            try:
                path = self.root / item["storage_key"]
                if hashlib.sha256(path.read_bytes()).hexdigest() != item["content_hash"]:
                    raise ParserFailure("blob_integrity_failed")
                parsed = await self.parser(path, item["media_type"], questions=True)
            except ParserFailure as exc:
                current = self.catalog.get(session, identifier)
                if current["status"] == "parsing":
                    current.update(status="failed", error_code=str(exc))
                    self.catalog.save(current)
                return
            item = self.catalog.get(session, identifier)
            if item["status"] != "parsing":
                return
            item.update(status="ready", page_count=parsed.page_count, split_method=parsed.split_method,
                        questions=[{**question.model_dump(), "task_id": None, "attempt": 0} for question in parsed.questions])
            self.catalog.save(item)
            return
        if item["status"] != "solving":
            return
        for question in item["questions"]:
            task_id = question["task_id"]
            if task_id:
                task = self.tasks.store.get_task(session, task_id)
                if task.status not in TERMINAL_STATUSES:
                    return
                continue
            source = {"batch_id": identifier, "number": question["number"], "label": question["label"],
                      "filename": item["original_name"], "page_start": question["page_start"], "page_end": question["page_end"]}
            metadata = {SOURCE_KEY: source, "document_ids": item["options"]["document_ids"],
                        RESPONSE_STYLE_KEY: item.get("start_style", item["options"]["response_style"])}
            if item.get("instruction"):
                metadata[INSTRUCTION_KEY] = item["instruction"]
            task = self.tasks.submit(session, question["problem"], metadata,
                                     f"question:{identifier}:{question['number']}:{question['attempt']}")
            question["task_id"] = task.id
            self.catalog.save(item)
            return
        item["status"] = "completed"
        self.catalog.save(item)

    def begin(self, session_id, identifier, prompt, style):
        if not self.accepting:
            raise PlatformError("question_service_unavailable", 503)
        if not isinstance(prompt, str) or len(prompt) > 4000 or style not in RESPONSE_STYLES:
            raise PlatformError("invalid_request", 400)
        return self.catalog.activate(session_id, identifier, sanitize_text(prompt.strip()), style)

    def cancel(self, session_id, identifier):
        item = self.catalog.get(session_id, identifier)
        if item["status"] not in ACTIVE | {"ready", "cancelled"}:
            raise PlatformError("question_batch_terminal", 409)
        item["status"] = "cancelled"
        self.catalog.save(item)
        self._cancel_tasks(item)
        return item

    def _cancel_tasks(self, item):
        for question in item["questions"]:
            task = (self.tasks.store.get_task(item["session_id"], question["task_id"]) if question["task_id"]
                    else self.tasks.store.lookup_submission(item["session_id"],
                        f"question:{item['id']}:{question['number']}:{question['attempt']}"))
            if task and task.metadata.get(SOURCE_KEY, {}).get("batch_id") == item["id"]:
                question["task_id"] = task.id
                if task.status not in TERMINAL_STATUSES:
                    try:
                        self.tasks.cancel(item["session_id"], task.id)
                    except PlatformError as exc:
                        if exc.code != "task_already_terminal":
                            raise
        item["cancel_reconciled"] = True
        self.catalog.save(item)

    def retry(self, session_id, identifier, number):
        item = self.catalog.get(session_id, identifier)
        if item["status"] not in {"solving", "completed"} or not 1 <= number <= len(item["questions"]):
            raise PlatformError("question_not_retryable", 409)
        question = item["questions"][number - 1]
        if not question["task_id"]:
            raise PlatformError("question_not_retryable", 409)
        task = self.tasks.store.get_task(session_id, question["task_id"])
        if task.status not in {TaskStatus.FAILED, TaskStatus.CANCELLED} or question["attempt"] >= 2:
            raise PlatformError("question_not_retryable", 409)
        if any(other["session_id"] == session_id and other["id"] != identifier and other["status"] in ACTIVE
               for other in self.catalog.active()):
            raise PlatformError("question_batch_active", 409)
        # Retry is explicit and receives a new Task; accepted task IDs remain in history.
        question.update(task_id=None, attempt=question["attempt"] + 1)
        item["status"] = "solving"
        self.catalog.save(item)
        return item

    def view(self, item, task_view, *, detail=True):
        result = {key: item[key] for key in ("id", "session_id", "status", "original_name", "size_bytes", "created_at", "error_code", "page_count", "split_method")}
        result["question_count"] = len(item["questions"])
        result["response_style"] = item.get("start_style", item["options"]["response_style"])
        result["user_instruction"] = item.get("instruction", "")
        questions = []
        for question in item["questions"]:
            task = self.tasks.store.get_task(item["session_id"], question["task_id"]) if question["task_id"] else None
            questions.append({**{key: question[key] for key in ("number", "label", "problem", "page_start", "page_end", "attempt")},
                              "status": task.status if task else "cancelled" if item["status"] == "cancelled" else "pending",
                              "task": task_view(task) if task and detail else None})
        result["counts"] = {status: sum(row["status"] == status for row in questions)
                            for status in ("pending", *[str(value) for value in TaskStatus])}
        if detail:
            result["questions"] = questions
        return sanitize(result)
