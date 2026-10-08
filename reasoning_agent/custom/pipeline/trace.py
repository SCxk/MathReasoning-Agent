from dataclasses import asdict, is_dataclass
from typing import Any

from reasoning_agent.custom.pipeline.types import PipelineCandidate, Plan, ProblemProfile


def dataclass_summary(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return {"value": str(value)}


def profile_summary(profile: ProblemProfile) -> dict[str, Any]:
    return dataclass_summary(profile)


def plan_summary(plan: Plan) -> dict[str, Any]:
    return {
        "strategy": plan.strategy,
        "step_count": len(plan.steps),
        "risk_count": len(plan.risk_points),
    }


def candidate_summary(candidate: PipelineCandidate, candidate_id: int = 0) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "source": candidate.source,
        "answer_chars": len(candidate.answer),
        "score": candidate.score,
        "verification": dict(candidate.verification),
    }


def candidates_summary(candidates: list[PipelineCandidate]) -> dict[str, Any]:
    return {
        "count": len(candidates),
        "candidates": [
            candidate_summary(candidate, candidate_id)
            for candidate_id, candidate in enumerate(candidates)
        ],
    }
