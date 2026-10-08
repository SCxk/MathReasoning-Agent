from dataclasses import dataclass, field
from typing import Any

from reasoning_agent.custom.prompts.tool_use import build_initial_messages
from reasoning_agent.custom.state import Candidate, SolveState


@dataclass
class RunnerContext:
    problem: str
    metadata: dict[str, Any]
    messages: list[dict[str, Any]]

    model_calls: int = 0
    step_verify_calls: int = 0
    # 当前局部 solve_step 连续被逻辑校验拒绝的次数；accept/revise 后清零。
    current_logic_retries: int = 0
    tool_calls: int = 0
    loop_steps: int = 0

    observations: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    raw_responses: list[str] = field(default_factory=list)
    debug_trace: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    solve_state: SolveState = field(default_factory=SolveState)

    @classmethod
    def create(
        cls,
        problem: str,
        metadata: dict | None,
        max_solve_steps: int = 14,
    ) -> "RunnerContext":
        normalized_problem = str(problem or "").strip()
        normalized_metadata = metadata if isinstance(metadata, dict) else {}
        messages = build_initial_messages(normalized_problem, max_solve_steps)
        ctx = cls(
            problem=normalized_problem,
            metadata=dict(normalized_metadata),
            messages=messages,
        )
        for message in messages:
            if message.get("role") == "user":
                ctx.debug_trace.append(
                    {"type": "user", "content": str(message.get("content", ""))}
                )
        return ctx

    def add_observation(self, observation: dict[str, Any]) -> None:
        self.observations.append(observation)
