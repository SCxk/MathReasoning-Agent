from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskPhase(str, Enum):
    RUN = "run"
    VERIFY = "verify"
    FINALIZE = "finalize"
    DONE = "done"


@dataclass
class Candidate:
    answer: str
    source: str
    reasoning_summary: str = ""


@dataclass
class SolveState:
    """单个候选生成过程中的可压缩状态。

    这个状态用于构造后续多轮提示词和 debug_trace，不进入正式业务 trace。
    """

    solve_steps: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    error_memory: list[dict[str, Any]] = field(default_factory=list)
    invalid_json_count: int = 0
    final_answer: str = ""
    reasoning_summary: str = ""

    def add_solve_step(self, step: dict[str, Any]) -> None:
        self.solve_steps.append(step)

    def add_tool_result(self, tool: str, observation: dict[str, Any]) -> None:
        self.tool_results.append({"tool": tool, "observation": observation})

    def add_invalid_json(self) -> None:
        self.invalid_json_count += 1

    def add_error_memory(
        self,
        reason: str,
        retry_instruction: str,
        rejected_step: dict[str, Any],
        max_items: int,
    ) -> None:
        memory = {
            "summary": _shorten(reason, 240),
            "retry_instruction": _shorten(retry_instruction, 240),
            "rejected_step_summary": _shorten(
                str(rejected_step.get("step_summary", "") or ""),
                180,
            ),
            "rejected_derived_results": [
                _shorten(str(item or ""), 160)
                for item in rejected_step.get("derived_results", [])
                if str(item or "").strip()
            ][:3],
            "avoid_repeating": (
                "不要重复 rejected_step_summary 或 rejected_derived_results 中的路线、"
                "候选结论或跳步推理；除非先补足 retry_instruction 要求的严格证明。"
            ),
        }
        self.error_memory.append(memory)
        if max_items > 0 and len(self.error_memory) > max_items:
            self.error_memory = self.error_memory[-max_items:]

    def set_final_answer(self, answer: str, reasoning_summary: str = "") -> None:
        self.final_answer = answer
        self.reasoning_summary = reasoning_summary

    def summary(self, max_solve_steps: int | None = None) -> dict[str, Any]:
        latest_step = self.solve_steps[-1] if self.solve_steps else {}
        latest_tool = self.tool_results[-1] if self.tool_results else {}
        solve_step_count = len(self.solve_steps)
        remaining_solve_steps = None
        if max_solve_steps is not None:
            remaining_solve_steps = max(max_solve_steps - solve_step_count, 0)
        return {
            "solve_step_count": solve_step_count,
            "max_solve_steps": max_solve_steps,
            "remaining_solve_steps": remaining_solve_steps,
            "latest_step": latest_step,
            "tool_result_count": len(self.tool_results),
            "latest_tool_result": latest_tool,
            "error_memory": self.error_memory,
            "invalid_json_count": self.invalid_json_count,
            "has_final_answer": bool(self.final_answer.strip()),
        }


@dataclass
class TaskResult:
    final_response: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    debug_trace: list[dict[str, Any]] = field(default_factory=list)


def _shorten(text: str, limit: int) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."

