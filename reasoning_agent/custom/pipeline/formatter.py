from reasoning_agent.custom.parsers.final_answer_parser import normalize_final_response
from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.pipeline.types import PipelineCandidate, ProblemProfile


class FinalFormatter:
    """最终答案格式化节点。

    final_response 必须能独立判分：证明题保留必要证明，选择/填空题保持清晰简洁。
    """

    def run(
        self,
        ctx: PipelineContext,
        profile: ProblemProfile,
        candidate: PipelineCandidate | None,
    ) -> str:
        if candidate is None:
            return "无法确定唯一答案"
        return normalize_final_response(
            candidate.answer,
            problem=ctx.problem,
            problem_type=profile.task_type,
        )
