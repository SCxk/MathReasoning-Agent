from typing import Any

from reasoning_agent.custom.state import Candidate


class AnswerVerifier:
    """Minimal verifier placeholder.

    The custom agent records that a candidate exists. Real verification logic can
    later be added without changing the TaskRunner interface.
    """

    def verify(self, ctx: Any, candidate: Candidate) -> dict[str, Any]:
        return {
            "verdict": "NOT_CHECKED",
            "candidate_source": candidate.source,
            "has_answer": bool(candidate.answer.strip()),
        }
