from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.pipeline.types import PipelineCandidate, Plan, ProblemProfile


class RepairRunner:
    """候选修复节点。

    第一版不额外调用模型，只为后续修复流程保留稳定入口。验证失败但答案非空时，
    返回一个低分兜底候选，避免 pipeline 因修复缺失而中断。
    """

    def run(
        self,
        ctx: PipelineContext,
        profile: ProblemProfile,
        plan: Plan,
        candidates: list[PipelineCandidate],
    ) -> list[PipelineCandidate]:
        if not ctx.pipeline_config.enable_repair:
            return []
        if ctx.repair_attempts >= ctx.pipeline_config.max_repair_attempts:
            return []

        needs_repair = [
            candidate
            for candidate in candidates
            if candidate.verification.get("verdict") == "NEEDS_REPAIR"
            and candidate.answer.strip()
        ]
        if not needs_repair:
            return []

        ctx.repair_attempts += 1
        repaired: list[PipelineCandidate] = []
        for candidate in needs_repair:
            repaired.append(
                PipelineCandidate(
                    answer=candidate.answer,
                    reasoning_summary=candidate.reasoning_summary,
                    source=f"{candidate.source}:repair_placeholder",
                    score=max(candidate.score, 0.3),
                    verification={
                        "verdict": "NOT_REPAIRED",
                        "issues": candidate.verification.get("issues", []),
                    },
                )
            )
        return repaired
