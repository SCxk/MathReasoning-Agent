import copy
import hashlib
import json
import threading
from datetime import timedelta
from typing import Any, Callable, Protocol

from agent_platform.models import (
    Message, PlatformError, Session, Task, TaskStatus, TERMINAL_STATUSES,
    TraceEvent, new_id, utc_now,
)
from agent_platform.safety import sanitize, sanitize_text
from agent_platform.history import cursor_member, member, page_cursor, session_summary


class TaskStore(Protocol):
    def list_sessions(self, limit: int, cursor: str | None = None) -> dict: ...
    def list_tasks(self, session_id: str, limit: int,
                   cursor: str | None = None) -> tuple[list[Task], str | None]: ...
    def tool_record(self, session_id: str, task_id: str, generation: int,
                    call_id: str, entry: dict, event_type: str, payload: dict) -> None: ...
    def record(self, session_id: str, task_id: str, generation: int,
               stage: str, event_type: str, payload: dict[str, Any]) -> None: ...
    def reject_checkpoint(self, session_id: str, task_id: str) -> None: ...
    def create_session(self, memory_token_limit: int) -> Session: ...
    def get_session(self, session_id: str) -> Session: ...
    def create_task(self, session_id: str, problem: str, metadata: dict[str, Any],
                    runtime_mode: str, idempotency_key: str | None,
                    before_create: Callable[[], None] | None = None) -> tuple[Task, bool]: ...
    def get_task(self, session_id: str, task_id: str) -> Task: ...
    def lookup_submission(self, session_id: str, key: str) -> Task | None: ...
    def list_queued(self) -> list[Task]: ...
    def queue_position(self, task_id: str) -> int | None: ...
    def start(self, session_id: str, task_id: str, budget_seconds: float) -> Task | None: ...
    def progress(self, session_id: str, task_id: str, generation: int,
                 stage: str, completed: bool, checkpoint: dict[str, Any] | None) -> None: ...
    def finish(self, session_id: str, task_id: str, generation: int,
               status: TaskStatus, final_response: str | None = None,
               error_code: str | None = None) -> Task: ...
    def cancel(self, session_id: str, task_id: str) -> Task: ...
    def resume(self, session_id: str, task_id: str) -> tuple[Task, bool]: ...
    def events_after(self, session_id: str, task_id: str, sequence: int,
                     limit: int = 500) -> list[TraceEvent]: ...


class InMemoryTaskStore:
    """Atomic process-local reference adapter; no restart durability."""

    name = "process_local"
    restart_durable = False

    def __init__(self, max_queued: int = 256) -> None:
        self.max_queued = max_queued
        self._sessions: dict[str, Session] = {}
        self._tasks: dict[str, Task] = {}
        self._idempotency: dict[tuple[str, str], tuple[str, str]] = {}
        self._lock = threading.RLock()

    def create_session(self, memory_token_limit: int) -> Session:
        with self._lock:
            session = Session(id=new_id(), memory_token_limit=memory_token_limit)
            self._sessions[session.id] = session
            return copy.deepcopy(session)

    def get_session(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise PlatformError("session_not_found", 404)
            return copy.deepcopy(session)

    def list_sessions(self, limit: int, cursor: str | None = None) -> dict:
        boundary = cursor_member(cursor, "sessions")
        with self._lock:
            sessions = sorted(self._sessions.values(), key=lambda item: member(item.created_at, item.id), reverse=True)
            sessions = [item for item in sessions if boundary is None or member(item.created_at, item.id) < boundary][:limit + 1]
            return {
                "items": [session_summary(item, [task for task in self._tasks.values() if task.session_id == item.id])
                          for item in sessions[:limit]],
                "next_cursor": page_cursor([member(item.created_at, item.id) for item in sessions], limit, "sessions"),
            }

    def list_tasks(self, session_id: str, limit: int,
                   cursor: str | None = None) -> tuple[list[Task], str | None]:
        scope = "tasks:" + session_id
        boundary = cursor_member(cursor, scope)
        with self._lock:
            self.get_session(session_id)
            tasks = sorted((task for task in self._tasks.values() if task.session_id == session_id),
                           key=lambda item: member(item.accepted_at, item.id), reverse=True)
            tasks = [item for item in tasks if boundary is None or member(item.accepted_at, item.id) < boundary][:limit + 1]
            return copy.deepcopy(tasks[:limit]), page_cursor([member(item.accepted_at, item.id) for item in tasks], limit, scope)

    def _task(self, session_id: str, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if task is None or task.session_id != session_id:
            raise PlatformError("task_not_found", 404)
        return task

    def get_task(self, session_id: str, task_id: str) -> Task:
        with self._lock:
            return copy.deepcopy(self._task(session_id, task_id))

    def lookup_submission(self, session_id: str, key: str) -> Task | None:
        with self._lock:
            self.get_session(session_id)
            original = self._idempotency.get((session_id, key))
            return copy.deepcopy(self._task(session_id, original[0])) if original else None

    def _check_capacity(self) -> None:
        if sum(t.status == TaskStatus.QUEUED for t in self._tasks.values()) >= self.max_queued:
            raise PlatformError("queue_capacity_exceeded", 429)

    def create_task(self, session_id: str, problem: str, metadata: dict[str, Any],
                    runtime_mode: str, idempotency_key: str | None,
                    before_create: Callable[[], None] | None = None) -> tuple[Task, bool]:
        with self._lock:
            session = self.get_session(session_id)
            fingerprint = hashlib.sha256(json.dumps(
                {"problem": problem, "metadata": metadata}, sort_keys=True,
                ensure_ascii=False, allow_nan=False,
            ).encode()).hexdigest()
            key = (session_id, idempotency_key)
            if idempotency_key and key in self._idempotency:
                task_id, original = self._idempotency[key]
                if fingerprint != original:
                    raise PlatformError("idempotency_conflict", 409)
                return copy.deepcopy(self._task(session_id, task_id)), False
            self._check_capacity()
            # Validate external prerequisites only for new tasks, not accepted retries.
            if before_create:
                before_create()
            # Conservatively budget characters: each Unicode character costs at most
            # four UTF-8 bytes, and treating every byte as a token avoids overfill.
            remaining = 0 if "_question_source" in metadata else session.memory_token_limit
            memory: list[Message] = []
            for message in reversed(session.messages):
                size = len(message.content.encode("utf-8"))
                if size > remaining:
                    break
                memory.append(message)
                remaining -= size
            task = Task(
                id=new_id(), session_id=session_id, problem=problem,
                metadata=copy.deepcopy(metadata), memory=tuple(reversed(memory)),
                runtime_mode=runtime_mode,
            )
            self._tasks[task.id] = task
            self._sessions[session_id].messages.append(Message(
                id=new_id(), role="user", content=sanitize_text(problem), task_id=task.id,
            ))
            if idempotency_key:
                self._idempotency[key] = (task.id, fingerprint)
            self._event(task, "task.accepted", "system", {
                "status": task.status, "queue_position": self.queue_position(task.id),
            })
            return copy.deepcopy(task), True

    def list_queued(self) -> list[Task]:
        with self._lock:
            return [copy.deepcopy(t) for t in self._tasks.values() if t.status == TaskStatus.QUEUED]

    def queue_position(self, task_id: str) -> int | None:
        with self._lock:
            queued = [t.id for t in self._tasks.values() if t.status == TaskStatus.QUEUED]
            return queued.index(task_id) + 1 if task_id in queued else None

    def _event(self, task: Task, event_type: str, stage_id: str,
               payload: dict[str, Any]) -> None:
        operation_id = payload.get("operation_id")
        if event_type == "model.started":
            call_type = payload["call_type"]
            task.model_calls[call_type] = task.model_calls.get(call_type, 0) + 1
        if operation_id:
            if event_type.endswith(".started"):
                task.active_operations[operation_id] = {"family": event_type.split(".")[0], "stage": stage_id}
            elif event_type.endswith((".completed", ".failed", ".interrupted")):
                task.active_operations.pop(operation_id, None)
        task.event_sequence += 1
        task.events.append(TraceEvent(
            task_id=task.id, session_id=task.session_id,
            sequence=task.event_sequence, stage_id=stage_id, event_type=event_type,
            payload=sanitize(payload), created_at=utc_now(),
        ))

    def _owned(self, task: Task, generation: int) -> bool:
        return task.generation == generation and task.status in {
            TaskStatus.RUNNING, TaskStatus.CANCELLING,
        }

    def start(self, session_id: str, task_id: str, budget_seconds: float) -> Task | None:
        with self._lock:
            task = self._task(session_id, task_id)
            if task.status != TaskStatus.QUEUED:
                return None
            task.status = TaskStatus.RUNNING
            task.generation += 1
            task.started_at = task.started_at or utc_now()
            task.deadline_at = task.deadline_at or task.started_at + timedelta(seconds=budget_seconds)
            self._event(task, "task.running", "system", {
                "status": task.status, "started_at": task.started_at.isoformat(),
                "deadline_at": task.deadline_at.isoformat(), "lease_generation": task.generation,
            })
            return copy.deepcopy(task)

    def progress(self, session_id: str, task_id: str, generation: int,
                 stage: str, completed: bool, checkpoint: dict[str, Any] | None) -> None:
        with self._lock:
            task = self._task(session_id, task_id)
            if not self._owned(task, generation) or task.cancellation_requested:
                raise PlatformError("stale_execution", 409)
            task.current_stage = stage
            if completed:
                task.checkpoint = sanitize(checkpoint or {"stage": stage})
                task.checkpoint_sequence = task.event_sequence + 1
            else:
                task.stage_started_at = utc_now()
            self._event(task, "stage.completed" if completed else "stage.started", stage, {
                "stage": stage, "attempt": task.generation,
                **({"checkpoint_sequence": task.checkpoint_sequence,
                    "duration_ms": max(0, int((utc_now() - (task.stage_started_at or utc_now())).total_seconds() * 1000))}
                   if completed else {}),
            })

    def record(self, session_id: str, task_id: str, generation: int,
               stage: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._lock:
            task = self._task(session_id, task_id)
            if not self._owned(task, generation) or task.cancellation_requested:
                raise PlatformError("stale_execution", 409)
            self._event(task, event_type, stage, payload)

    def reject_checkpoint(self, session_id: str, task_id: str) -> None:
        with self._lock:
            task = self._task(session_id, task_id)
            if task.status == TaskStatus.INTERRUPTED and task.error_code != "checkpoint_incompatible":
                task.error_code = "checkpoint_incompatible"
                self._event(task, "checkpoint.incompatible", "system", {"error_code": task.error_code})

    def tool_record(self, session_id: str, task_id: str, generation: int,
                    call_id: str, entry: dict, event_type: str, payload: dict) -> None:
        with self._lock:
            task = self._task(session_id, task_id)
            if not self._owned(task, generation) or task.cancellation_requested:
                raise PlatformError("stale_execution", 409)
            if call_id not in task.tool_calls and len(task.tool_calls) >= 64:
                raise PlatformError("tool_capacity_exceeded", 409)
            if len(json.dumps(entry, allow_nan=False).encode()) > 70000:
                raise PlatformError("tool_record_too_large", 413)
            previous = task.tool_calls.get(call_id)
            if previous and previous["arguments_hash"] != entry["arguments_hash"]:
                raise PlatformError("tool_idempotency_conflict", 409)
            task.tool_calls[call_id] = sanitize(copy.deepcopy(entry))
            self._event(task, event_type, entry["stage_id"], payload)

    def finish(self, session_id: str, task_id: str, generation: int,
               status: TaskStatus, final_response: str | None = None,
               error_code: str | None = None) -> Task:
        with self._lock:
            task = self._task(session_id, task_id)
            if not self._owned(task, generation):
                return copy.deepcopy(task)
            if task.cancellation_requested:
                status = TaskStatus.CANCELLED
                final_response = None
                error_code = None
            task.status = status
            task.final_response = sanitize_text(final_response) if final_response else None
            task.error_code = error_code
            task.finished_at = utc_now() if status in TERMINAL_STATUSES else None
            for call in task.tool_calls.values():
                if not call.get("result"):
                    call["status"] = "interrupted"
                    for attempt in call["attempts"]:
                        if attempt["status"] == "started":
                            attempt.update(status="interrupted", retryable=True,
                                           error_code="transport_error", finished_at=utc_now().isoformat())
            for operation_id, operation in list(task.active_operations.items()):
                self._event(task, f"{operation['family']}.interrupted", operation["stage"], {
                    "operation_id": operation_id, "reason": "execution_ended",
                })
            payload: dict[str, Any] = {"status": status}
            if task.finished_at:
                payload["finished_at"] = task.finished_at.isoformat()
            if status == TaskStatus.INTERRUPTED:
                payload["checkpoint_sequence"] = task.checkpoint_sequence
            if task.final_response:
                payload["final_response"] = task.final_response
                self._sessions[session_id].messages.append(Message(
                    id=new_id(), role="assistant", content=task.final_response, task_id=task.id,
                ))
            if error_code:
                payload["error_code"] = error_code
            self._event(task, f"task.{status}", task.current_stage or "system", payload)
            return copy.deepcopy(task)

    def cancel(self, session_id: str, task_id: str) -> Task:
        with self._lock:
            task = self._task(session_id, task_id)
            if task.status in TERMINAL_STATUSES:
                if task.status != TaskStatus.CANCELLED:
                    raise PlatformError("task_already_terminal", 409)
                return copy.deepcopy(task)
            if task.cancellation_requested:
                return copy.deepcopy(task)
            task.cancellation_requested = True
            if task.status in {TaskStatus.QUEUED, TaskStatus.INTERRUPTED}:
                task.status = TaskStatus.CANCELLED
                task.finished_at = utc_now()
                self._event(task, "task.cancelled", "system", {
                    "status": task.status, "finished_at": task.finished_at.isoformat(),
                })
            else:
                task.status = TaskStatus.CANCELLING
                self._event(task, "task.cancelling", "system", {"status": task.status})
            return copy.deepcopy(task)

    def resume(self, session_id: str, task_id: str) -> tuple[Task, bool]:
        with self._lock:
            task = self._task(session_id, task_id)
            if task.status != TaskStatus.INTERRUPTED:
                if task.resume_requested and task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
                    return copy.deepcopy(task), False
                raise PlatformError("task_not_interrupted", 409)
            self._check_capacity()
            task.status = TaskStatus.QUEUED
            task.resume_requested = True
            task.error_code = None
            self._event(task, "task.resumed", "system", {
                "status": task.status, "lease_generation": task.generation + 1,
                "checkpoint_sequence": task.checkpoint_sequence,
            })
            return copy.deepcopy(task), True

    def events_after(self, session_id: str, task_id: str, sequence: int,
                     limit: int = 500) -> list[TraceEvent]:
        with self._lock:
            task = self._task(session_id, task_id)
            if sequence > len(task.events):
                raise PlatformError("cursor_ahead", 409)
            return copy.deepcopy(task.events[sequence:sequence + limit])
