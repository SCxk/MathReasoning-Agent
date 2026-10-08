from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


TERMINAL_STATUSES = {TaskStatus.CANCELLED, TaskStatus.SUCCEEDED, TaskStatus.FAILED}


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionCreate(StrictRequest):
    memory_token_limit: int = Field(default=4000, ge=0, le=16000)


class TaskCreate(StrictRequest):
    problem: str = Field(min_length=1, max_length=24000)
    metadata: dict[str, Any] | None = None
    response_style: Literal["auto", "answer", "brief", "detailed"] | None = None

    @field_validator("problem")
    @classmethod
    def nonempty_problem(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("invalid_problem")
        return value


class CancelRequest(StrictRequest):
    reason: str | None = Field(default=None, max_length=500)


class QuestionBatchStart(StrictRequest):
    prompt: str = Field(default="", max_length=4000)
    response_style: Literal["auto", "answer", "brief", "detailed"] = "auto"

    @field_validator("prompt")
    @classmethod
    def trimmed_prompt(cls, value: str) -> str:
        return value.strip()


class TraceEvent(BaseModel):
    task_id: str
    session_id: str
    sequence: int
    stage_id: str
    event_type: str
    created_at: datetime
    payload: dict[str, Any]

    def sse_frame(self) -> str:
        return (
            f"id: {self.sequence}\nevent: {self.event_type}\n"
            f"data: {self.model_dump_json()}\n\n"
        )


@dataclass(frozen=True)
class Message:
    id: str
    role: str
    content: str
    task_id: str


@dataclass
class Session:
    id: str
    memory_token_limit: int
    created_at: datetime = field(default_factory=utc_now)
    messages: list[Message] = field(default_factory=list)


@dataclass
class Task:
    id: str
    session_id: str
    problem: str
    metadata: dict[str, Any]
    memory: tuple[Message, ...]
    runtime_mode: str
    status: TaskStatus = TaskStatus.QUEUED
    current_stage: str | None = None
    final_response: str | None = None
    error_code: str | None = None
    accepted_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    deadline_at: datetime | None = None
    finished_at: datetime | None = None
    cancellation_requested: bool = False
    resume_requested: bool = False
    checkpoint: dict[str, Any] | None = None
    checkpoint_sequence: int = 0
    stage_started_at: datetime | None = None
    generation: int = 0
    event_sequence: int = 0
    lease_until: datetime | None = None
    active_operations: dict[str, dict[str, str]] = field(default_factory=dict)
    model_calls: dict[str, int] = field(default_factory=dict)
    tool_calls: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[TraceEvent] = field(default_factory=list)


class PlatformError(Exception):
    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
