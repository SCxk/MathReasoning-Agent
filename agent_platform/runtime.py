import asyncio
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol

from agent_platform.models import Message
from agent_platform.safety import sanitize_text


STAGES = ("profile", "retrieve", "plan", "solve", "tool", "verify", "repair", "finalize")


@dataclass(frozen=True)
class RuntimeResult:
    final_response: str


class CheckpointIncompatible(Exception):
    pass


class RuntimeContext:
    def __init__(self, task_id: str, session_id: str, problem: str,
                 metadata: dict[str, Any], memory: tuple[Message, ...],
                 checkpoint: dict[str, Any] | None,
                 progress: Callable[[str, bool, dict[str, Any] | None], None],
                 *, deadline_at: datetime | None = None,
                 finalize_reserve_seconds: float = 25,
                 model_calls: dict[str, int] | None = None,
                 record: Callable[[str, str, dict[str, Any]], None] | None = None,
                 tool_calls: dict[str, dict[str, Any]] | None = None,
                 commit_tool: Callable[[str, dict, str, dict], None] | None = None) -> None:
        self.task_id = task_id
        self.session_id = session_id
        self.problem = problem
        self.metadata = metadata
        self.memory = memory
        self.checkpoint = checkpoint
        self._progress = progress
        self.deadline_at = deadline_at
        self.finalize_reserve_seconds = finalize_reserve_seconds
        self._record = record
        self.cancelled = threading.Event()
        self.model_calls = dict(model_calls or {})
        self.solver_calls_used = sum(count for name, count in self.model_calls.items() if name.startswith("solver"))
        self.max_solve_calls: int | None = None
        self.saved_response: str | None = None
        self.tool_calls = dict(tool_calls or {})
        self.tool_locks: dict[str, threading.Lock] = {}
        self._commit_tool = commit_tool

    def commit_tool(self, call_id: str, entry: dict, event_type: str, payload: dict) -> None:
        if self.cancelled.is_set():
            raise RuntimeError("execution_stopped")
        if self._commit_tool:
            self._commit_tool(call_id, entry, event_type, payload)
        else:
            self.record(entry["stage_id"], event_type, payload)
        self.tool_calls[call_id] = entry

    def progress(self, stage: str, *, completed: bool = False,
                 checkpoint: dict[str, Any] | None = None) -> None:
        if stage not in STAGES:
            raise ValueError("invalid_stage")
        self._progress(stage, completed, checkpoint)

    def record(self, stage: str, event_type: str, payload: dict[str, Any]) -> None:
        if self.cancelled.is_set():
            raise RuntimeError("execution_stopped")
        if self._record:
            self._record(stage, event_type, payload)

    def save_response(self, response: str) -> None:
        if response.strip():
            self.saved_response = sanitize_text(response)


class AgentRuntime(Protocol):
    name: str

    async def run(self, context: RuntimeContext) -> RuntimeResult: ...


class ModelPermits(Protocol):
    def acquire(self, timeout: float = ...) -> bool: ...
    def release(self) -> None: ...


class FakeRuntime:
    name = "fake"

    def __init__(self, stage_delay: float = 0.25) -> None:
        self.stage_delay = stage_delay

    async def run(self, context: RuntimeContext) -> RuntimeResult:
        completed = (context.checkpoint or {}).get("completed_stage", -1)
        for index, stage in enumerate(STAGES):
            if index <= completed:
                continue
            context.progress(stage)
            await asyncio.sleep(self.stage_delay)
            context.progress(stage, completed=True, checkpoint={"completed_stage": index})
        return RuntimeResult(
            "Fake Runtime completed. No mathematical answer was generated."
        )
