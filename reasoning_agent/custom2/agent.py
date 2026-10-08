from typing import Any
import json

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.parsers.final_answer_parser import normalize_final_response
from reasoning_agent.custom.parsers.json_parser import make_json_safe
from reasoning_agent.custom2.runner import ReasoningRuntime


class Custom2Agent:
    """State-driven reasoning runtime following long reasoning V2 first phase."""

    def __init__(
        self,
        client: Any,
        config: AgentConfig | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.client = client
        self.config = config or AgentConfig()
        self.solver_protocol = getattr(self.config, "custom2_solver_protocol", "json")
        if self.solver_protocol not in {"json", "text", "staged"}:
            raise ValueError("custom2_solver_protocol must be json, text or staged")

    def solve(self, problem: str, metadata: dict | None) -> dict:
        if self.solver_protocol == "staged":
            from reasoning_agent.custom2.staged_runtime import StagedReasoningRuntime

            runtime = StagedReasoningRuntime(client=self.client, config=self.config)
            try:
                return runtime.run(problem=problem, metadata=metadata)
            except Exception as exc:
                return runtime.recover_unhandled_exception(exc)
        if self.solver_protocol == "text":
            from reasoning_agent.custom2.solver_text_runtime import (
                SolverTextReasoningRuntime, format_solver_text_response,
            )

            runtime = SolverTextReasoningRuntime(client=self.client, config=self.config)
        else:
            runtime = ReasoningRuntime(client=self.client, config=self.config)
        result = runtime.run(problem=problem, metadata=metadata)
        output = {
            "final_response": format_solver_text_response(result.final_response, problem)
            if self.solver_protocol == "text" else normalize_final_response(
                result.final_response,
                problem=problem,
                problem_type=result.state.problem_type,
            ),
            "trace": make_json_safe(result.trace),
        }
        if self.config.emit_debug_trace:
            debug_trace = result.debug_trace
            if self.solver_protocol == "text":
                safe_fields = {
                    "type", "call_type", "task_id", "claim_count", "candidate_count",
                    "duration_seconds", "finish_reason", "content_length", "error_type", "attempt",
                }
                debug_trace = [
                    {key: value for key, value in item.items() if key in safe_fields}
                    for item in debug_trace
                ]
            output["debug_trace"] = _bounded_debug_trace(
                debug_trace, self.config.max_trace_chars
            )
        return output


def _bounded_debug_trace(items: list[dict], max_chars: int) -> list[dict]:
    remaining = max(0, int(max_chars))
    prioritized = [
        (index, item)
        for index, item in reversed(list(enumerate(items)))
        if item.get("type") == "model_response"
    ]
    prioritized.extend(
        (index, item)
        for index, item in reversed(list(enumerate(items)))
        if item.get("type") != "model_response"
    )
    selected: list[tuple[int, dict]] = []
    selected_indexes: set[int] = set()
    for index, raw_item in prioritized:
        if index in selected_indexes:
            continue
        if remaining <= 0:
            break
        item = _compact_debug_item(raw_item)
        encoded = json.dumps(item, ensure_ascii=False)
        if len(encoded) > remaining:
            item = {
                "type": str(item.get("type", "debug")),
                "content": str(
                    item.get("content_tail", item.get("content", ""))
                )[-max(0, remaining - 80) :],
            }
            encoded = json.dumps(item, ensure_ascii=False)
        if len(encoded) > remaining:
            continue
        selected.append((index, item))
        selected_indexes.add(index)
        remaining -= len(encoded)
    return [item for _, item in sorted(selected, key=lambda pair: pair[0])]


def _compact_debug_item(raw_item: dict) -> dict:
    item = dict(make_json_safe(raw_item))
    content = item.pop("content", None)
    if isinstance(content, str):
        item.setdefault("content_head", content[:600])
        item.setdefault(
            "content_tail", content[-600:] if len(content) > 600 else content
        )
        item.setdefault("content_length", len(content))
    return item
