from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProblemProfile:
    task_type: str = "unknown"
    difficulty: str = "unknown"
    needs_tools: bool = False
    answer_style: str = "explanation"


@dataclass
class Plan:
    strategy: str
    steps: list[str] = field(default_factory=list)
    risk_points: list[str] = field(default_factory=list)


@dataclass
class PipelineCandidate:
    answer: str
    reasoning_summary: str = ""
    source: str = "unknown"
    score: float = 0.0
    verification: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    final_response: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    debug_trace: list[dict[str, Any]] = field(default_factory=list)
