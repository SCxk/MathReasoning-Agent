from typing import Any

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom.parsers.final_answer_parser import fallback_answer
from reasoning_agent.custom.pipeline.classifier import ProblemClassifier
from reasoning_agent.custom.pipeline.config import PipelineConfig
from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.pipeline.formatter import FinalFormatter
from reasoning_agent.custom.pipeline.generator import CandidateGenerator
from reasoning_agent.custom.pipeline.planner import Planner
from reasoning_agent.custom.pipeline.repair import RepairRunner
from reasoning_agent.custom.pipeline.selector import CandidateSelector
from reasoning_agent.custom.pipeline.strategy_preprocessor import StrategyPreprocessor
from reasoning_agent.custom.pipeline.trace import (
    candidate_summary,
    candidates_summary,
    plan_summary,
    profile_summary,
)
from reasoning_agent.custom.pipeline.types import PipelineResult
from reasoning_agent.custom.pipeline.types import Plan, ProblemProfile
from reasoning_agent.custom.pipeline.verifier import CandidateVerifier
from reasoning_agent.custom.runner.context import RunnerContext
from reasoning_agent.custom.runner.loop import ToolUseRunner
from reasoning_agent.custom.tools.executor import ToolExecutor


class PipelineOrchestrator:
    """业务层 pipeline 总编排。

    这里只负责阶段顺序、trace 摘要和异常兜底；具体推理、验证、修复策略都放在
    独立节点中，避免主流程变成不可维护的大函数。
    """

    def __init__(
        self,
        client: Any,
        tool_executor: ToolExecutor,
        agent_config: AgentConfig,
        pipeline_config: PipelineConfig | None = None,
        tool_use_runner: ToolUseRunner | None = None,
    ) -> None:
        self.agent_config = agent_config
        self.pipeline_config = pipeline_config or PipelineConfig()
        self.tool_use_runner = tool_use_runner or ToolUseRunner(
            client=client,
            tool_executor=tool_executor,
            config=agent_config,
        )
        self.classifier = ProblemClassifier()
        self.planner = Planner()
        self.strategy_preprocessor = StrategyPreprocessor(client=client, config=agent_config)
        self.generator = CandidateGenerator(self.tool_use_runner)
        self.verifier = CandidateVerifier()
        self.repair = RepairRunner()
        self.selector = CandidateSelector()
        self.formatter = FinalFormatter()

    def run(self, problem: str, metadata: dict | None) -> PipelineResult:
        ctx = PipelineContext.create(
            problem=problem,
            metadata=metadata,
            agent_config=self.agent_config,
            pipeline_config=self.pipeline_config,
        )

        try:
            if self.pipeline_config.enable_classify:
                profile = self.classifier.run(ctx)
                ctx.add_trace("classify", profile_summary(profile))
            else:
                profile = ProblemProfile()

            if self.pipeline_config.enable_plan:
                plan = self.planner.run(ctx, profile)
                ctx.add_trace("plan", plan_summary(plan))
            else:
                plan = Plan(strategy="direct_generate")

            strategy_guidance = self.strategy_preprocessor.run(ctx)
            if strategy_guidance:
                ctx.add_trace(
                    "strategy_preprocess",
                    {
                        "problem_type": str(strategy_guidance.get("problem_type", "unknown")),
                        "phase_count": len(strategy_guidance.get("phase_plan", []))
                        if isinstance(strategy_guidance.get("phase_plan"), list)
                        else 0,
                        "risk_count": len(strategy_guidance.get("risk_controls", []))
                        if isinstance(strategy_guidance.get("risk_controls"), list)
                        else 0,
                    },
                )

            candidates = self.generator.run(ctx, profile, plan)
            ctx.add_trace("generate_candidates", candidates_summary(candidates))

            if self.pipeline_config.enable_verify:
                candidates = self.verifier.run(ctx, profile, plan, candidates)
                ctx.add_trace("verify", candidates_summary(candidates))

            if self.pipeline_config.enable_repair:
                repaired = self.repair.run(ctx, profile, plan, candidates)
                if repaired:
                    candidates.extend(repaired)
                    ctx.add_trace("repair", candidates_summary(repaired))

            best = self.selector.run(ctx, candidates)
            ctx.add_trace(
                "select",
                candidate_summary(best) if best is not None else {"candidate_id": None},
            )

            final_response = self.formatter.run(ctx, profile, best)
        except Exception as exc:  # noqa: BLE001 - keep platform output contract stable.
            ctx.add_error(exc)
            fallback_ctx = RunnerContext.create(
                problem=ctx.problem,
                metadata=ctx.metadata,
                max_solve_steps=self.agent_config.max_solve_steps,
            )
            fallback_ctx.debug_trace = ctx.debug_trace
            final_response = fallback_answer(fallback_ctx)

        ctx.add_trace("finalize", {"answer_chars": len(final_response)})
        return PipelineResult(
            final_response=final_response,
            trace=ctx.trace,
            debug_trace=ctx.debug_trace,
        )
