import re

from reasoning_agent.custom.pipeline.context import PipelineContext
from reasoning_agent.custom.pipeline.types import PipelineCandidate, Plan, ProblemProfile


class CandidateVerifier:
    """候选验证节点。

    第一版做低成本结构检查。模型验证后续可挂到这里，但不要和修复逻辑混在一起。
    """

    def run(
        self,
        ctx: PipelineContext,
        profile: ProblemProfile,
        plan: Plan,
        candidates: list[PipelineCandidate],
    ) -> list[PipelineCandidate]:
        for candidate in candidates:
            candidate.verification = self._verify_one(ctx, profile, candidate)
            candidate.score = self._score(candidate.verification)
        return candidates

    def _verify_one(
        self,
        ctx: PipelineContext,
        profile: ProblemProfile,
        candidate: PipelineCandidate,
    ) -> dict[str, object]:
        answer = candidate.answer.strip()
        issues: list[str] = []

        if not answer:
            issues.append("empty_answer")

        if profile.task_type == "choice" and not self._contains_choice(answer):
            issues.append("missing_choice_option")

        if (
            profile.task_type == "proof"
            and len(answer) < ctx.pipeline_config.min_answer_chars_for_proof
        ):
            issues.append("proof_too_short")

        return {
            "verdict": "PASS" if not issues else "NEEDS_REPAIR",
            "issues": issues,
        }

    @staticmethod
    def _contains_choice(answer: str) -> bool:
        normalized = answer.strip().upper()
        return bool(
            re.search(r"(^|[^A-Z])(?:选项)?[ABCDE](?:[\.。)、\s]|$)", normalized)
        )

    @staticmethod
    def _score(verification: dict[str, object]) -> float:
        if verification.get("verdict") == "PASS":
            return 1.0
        issues = verification.get("issues", [])
        issue_count = len(issues) if isinstance(issues, list) else 1
        return max(0.0, 0.6 - 0.2 * issue_count)
