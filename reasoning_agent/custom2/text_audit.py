import re

from reasoning_agent.custom2.text_models import DraftAudit, NarrativeAudit, ProblemProfile, SolutionDraft, TextCandidate


def parse_narrative_audit(text: str, draft: SolutionDraft, *, truncated: bool = False) -> NarrativeAudit:
    feedback = text.strip()
    pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?:\*\*)?(?:审核结论|结论|verdict)\s*[:：]\s*"
        r"(?:\*\*)?(通过|修复|重解|不确定|accept|repair|reject_route|uncertain)"
        r"(?:\*\*)?[。.!！]?\s*$", re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(feedback))
    verdict = "uncertain"
    status = "missing_verdict"
    if truncated:
        status = "truncated"
    elif not feedback:
        status = "empty"
    elif matches:
        mapping = {
            "通过": "accept", "修复": "repair", "重解": "reject_route", "不确定": "uncertain",
            "accept": "accept", "repair": "repair", "reject_route": "reject_route", "uncertain": "uncertain",
        }
        values = {mapping[match.group(1).lower()] for match in matches}
        if len(values) != 1:
            status = "conflicting_verdicts"
        elif feedback[matches[-1].end():].strip():
            status = "nonterminal_verdict"
        elif not pattern.sub("", feedback).strip():
            status = "missing_analysis"
        else:
            verdict = values.pop()
            status = "explicit_verdict"
    return NarrativeAudit(draft.id, verdict, feedback, status)


def validate_audit(
    review: DraftAudit, draft: SolutionDraft, profile: ProblemProfile,
    candidate: TextCandidate | None,
) -> DraftAudit:
    if review.solution_id != draft.id or draft.truncated:
        raise ValueError("wrong_or_truncated_solution")
    if candidate is not None and (
        candidate.solution_id != draft.id
        or not 0 <= candidate.start < candidate.end <= len(draft.text)
        or draft.text[candidate.start:candidate.end] != candidate.value
    ):
        raise ValueError("candidate_source_mismatch")
    paragraphs = {item.id: item.text for item in draft.paragraphs}
    checked = [check.obligation for check in review.obligation_checks]
    if len(checked) != len(set(checked)) or set(checked) != set(profile.obligations):
        raise ValueError("obligation_coverage_mismatch")
    for check in review.obligation_checks:
        if any(reference not in paragraphs for reference in check.evidence_ids):
            raise ValueError("unknown_evidence")
        if check.status == "supported" and not check.evidence_ids:
            raise ValueError("missing_support_location")
    for issue in review.issues:
        if issue.location not in paragraphs or issue.quote not in paragraphs[issue.location]:
            raise ValueError("invalid_issue_source")
    contradicted = review.answer_status == "contradicted" or any(
        check.status == "contradicted" for check in review.obligation_checks
    )
    if (contradicted or review.verdict == "reject_route") and not review.issues:
        raise ValueError("missing_contradiction_source")
    if review.verdict == "accept":
        if review.answer_status != "supported" or review.issues or any(
            check.status != "supported" for check in review.obligation_checks
        ):
            raise ValueError("inconsistent_accept")
        if profile.answer_mode in {"choice", "judgment", "fill_blank"} and candidate is None:
            raise ValueError("objective_answer_not_extracted")
    return review


def solution_rank(
    draft: SolutionDraft, candidate: TextCandidate | None, review: DraftAudit | NarrativeAudit | None,
) -> tuple[int, float, int]:
    if draft.truncated:
        return (1, 0.0, int(candidate is not None))
    if review is None:
        return (2, 0.0, int(candidate is not None))
    if review.verdict == "accept":
        return (3, 1.0, int(candidate is not None))
    if isinstance(review, NarrativeAudit):
        return (0 if review.verdict == "reject_route" else 2, 0.0, int(candidate is not None))
    if review.verdict == "reject_route" or review.answer_status == "contradicted" or any(
        check.status == "contradicted" for check in review.obligation_checks
    ):
        return (0, 0.0, int(candidate is not None))
    supported = sum(check.status == "supported" for check in review.obligation_checks)
    return (2, supported / max(1, len(review.obligation_checks)), int(candidate is not None))
