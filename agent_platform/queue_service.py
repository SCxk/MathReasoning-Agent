"""API-side durable discovery; Celery delivery contains IDs only, never problem text."""

import asyncio
from contextlib import suppress
import threading
import time
from typing import TypedDict

from agent_platform.service import TaskService
from agent_platform.postgres_store import PostgresTaskStore


class PhaseState(TypedDict):
    ok: bool | None
    failures: int
    last_success: float | None


class QueueTaskService(TaskService):
    def __init__(self, store: PostgresTaskStore, runtime, celery, transport, *, poll_seconds=1,
                 clock=time.monotonic):
        if not 0 < poll_seconds <= 5:
            raise ValueError("invalid_discovery_interval")
        super().__init__(store, runtime)
        self.store: PostgresTaskStore = store
        self.celery, self.transport, self.poll_seconds = celery, transport, poll_seconds
        self.discovery: asyncio.Task | None = None
        self.clock = clock
        self.last_cleanup: float | None = None
        self.last_cleanup_attempt: float | None = None
        self.last_cycle = self.clock()
        self.closing = threading.Event()
        self.health_lock = threading.Lock()
        self.phases: dict[str, PhaseState] = {name: {"ok": None, "failures": 0, "last_success": None}
                       for name in ("cleanup", "recovery", "dispatch", "events")}

    async def start(self):
        if self.accepting:
            return
        self.store.ready()
        self.closing.clear()
        self.last_cycle = self.clock()
        self.accepting = True
        self.discovery = asyncio.create_task(self._discover())

    async def stop(self):
        self.accepting = False
        self.closing.set()
        if self.discovery:
            self.discovery.cancel()
            await asyncio.gather(self.discovery, return_exceptions=True)
            self.discovery = None

    def _enqueue(self, task):
        pass  # Committed queued rows are the job outbox; no in-process execution.

    async def _discover(self):
        while True:
            cycle = asyncio.create_task(asyncio.to_thread(self.discover_once))
            try:
                await asyncio.shield(cycle)
            except asyncio.CancelledError:
                # Cancelling to_thread does not stop its database/broker operations.
                with suppress(Exception):
                    await cycle
                raise
            await asyncio.sleep(self.poll_seconds)

    def operational_health(self):
        with self.health_lock:
            phases = {name: dict(value) for name, value in self.phases.items()}
            age = max(0, self.clock() - self.last_cycle)
        reasons = [f"{name}_failed" for name, value in phases.items() if value["ok"] is False]
        if self.accepting and age > 30:
            reasons.append("dispatcher_stalled")
        if self.accepting and (self.discovery is None or self.discovery.done()):
            reasons.append("dispatcher_stopped")
        return {"status": "degraded" if reasons else "ok", "reasons": reasons,
                "cycle_age_seconds": age, "phases": phases}

    def _phase(self, name, operation):
        try:
            operation()
        except Exception:
            with self.health_lock:
                self.phases[name]["ok"] = False
                self.phases[name]["failures"] += 1
        else:
            with self.health_lock:
                self.phases[name]["ok"] = True
                self.phases[name]["last_success"] = self.clock()

    def _recover(self):
        from agent_platform.models import PlatformError

        self.store.recover_expired()
        compatible = getattr(self.runtime, "checkpoint_compatible", lambda value: True)
        failed = False
        for task in self.store.list_interrupted():
            if self.closing.is_set():
                break
            if (
                task.runtime_mode != self.runtime.name
                or task.error_code == "checkpoint_incompatible"
            ):
                continue
            try:
                if compatible(task.checkpoint):
                    self.store.resume(task.session_id, task.id)
                else:
                    self.store.reject_checkpoint(task.session_id, task.id)
            except PlatformError as exc:
                if exc.code not in {"task_not_interrupted", "task_not_found"}:
                    failed = True
            except Exception:
                failed = True
        if failed:
            raise RuntimeError("recovery_failed")

    def _dispatch(self):
        failed = False
        for task in self.store.dispatch_due(self.runtime.name):
            if self.closing.is_set():
                break
            try:
                self.celery.send_task(
                    "maths.execute", args=[task.session_id, task.id],
                    queue="recovery" if task.resume_requested else "reasoning", retry=False,
                )
            except Exception:
                failed = True
        if failed:
            raise RuntimeError("dispatch_failed")

    def discover_once(self):
        with self.health_lock:
            self.last_cycle = self.clock()
        now = self.clock()
        cleanup_due = self.last_cleanup is None or now - self.last_cleanup >= 3600
        retry_due = self.last_cleanup_attempt is None or now - self.last_cleanup_attempt >= 60
        if cleanup_due and retry_due:
            self.last_cleanup_attempt = now

            def cleanup():
                self.store.cleanup()
                self.last_cleanup = self.clock()

            self._phase("cleanup", cleanup)
        self._phase("recovery", self._recover)
        self._phase("dispatch", self._dispatch)
        self._phase("events", self.transport.flush)
