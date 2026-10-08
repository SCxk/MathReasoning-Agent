import asyncio
import itertools
from datetime import datetime, timezone
from typing import Callable

from agent_platform.models import PlatformError, Task, TaskStatus
from agent_platform.runtime import AgentRuntime, CheckpointIncompatible, RuntimeContext
from agent_platform.storage import TaskStore


class TaskService:
    def __init__(self, store: TaskStore, runtime: AgentRuntime,
                 max_concurrency: int = 8, budget_seconds: float = 1200,
                 finalize_reserve_seconds: float = 25, *, recovery_poll_seconds: float = 5) -> None:
        if max_concurrency < 1 or budget_seconds <= finalize_reserve_seconds or finalize_reserve_seconds < 0:
            raise ValueError("invalid_service_configuration")
        self.store = store
        self.runtime = runtime
        self.max_concurrency = max_concurrency
        self.budget_seconds = budget_seconds
        self.finalize_reserve_seconds = finalize_reserve_seconds
        if not 0 < recovery_poll_seconds <= 5:
            raise ValueError("invalid_recovery_configuration")
        self.recovery_poll_seconds = recovery_poll_seconds
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._delivery_sequence = itertools.count()
        self._pending: set[str] = set()
        self._workers: list[asyncio.Task] = []
        self._executions: dict[str, asyncio.Task] = {}
        self._reconciler: asyncio.Task | None = None
        self.accepting = False

    async def start(self) -> None:
        if self.accepting:
            return
        if hasattr(self.store, "ready"):
            self.store.ready()
        queued = self.store.list_queued()
        self.accepting = True
        self._workers = [asyncio.create_task(self._worker()) for _ in range(self.max_concurrency)]
        for task in queued:
            if task.runtime_mode == self.runtime.name:
                self._enqueue(task)
        if hasattr(self.store, "recover_expired"):
            self._reconciler = asyncio.create_task(self._reconcile())

    async def stop(self) -> None:
        self.accepting = False
        if self._reconciler:
            self._reconciler.cancel()
            await asyncio.gather(self._reconciler, return_exceptions=True)
            self._reconciler = None
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        # Store is authoritative; discard old in-process deliveries on restart.
        self._queue = asyncio.PriorityQueue()
        self._pending.clear()

    def _enqueue(self, task: Task) -> None:
        if task.id not in self._pending and task.id not in self._executions:
            self._pending.add(task.id)
            self._queue.put_nowait((0 if task.resume_requested else 1,
                                    next(self._delivery_sequence), task.session_id, task.id))

    def submit(self, session_id: str, problem: str, metadata: dict,
               idempotency_key: str | None, before_create: Callable[[], None] | None = None) -> Task:
        if not self.accepting:
            raise PlatformError("not_ready", 503)
        task, created = self.store.create_task(
            session_id, problem, metadata, self.runtime.name, idempotency_key, before_create,
        )
        if created:
            self._enqueue(task)
        return task

    def cancel(self, session_id: str, task_id: str) -> Task:
        task = self.store.cancel(session_id, task_id)
        execution = self._executions.get(task_id)
        if execution:
            execution.cancel()
        return task

    def resume(self, session_id: str, task_id: str) -> Task:
        if not self.accepting:
            raise PlatformError("not_ready", 503)
        if self.store.get_task(session_id, task_id).runtime_mode != self.runtime.name:
            raise PlatformError("runtime_mismatch", 409)
        task, queued = self.store.resume(session_id, task_id)
        if queued:
            self._enqueue(task)
        return task

    async def _worker(self) -> None:
        while True:
            _, _, session_id, task_id = await self._queue.get()
            self._pending.discard(task_id)
            try:
                task = self.store.start(session_id, task_id, self.budget_seconds)
                if task:
                    await self._execute(task)
            except Exception:
                # Persistent queued records are re-delivered by reconciliation.
                await asyncio.sleep(.1)
            finally:
                self._queue.task_done()

    async def _reconcile(self) -> None:
        while True:
            try:
                self.store.recover_expired()
                for task in self.store.list_interrupted():
                    compatible = getattr(self.runtime, "checkpoint_compatible", lambda value: True)
                    if (task.runtime_mode == self.runtime.name
                            and task.error_code != "checkpoint_incompatible"
                            and compatible(task.checkpoint)):
                        recovered, _ = self.store.resume(task.session_id, task.id)
                        self._enqueue(recovered)
                    elif task.runtime_mode == self.runtime.name and not compatible(task.checkpoint):
                        self.store.reject_checkpoint(task.session_id, task.id)
                for task in self.store.list_queued():
                    if task.runtime_mode == self.runtime.name:
                        self._enqueue(task)
            except Exception:
                pass  # Fail closed during storage outages; retry discovery.
            await asyncio.sleep(self.recovery_poll_seconds)

    async def _renew(self, task: Task, context: RuntimeContext, execution: asyncio.Task):
        while True:
            await asyncio.sleep(min(3, self.store.lease_seconds / 3))
            try:
                self.store.renew(task.session_id, task.id, task.generation)
            except Exception:
                context.cancelled.set()
                execution.cancel()
                return

    async def _execute(self, task: Task) -> None:
        context = RuntimeContext(
            task.id, task.session_id, task.problem, task.metadata, task.memory,
            task.checkpoint,
            lambda stage, completed, checkpoint: self.store.progress(
                task.session_id, task.id, task.generation, stage, completed, checkpoint,
            ),
            deadline_at=task.deadline_at,
            finalize_reserve_seconds=self.finalize_reserve_seconds,
            model_calls=task.model_calls,
            tool_calls=task.tool_calls,
            commit_tool=lambda call_id, entry, event_type, payload: self.store.tool_record(
                task.session_id, task.id, task.generation, call_id, entry, event_type, payload,
            ),
            record=lambda stage, event_type, payload: self.store.record(
                task.session_id, task.id, task.generation, stage, event_type, payload,
            ),
        )
        execution = asyncio.create_task(self.runtime.run(context))
        self._executions[task.id] = execution
        renewal = (asyncio.create_task(self._renew(task, context, execution))
                   if hasattr(self.store, "renew") else None)
        remaining = (task.deadline_at - datetime.now(timezone.utc)).total_seconds()
        try:
            result = await asyncio.wait_for(execution, max(0, remaining - self.finalize_reserve_seconds))
            if not isinstance(result.final_response, str) or not result.final_response.strip():
                raise ValueError("empty_final_response")
            self.store.finish(task.session_id, task.id, task.generation,
                              TaskStatus.SUCCEEDED, result.final_response)
        except asyncio.CancelledError:
            self.store.finish(task.session_id, task.id, task.generation,
                              TaskStatus.INTERRUPTED, error_code="service_interrupted")
            if not self.accepting:
                raise
        except TimeoutError:
            if context.saved_response:
                self.store.finish(task.session_id, task.id, task.generation,
                                  TaskStatus.SUCCEEDED, context.saved_response)
            else:
                self.store.finish(task.session_id, task.id, task.generation,
                                  TaskStatus.FAILED, error_code="task_deadline_exceeded")
        except CheckpointIncompatible:
            self.store.finish(task.session_id, task.id, task.generation,
                              TaskStatus.INTERRUPTED, error_code="checkpoint_incompatible")
        except Exception:
            self.store.finish(task.session_id, task.id, task.generation,
                              TaskStatus.FAILED, error_code="runtime_failed")
        finally:
            context.cancelled.set()
            if renewal:
                renewal.cancel()
                await asyncio.gather(renewal, return_exceptions=True)
            self._executions.pop(task.id, None)
