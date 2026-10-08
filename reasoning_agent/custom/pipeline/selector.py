from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.pipeline.types import PipelineCandidate


class CandidateSelector:
    """多候选选择节点。"""

    def run(
        self,
        ctx: PipelineContext,
        candidates: list[PipelineCandidate],
    ) -> PipelineCandidate | None:
        non_empty = [candidate for candidate in candidates if candidate.answer.strip()]
        if not non_empty:
            return None
        return max(non_empty, key=lambda candidate: candidate.score)
