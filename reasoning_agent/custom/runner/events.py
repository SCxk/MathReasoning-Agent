from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ToolCallEvent:
    type: Literal["tool_call"] = "tool_call"
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = ""
    assistant_message: dict[str, Any] | None = None


@dataclass(frozen=True)
class FinalAnswerEvent:
    type: Literal["final_answer"] = "final_answer"
    answer: str = ""
    reasoning_summary: str = ""


@dataclass(frozen=True)
class SolveStepEvent:
    type: Literal["solve_step"] = "solve_step"
    step_summary: str = ""
    known_facts: list[str] = field(default_factory=list)
    derived_results: list[str] = field(default_factory=list)
    remaining_tasks: list[str] = field(default_factory=list)
    is_ready_for_final: bool = False


@dataclass(frozen=True)
class InvalidEvent:
    type: Literal["invalid"] = "invalid"
    raw: str = ""
    message: str = ""


ModelEvent = ToolCallEvent | FinalAnswerEvent | SolveStepEvent | InvalidEvent
