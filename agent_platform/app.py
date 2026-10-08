import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse

from agent_platform.models import (
    CancelRequest, PlatformError, QuestionBatchStart, SessionCreate, Task, TaskCreate, TaskStatus,
    TERMINAL_STATUSES,
)
from agent_platform.runtime import AgentRuntime, FakeRuntime
from agent_platform.presentation import RESPONSE_STYLE_KEY, RESPONSE_STYLES
from agent_platform.safety import sanitize, validate_metadata
from agent_platform.service import TaskService
from agent_platform.storage import InMemoryTaskStore, TaskStore
from agent_platform.references import public_references


class LocalRateLimiter:
    """Process-local token buckets; replace with Redis in the durable deployment."""

    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], tuple[float, float]] = {}

    def consume(self, group: str, key: str, capacity: int, per_second: float) -> None:
        now = time.monotonic()
        tokens, updated = self._buckets.get((group, key), (float(capacity), now))
        tokens = min(capacity, tokens + (now - updated) * per_second)
        if tokens < 1:
            raise PlatformError("rate_limit_exceeded", 429)
        self._buckets[(group, key)] = (tokens - 1, now)


class StreamBudget:
    def __init__(self, total: int = 64, per_task: int = 8) -> None:
        self.total = total
        self.per_task = per_task
        self._counts: dict[str, int] = {}

    def acquire(self, task_id: str) -> None:
        if sum(self._counts.values()) >= self.total or self._counts.get(task_id, 0) >= self.per_task:
            raise PlatformError("sse_capacity_exceeded", 429)
        self._counts[task_id] = self._counts.get(task_id, 0) + 1

    def release(self, task_id: str) -> None:
        remaining = self._counts.get(task_id, 0) - 1
        if remaining > 0:
            self._counts[task_id] = remaining
        else:
            self._counts.pop(task_id, None)


def create_app(*, store: TaskStore | None = None, runtime: AgentRuntime | None = None,
               max_concurrency: int = 8, budget_seconds: float = 1200,
               finalize_reserve_seconds: float = 25, heartbeat_seconds: float = 15,
               poll_seconds: float = 0.1, rate_limits: bool = True, documents=None,
               task_service=None, limiter=None, event_transport=None, readiness=None,
               operational_health=None, question_dir=None) -> FastAPI:
    if not 0 < heartbeat_seconds <= 15 or poll_seconds <= 0:
        raise ValueError("invalid_stream_configuration")
    repository = store if store is not None else InMemoryTaskStore()
    runtime = runtime if runtime is not None else FakeRuntime()
    service = task_service or TaskService(repository, runtime, max_concurrency, budget_seconds,
                                         finalize_reserve_seconds)
    limiter = limiter or LocalRateLimiter()
    streams = StreamBudget()
    questions = None
    if question_dir is not None:
        from agent_platform.question_batches import QuestionBatchService
        questions = QuestionBatchService(question_dir, service)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            if documents:
                await documents.start()
            await service.start()
            if questions:
                await questions.start()
            yield
        finally:
            if questions:
                await questions.stop()
            await service.stop()
            if documents:
                await documents.stop()

    app = FastAPI(title="MathReasoning-Agent", version="0.1.0", lifespan=lifespan)
    from agent_platform.frontend import install_chat
    install_chat(app)
    app.state.service = service
    app.state.store = repository
    app.state.streams = streams
    app.state.documents = documents
    app.state.questions = questions
    if documents or questions:
        from agent_platform.rag.upload import UploadLimit
        app.add_middleware(UploadLimit)

    @app.exception_handler(PlatformError)
    async def platform_error(request: Request, exc: PlatformError):
        headers = {"Retry-After": "1"} if exc.status_code == 429 else {}
        return JSONResponse({"error": {"code": exc.code}}, exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # FastAPI's default validation response echoes invalid input values.
        return JSONResponse({"error": {"code": "invalid_request"}}, 400)

    def limit(group: str, key: str, capacity: int, per_second: float) -> None:
        if rate_limits:
            limiter.consume(group, key, capacity, per_second)

    def task_view(task: Task) -> dict:
        base = f"/v1/sessions/{task.session_id}/tasks/{task.id}"
        return sanitize({
            "id": task.id, "session_id": task.session_id, "status": task.status,
            "runtime_mode": task.runtime_mode, "current_stage": task.current_stage,
            "final_response": task.final_response, "error_code": task.error_code,
            "response_style": task.metadata.get(RESPONSE_STYLE_KEY),
            "references": public_references(task),
            "question_source": task.metadata.get("_question_source"),
            "accepted_at": task.accepted_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "deadline_at": task.deadline_at.isoformat() if task.deadline_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "active_runtime_limit_seconds": budget_seconds,
            "queue_position": repository.queue_position(task.id),
            "checkpoint_available": task.checkpoint is not None,
            "events_url": f"{base}/events", "status_url": base, "trace_url": f"{base}/trace",
        })

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/trace-viewer")

    @app.get("/trace-viewer", include_in_schema=False)
    async def trace_viewer():
        return FileResponse(Path(__file__).parent / "static" / "index.html",
                            headers={"Cache-Control": "no-store"})

    @app.get("/health/live")
    async def live():
        return {"status": "ok"}

    def readiness_view():
        status = 200 if service.accepting else 503
        if documents and not documents.accepting:
            status = 503
        if questions and (not questions.accepting or questions.worker.done()):
            status = 503
        try:
            if hasattr(repository, "ready"):
                repository.ready()
            if readiness:
                readiness()
        except Exception:
            status = 503
        return {
            "status": "ready" if status == 200 else "not_ready",
            "runtime_mode": runtime.name, "storage": getattr(repository, "name", "process_local"),
            "restart_durable": getattr(repository, "restart_durable", False),
            "document_search": "ready" if documents and documents.accepting else "unavailable",
            "response_styles": sorted(RESPONSE_STYLES),
            "server_history": True,
            "question_attachments": questions is not None,
            "question_submission": "explicit_send" if questions else None,
        }, status

    @app.get("/health/ready")
    async def ready():
        payload, status = await asyncio.to_thread(readiness_view)
        return JSONResponse(payload, status)

    @app.get("/health/summary")
    async def summary():
        payload, status = await asyncio.to_thread(readiness_view)
        if operational_health:
            try:
                operations = operational_health()
            except Exception:
                operations = {"status": "degraded", "reasons": ["monitor_unavailable"]}
            payload["operations"] = operations
            if status == 200 and operations["status"] != "ok":
                payload["status"] = "degraded"
        return JSONResponse(sanitize(payload), status)

    @app.post("/v1/sessions", status_code=201)
    async def create_session(request: Request, body: SessionCreate = SessionCreate()):
        limit("session", request.client.host if request.client else "local", 5, 5)
        session = repository.create_session(body.memory_token_limit)
        return {
            "id": session.id, "status": "active", "memory_token_limit": session.memory_token_limit,
            "created_at": session.created_at.isoformat(), "expires_at": None,
        }

    @app.get("/v1/sessions")
    async def sessions(request: Request,
                       limit_count: Annotated[int, Query(alias="limit", ge=1, le=50)] = 30,
                       cursor: Annotated[str | None, Query(max_length=512)] = None):
        limit("history", request.client.host if request.client else "local", 10, 10)
        return JSONResponse(sanitize(await asyncio.to_thread(repository.list_sessions, limit_count, cursor)),
                            headers={"Cache-Control": "no-store"})

    @app.get("/v1/sessions/{session_id}")
    async def session_details(session_id: str):
        limit("read", session_id, 20, 20)
        session = await asyncio.to_thread(repository.get_session, session_id)
        return JSONResponse({"id": session.id, "memory_token_limit": session.memory_token_limit,
                             "created_at": session.created_at.isoformat()}, headers={"Cache-Control": "no-store"})

    @app.get("/v1/sessions/{session_id}/tasks")
    async def task_history(session_id: str,
                           limit_count: Annotated[int, Query(alias="limit", ge=1, le=50)] = 20,
                           cursor: Annotated[str | None, Query(max_length=512)] = None):
        limit("read", session_id, 20, 20)
        def load():
            tasks, following = repository.list_tasks(session_id, limit_count, cursor)
            return {"items": [{**task_view(task), "problem": sanitize(task.problem)} for task in tasks],
                    "next_cursor": following}
        return JSONResponse(await asyncio.to_thread(load), headers={"Cache-Control": "no-store"})

    @app.post("/v1/sessions/{session_id}/tasks", status_code=202)
    async def submit(session_id: str, body: TaskCreate,
                     idempotency_key: Annotated[str | None, Header(max_length=128)] = None):
        limit("task_global", "deployment", 10, 10)
        limit("task_session", session_id, 2, 2)
        metadata = dict(body.metadata or {})
        if RESPONSE_STYLE_KEY in metadata or "_question_source" in metadata or "_question_instruction" in metadata:
            raise PlatformError("reserved_metadata_field", 400)
        if body.response_style is not None:
            metadata[RESPONSE_STYLE_KEY] = body.response_style
        check_selection = None
        if "document_ids" in metadata:
            from agent_platform.tools.schemas import DocumentArguments
            from pydantic import ValidationError
            try:
                selection = DocumentArguments(query="selection", session_id=session_id,
                                              document_ids=metadata["document_ids"]).document_ids
                if selection is None:
                    raise ValueError
            except (ValidationError, ValueError):
                raise PlatformError("invalid_document_selection", 400) from None
            def check_selection():
                for identifier in selection:
                    if not documents:
                        raise PlatformError("document_service_unavailable", 503)
                    if documents.get(session_id, identifier)["status"] != "ready":
                        raise PlatformError("document_not_ready", 409)
        metadata = validate_metadata(metadata)
        task = service.submit(session_id, body.problem, metadata,
                              idempotency_key, check_selection)
        return task_view(task)

    def question_service(session_id):
        repository.get_session(session_id)
        if not questions or not questions.accepting:
            raise PlatformError("question_service_unavailable", 503)
        return questions

    @app.post("/v1/sessions/{session_id}/question-batches", status_code=202)
    async def upload_questions(session_id: str, request: Request):
        batches = question_service(session_id)
        limit("upload", session_id, 2, 2 / 60)
        from starlette.datastructures import UploadFile
        from starlette.exceptions import HTTPException
        from agent_platform.tools.schemas import DocumentArguments
        from pydantic import ValidationError
        import json
        try:
            async with request.form(max_files=1, max_fields=2, max_part_size=8000) as form:
                file = form.get("file")
                if (not isinstance(file, UploadFile) or len(form.getlist("file")) != 1
                        or set(form) - {"file", "response_style", "document_ids"}
                        or any(len(form.getlist(key)) > 1 for key in ("response_style", "document_ids"))):
                    raise PlatformError("invalid_request", 400)
                style = form.get("response_style", "auto")
                if style not in RESPONSE_STYLES:
                    raise PlatformError("invalid_request", 400)
                try:
                    raw_ids = json.loads(form.get("document_ids", "[]"))
                    ids = DocumentArguments(query="selection", session_id=session_id, document_ids=raw_ids).document_ids
                    if ids is None:
                        raise ValueError
                except (TypeError, ValueError, ValidationError):
                    raise PlatformError("invalid_document_selection", 400) from None
                for identifier in ids:
                    if not documents:
                        raise PlatformError("document_service_unavailable", 503)
                    if documents.get(session_id, identifier)["status"] != "ready":
                        raise PlatformError("document_not_ready", 409)
                item = await batches.upload(session_id, file, {"response_style": style, "document_ids": sorted(set(ids))})
                return batches.view(item, task_view)
        except HTTPException as exc:
            raise PlatformError("file_too_large" if exc.detail == "file_too_large" else "invalid_request",
                                413 if exc.detail == "file_too_large" else 400) from None

    @app.get("/v1/sessions/{session_id}/question-batches")
    async def question_list(session_id: str,
                            limit_count: Annotated[int, Query(alias="limit", ge=1, le=10)] = 10,
                            cursor: Annotated[str | None, Query(max_length=512)] = None):
        batches = question_service(session_id)
        limit("read", session_id, 20, 20)
        rows, following = batches.catalog.page(session_id, limit_count, cursor)
        return JSONResponse({"items": [batches.view(item, task_view, detail=False) for item in rows],
                            "next_cursor": following}, headers={"Cache-Control": "no-store"})

    @app.get("/v1/sessions/{session_id}/question-batches/{batch_id}")
    async def question_details(session_id: str, batch_id: str):
        batches = question_service(session_id)
        limit("read", session_id, 20, 20)
        return JSONResponse(batches.view(batches.catalog.get(session_id, batch_id), task_view),
                            headers={"Cache-Control": "no-store"})

    @app.post("/v1/sessions/{session_id}/question-batches/{batch_id}/start", status_code=202)
    async def start_questions(session_id: str, batch_id: str, body: QuestionBatchStart):
        batches = question_service(session_id)
        limit("mutation", session_id, 10, 10)
        return batches.view(batches.begin(session_id, batch_id, body.prompt, body.response_style), task_view)

    @app.post("/v1/sessions/{session_id}/question-batches/{batch_id}/cancel")
    async def cancel_questions(session_id: str, batch_id: str):
        batches = question_service(session_id)
        limit("mutation", session_id, 10, 10)
        return batches.view(batches.cancel(session_id, batch_id), task_view)

    @app.post("/v1/sessions/{session_id}/question-batches/{batch_id}/questions/{number}/retry", status_code=202)
    async def retry_question(session_id: str, batch_id: str, number: int):
        batches = question_service(session_id)
        limit("mutation", session_id, 10, 10)
        return batches.view(batches.retry(session_id, batch_id, number), task_view)

    @app.get("/v1/sessions/{session_id}/documents")
    async def document_list(session_id: str,
                            limit_count: Annotated[int, Query(alias="limit", ge=1, le=50)] = 20,
                            cursor: Annotated[str | None, Query(max_length=512)] = None):
        limit("read", session_id, 20, 20)
        await asyncio.to_thread(repository.get_session, session_id)
        if not documents:
            raise PlatformError("document_service_unavailable", 503)
        return JSONResponse(await asyncio.to_thread(documents.list, session_id, limit_count, cursor),
                            headers={"Cache-Control": "no-store"})

    @app.post("/v1/sessions/{session_id}/documents", status_code=202)
    async def upload_document(session_id: str, request: Request):
        repository.get_session(session_id)
        limit("upload", session_id, 2, 2 / 60)
        if not documents or not documents.accepting:
            raise PlatformError("document_service_unavailable", 503)
        from starlette.datastructures import UploadFile
        from starlette.exceptions import HTTPException
        try:
            async with request.form(max_files=1, max_fields=3, max_part_size=1024) as form:
                file = form.get("file")
                if (not isinstance(file, UploadFile) or len(form.getlist("file")) != 1
                        or set(form) - {"file", "domain", "problem_type", "source"}):
                    raise PlatformError("invalid_request", 400)
                fields = {key: form.get(key) for key in ("domain", "problem_type", "source")}
                if any(value is not None and not isinstance(value, str) for value in fields.values()):
                    raise PlatformError("invalid_request", 400)
                return await documents.upload(session_id, file, **fields)
        except HTTPException as exc:
            if exc.detail == "file_too_large":
                raise PlatformError("file_too_large", 413) from None
            raise PlatformError("invalid_request", 400) from None

    @app.get("/v1/sessions/{session_id}/documents/{document_id}")
    async def document_status(session_id: str, document_id: str):
        repository.get_session(session_id)
        limit("read", session_id, 20, 20)
        if not documents:
            raise PlatformError("document_service_unavailable", 503)
        return documents.get(session_id, document_id)

    @app.get("/v1/sessions/{session_id}/tasks/{task_id}")
    async def task_status(session_id: str, task_id: str):
        limit("read", session_id, 20, 20)
        return task_view(repository.get_task(session_id, task_id))

    @app.post("/v1/sessions/{session_id}/tasks/{task_id}/cancel")
    async def cancel(session_id: str, task_id: str, body: CancelRequest = CancelRequest()):
        limit("mutation", session_id, 10, 10)
        return task_view(service.cancel(session_id, task_id))

    @app.post("/v1/sessions/{session_id}/tasks/{task_id}/resume", status_code=202)
    async def resume(session_id: str, task_id: str):
        limit("mutation", session_id, 10, 10)
        return task_view(service.resume(session_id, task_id))

    @app.get("/v1/sessions/{session_id}/tasks/{task_id}/trace")
    async def trace(session_id: str, task_id: str,
                    after_sequence: Annotated[int, Query(ge=0)] = 0,
                    limit_count: Annotated[int, Query(alias="limit", ge=1, le=500)] = 100):
        limit("read", session_id, 20, 20)
        events = (event_transport or repository).events_after(session_id, task_id, after_sequence, limit_count)
        return {
            "events": [event.model_dump(mode="json") for event in events],
            "next_sequence": events[-1].sequence if events else after_sequence,
        }

    @app.get("/v1/sessions/{session_id}/tasks/{task_id}/events")
    async def events(request: Request, session_id: str, task_id: str,
                     after: Annotated[int, Query(ge=0)] = 0,
                     last_event_id: Annotated[str | None, Header()] = None):
        limit("read", session_id, 20, 20)
        try:
            cursor = int(last_event_id) if last_event_id is not None else after
        except ValueError:
            raise PlatformError("invalid_cursor", 400) from None
        if cursor < 0:
            raise PlatformError("invalid_cursor", 400)
        repository.events_after(session_id, task_id, cursor)
        streams.acquire(task_id)

        async def frames():
            sequence = cursor
            last_sent = time.monotonic()
            while not await request.is_disconnected():
                batch = (event_transport or repository).events_after(session_id, task_id, sequence)
                for event in batch:
                    yield event.sse_frame()
                    sequence = event.sequence
                    last_sent = time.monotonic()
                task = repository.get_task(session_id, task_id)
                # Interrupted work closes the connection; explicit resume can reconnect.
                if task.status in TERMINAL_STATUSES | {TaskStatus.INTERRUPTED}:
                    if not repository.events_after(session_id, task_id, sequence):
                        break
                    continue
                if time.monotonic() - last_sent >= heartbeat_seconds:
                    yield ": heartbeat\n\n"
                    last_sent = time.monotonic()
                await asyncio.sleep(poll_seconds)

        async def stream():
            try:
                async for frame in frames():
                    yield frame
            finally:
                streams.release(task_id)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no",
            "Referrer-Policy": "no-referrer",
        })

    return app


app = create_app()
