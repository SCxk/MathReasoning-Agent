from dataclasses import dataclass, field
from typing import Any, Literal

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.errors import EmptyModelResponse
from reasoning_agent.custom.parsers.json_parser import extract_json_object
from reasoning_agent.custom.prompts.step_verifier import build_step_verifier_messages
from reasoning_agent.custom.runner.context import RunnerContext
from reasoning_agent.max_token_retry import (
    build_retry_max_token_schedule,
    call_with_max_token_retry,
)


VerifierVerdict = Literal["accept", "revise", "reject"]


@dataclass(frozen=True)
class StepVerifyResult:
    verdict: VerifierVerdict
    reason: str = ""
    retry_instruction: str = ""
    revised_step: dict[str, Any] = field(default_factory=dict)


class StepLogicVerifier:
    """独立的 solve_step 数学逻辑校验器。

    这个组件只消耗 ctx.step_verify_calls，不占用主解题 ctx.model_calls。
    """

    def __init__(self, client: Any, config: AgentConfig) -> None:
        self.client = client
        self.config = config

    def verify(self, ctx: RunnerContext, candidate_step: dict[str, Any]) -> StepVerifyResult:
        if not self.config.enable_step_logic_verifier:
            return StepVerifyResult(verdict="accept", reason="step verifier disabled")

        if ctx.step_verify_calls >= self.config.max_step_verify_calls:
            return StepVerifyResult(
                verdict="accept",
                reason="step verifier budget exhausted; allow main loop to continue",
            )

        state_summary = ctx.solve_state.summary(self.config.max_solve_steps)
        messages = build_step_verifier_messages(
            problem=ctx.problem,
            state_summary=state_summary,
            candidate_step=candidate_step,
        )
        user_content = messages[-1]["content"]
        ctx.debug_trace.append(
            {
                "type": "step_verify_call",
                "content": user_content[: self.config.max_trace_chars],
            }
        )

        ctx.step_verify_calls += 1
        response = call_with_max_token_retry(
            self.client.chat,
            messages=messages,
            temperature=self.config.step_verifier_temperature,
            thinking_mode=self.config.thinking_mode,
            tools=None,
            max_token_schedule=build_retry_max_token_schedule(
                getattr(self.client, "retry", 3),
                initial_max_tokens=self.config.step_verifier_max_tokens,
                floor_max_tokens=min(self.config.step_verifier_max_tokens, 4096),
            ),
            result_validator=self._ensure_non_empty_response,
        )

        content = self._response_content(response)
        result = self._parse_result(content)
        ctx.debug_trace.append(
            {
                "type": "step_verify_result",
                "content": {
                    "verdict": result.verdict,
                    "reason": result.reason,
                    "retry_instruction": result.retry_instruction,
                    "revised_step": result.revised_step,
                    "raw": content[: self.config.max_trace_chars],
                },
            }
        )
        return result

    @staticmethod
    def _ensure_non_empty_response(response: str | dict[str, Any]) -> None:
        if isinstance(response, str) and response.strip():
            return
        if isinstance(response, dict):
            content = response.get("content")
            if isinstance(content, str) and content.strip():
                return
        raise EmptyModelResponse("step verifier returned empty content")

    @staticmethod
    def _response_content(response: str | dict[str, Any]) -> str:
        if isinstance(response, str):
            return response.strip()
        content = response.get("content")
        return content.strip() if isinstance(content, str) else ""

    def _parse_result(self, content: str) -> StepVerifyResult:
        data = extract_json_object(content)
        if not isinstance(data, dict):
            return StepVerifyResult(
                verdict="accept",
                reason="step verifier returned invalid JSON; allow main loop to continue",
            )

        verdict = str(data.get("verdict", "")).strip().lower()
        reason = str(data.get("reason", "") or "").strip()
        if verdict == "accept":
            return StepVerifyResult(verdict="accept", reason=reason)
        if verdict == "reject":
            retry_instruction = str(data.get("retry_instruction", "") or "").strip()
            return StepVerifyResult(
                verdict="reject",
                reason=reason or "step verifier rejected this step",
                retry_instruction=retry_instruction or "请重新给出更小、更可验证的一步推理。",
            )
        if verdict == "revise":
            revised_step = self._normalize_revised_step(data.get("revised_step"))
            if revised_step:
                return StepVerifyResult(
                    verdict="revise",
                    reason=reason,
                    revised_step=revised_step,
                )
            return StepVerifyResult(
                verdict="reject",
                reason=reason or "step verifier requested revise but revised_step is invalid",
                retry_instruction="请重新输出一个字段完整、逻辑可验证的 solve_step。",
            )

        return StepVerifyResult(
            verdict="accept",
            reason=f"unknown verifier verdict: {verdict}; allow main loop to continue",
        )

    @staticmethod
    def _normalize_revised_step(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {
            "step_summary": str(value.get("step_summary", "") or "").strip(),
            "known_facts": _as_text_list(value.get("known_facts", [])),
            "derived_results": _as_text_list(value.get("derived_results", [])),
            "remaining_tasks": _as_text_list(value.get("remaining_tasks", [])),
            "is_ready_for_final": bool(value.get("is_ready_for_final", False)),
        }


def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item or "").strip())]
