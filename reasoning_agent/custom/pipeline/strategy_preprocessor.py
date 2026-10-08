import re
from typing import Any

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.errors import EmptyModelResponse
from reasoning_agent.custom.parsers.json_parser import extract_json_object
from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.prompts.strategy_preprocess import (
    build_strategy_preprocess_messages,
)
from reasoning_agent.max_token_retry import (
    build_retry_max_token_schedule,
    call_with_max_token_retry,
)


class StrategyPreprocessor:
    """正式解题前的策略预处理节点。

    该节点只生成本题解题策略、阶段约束和风险规避，不直接作答；
    调用次数单独统计，不占用 generator 的 max_model_calls。
    """

    def __init__(self, client: Any, config: AgentConfig) -> None:
        self.client = client
        self.config = config

    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        if not self.config.enable_strategy_preprocess:
            return {}
        if ctx.strategy_preprocess_calls >= self.config.max_strategy_preprocess_calls:
            return {}
        if not callable(getattr(self.client, "chat", None)):
            return {}

        messages = build_strategy_preprocess_messages(
            problem=ctx.problem,
            metadata=ctx.metadata,
        )
        ctx.debug_trace.append(
            {
                "type": "strategy_preprocess_call",
                "content": messages[-1]["content"][: self.config.max_trace_chars],
            }
        )
        ctx.strategy_preprocess_calls += 1

        response = call_with_max_token_retry(
            self.client.chat,
            messages=messages,
            temperature=self.config.strategy_preprocess_temperature,
            thinking_mode=self.config.thinking_mode,
            tools=None,
            max_token_schedule=build_retry_max_token_schedule(
                getattr(self.client, "retry", 3),
                initial_max_tokens=self.config.strategy_preprocess_max_tokens,
                floor_max_tokens=min(self.config.strategy_preprocess_max_tokens, 4096),
            ),
            result_validator=self._ensure_non_empty_response,
        )
        content = self._response_content(response)
        guidance = self._parse_guidance(content)
        ctx.strategy_guidance = guidance
        ctx.debug_trace.append(
            {
                "type": "strategy_preprocess_result",
                "content": {
                    "guidance": guidance,
                    "raw": content[: self.config.max_trace_chars],
                },
            }
        )
        return guidance

    @staticmethod
    def _ensure_non_empty_response(response: str | dict[str, Any]) -> None:
        if isinstance(response, str) and response.strip():
            return
        if isinstance(response, dict):
            content = response.get("content")
            if isinstance(content, str) and content.strip():
                return
        raise EmptyModelResponse("strategy preprocessor returned empty content")

    @staticmethod
    def _response_content(response: str | dict[str, Any]) -> str:
        if isinstance(response, str):
            return response.strip()
        content = response.get("content")
        return content.strip() if isinstance(content, str) else ""

    @staticmethod
    def _parse_guidance(content: str) -> dict[str, Any]:
        data = extract_json_object(content)
        if not isinstance(data, dict):
            return {
                "problem_type": "unknown",
                "core_transforms": [],
                "phase_plan": [],
                "lower_bound_requirements": [],
                "upper_bound_requirements": [],
                "risk_controls": ["策略预处理输出无法解析，正式解题时必须保守推进。"],
                "do_not": ["不要猜最终答案。"],
                "first_step_instruction": "先进行规范化、排序、变量替换或等价变形。",
            }
        return StrategyPreprocessor._sanitize_guidance(data)

    @staticmethod
    def _sanitize_guidance(guidance: dict[str, Any]) -> dict[str, Any]:
        """Remove strategy items that leak candidate answers or unproved results.

        Strategy guidance is intentionally untrusted: it may propose a direction,
        but it must not smuggle a concrete final constant, candidate answer, or
        known-result assertion into later solve steps.
        """

        sanitized = dict(guidance)
        removed_items: list[str] = []
        list_fields = (
            "core_transforms",
            "phase_plan",
            "lower_bound_requirements",
            "upper_bound_requirements",
            "risk_controls",
            "do_not",
        )

        for field in list_fields:
            value = sanitized.get(field)
            if not isinstance(value, list):
                continue
            kept = []
            for item in value:
                text = str(item)
                if StrategyPreprocessor._contains_unproved_candidate(text):
                    removed_items.append(text)
                    continue
                kept.append(item)
            sanitized[field] = kept

        first_step = sanitized.get("first_step_instruction")
        if isinstance(first_step, str) and StrategyPreprocessor._contains_unproved_candidate(
            first_step
        ):
            removed_items.append(first_step)
            sanitized["first_step_instruction"] = (
                "先进行规范化、排序、变量替换或等价变形；每个等价变形必须逐项检查分母和变量位置。"
            )

        if removed_items:
            risk_controls = sanitized.get("risk_controls")
            if not isinstance(risk_controls, list):
                risk_controls = []
            risk_controls.append(
                "策略预处理曾包含具体最终常数、候选答案或 known result，相关内容已清除；正式解题不得采用这些候选，除非在 solve_step 中完成推导证明。"
            )
            risk_controls.append(
                "等价变形必须逐项代入检查分母和变量位置；如果同一步出现两个不同等价式且不一致，必须回退并重新推导。"
            )
            sanitized["risk_controls"] = risk_controls

            do_not = sanitized.get("do_not")
            if not isinstance(do_not, list):
                do_not = []
            do_not.append("不要把策略预处理中的候选常数或 known result 当作已证明结论。")
            do_not.append("不要使用针对题目关键词、metadata idx、常见答案或历史失败模式的硬编码兜底。")
            sanitized["do_not"] = do_not
            sanitized["sanitization_warnings"] = [
                "removed_unproved_candidate_or_known_result",
            ]

        return sanitized

    _UNPROVED_CANDIDATE_PATTERNS = tuple(
        re.compile(pattern, re.IGNORECASE)
        for pattern in (
            r"\\boxed",
            r"(?:候选答案|候选常数|最终答案|最终常数)",
            r"(?:answer|constant)\s*(?:is|=|:)",
            r"(?:minimum|minimal|maximum|maximal|optimum|optimal).{0,24}(?:is|=|:)",
            r"\b(?:T|C|K|k)\s*(?:=|≈|~=|<=|>=|<|>|≤|≥|\\le|\\ge)",
            r"(?:known result|well-known|standard result|folklore|known theorem)",
            r"(?:众所周知|已知结论|经典结论|标准结论|著名结论)",
            r"(?:golden ratio|黄金分割|phi|φ)",
            r"(?:sqrt|√)\s*[\({]?\s*\d",
        )
    )

    @staticmethod
    def _contains_unproved_candidate(text: str) -> bool:
        return any(
            pattern.search(text)
            for pattern in StrategyPreprocessor._UNPROVED_CANDIDATE_PATTERNS
        )
