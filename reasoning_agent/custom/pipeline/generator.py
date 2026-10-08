from typing import Any

from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.pipeline.types import PipelineCandidate, Plan, ProblemProfile
from reasoning_agent.custom.prompts.strategy_preprocess import build_strategy_guidance_message
from reasoning_agent.custom.runner.context import RunnerContext
from reasoning_agent.custom.runner.loop import ToolUseRunner
from reasoning_agent.custom.state import Candidate as RunnerCandidate


class CandidateGenerator:
    """候选生成节点。

    第一版复用现有 ToolUseRunner，保持当前 ReAct/JSON loop 行为不变。后续需要
    多候选时，可以在这里按不同策略多次构造 RunnerContext。
    """

    def __init__(self, tool_use_runner: ToolUseRunner) -> None:
        self.tool_use_runner = tool_use_runner

    def run(
        self,
        ctx: PipelineContext,
        profile: ProblemProfile,
        plan: Plan,
    ) -> list[PipelineCandidate]:
        candidates: list[PipelineCandidate] = []
        for _ in range(ctx.pipeline_config.max_candidates):
            runner_ctx = RunnerContext.create(
                problem=ctx.problem,
                metadata=ctx.metadata,
                max_solve_steps=ctx.agent_config.max_solve_steps,
            )
            if ctx.strategy_guidance:
                strategy_message = build_strategy_guidance_message(ctx.strategy_guidance)
                runner_ctx.messages.append(strategy_message)
                runner_ctx.debug_trace.append(
                    {
                        "type": "user",
                        "content": str(strategy_message.get("content", "")),
                    }
                )
            try:
                runner_candidate = self.tool_use_runner.run(runner_ctx)
            finally:
                ctx.debug_trace.extend(runner_ctx.debug_trace)
            candidates.append(self._from_runner_candidate(runner_candidate))
        return candidates

    @staticmethod
    def _from_runner_candidate(candidate: RunnerCandidate | Any) -> PipelineCandidate:
        return PipelineCandidate(
            answer=str(getattr(candidate, "answer", "") or "").strip(),
            reasoning_summary=str(getattr(candidate, "reasoning_summary", "") or ""),
            source=str(getattr(candidate, "source", "tool_loop") or "tool_loop"),
        )
