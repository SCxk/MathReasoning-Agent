from copy import deepcopy
import re
import time

from reasoning_agent.custom2.models import (
    AgentState,
    BranchState,
    CandidateAnswer,
    CandidateSetVerificationRecord,
    CandidateVerificationRecord,
    CompletionRequirement,
    Definition,
    DerivedResult,
    ErrorRecord,
    ProblemFact,
    ProgressAudit,
    ReplanRecord,
    Task,
)
from reasoning_agent.custom2.schemas import (
    CandidateSetVerification,
    CandidateVerification,
    ReasoningStep,
    SolutionDraft,
    DraftClaim,
    StepVerification,
    TaskProposal,
)
from reasoning_agent.custom2.strategy_skills import ALLOWED_SKILL_CATEGORIES


PROBLEM_TYPES = {
    "unknown",
    "numeric",
    "equation",
    "sequence",
    "combinatorics",
    "geometry",
    "extremum",
    "proof",
    "game",
    "functional_equation",
    "number_theory",
    "离散数学",
    "数值分析",
    "测度积分",
    "微分几何",
    "概率论",
    "抽象代数",
    "随机过程",
    "复分析",
    "常微分方程",
    "统计推断",
    "泛函分析",
    "线性回归",
    "偏微分方程",
    "非基础及进阶课程",
    "高等代数",
    "运筹学",
    "数学分析",
    "拓扑学",
} | set(ALLOWED_SKILL_CATEGORIES)

REPLAN_TRIGGERS = {
    "task_rejected_twice",
    "task_protocol_failure",
    "no_new_evidence",
    "no_executable_task",
    "requirements_stalled",
    "model_replan",
    "finalizer_failed",
    "manual",
}


def initialize_state(problem: str) -> AgentState:
    state = AgentState(problem=problem)
    state.branches.append(BranchState(id="B1", idea="默认解题路线", status="active"))
    state.active_branch_id = "B1"
    return state


def commit_formalization(
    state: AgentState,
    problem_facts: list[ProblemFact],
    tasks: list[Task],
    problem_type: str = "unknown",
    secondary_problem_types: list[str] | None = None,
    classification_confidence: float = 0.0,
    classification_reason: str = "",
) -> AgentState:
    state.problem_type = problem_type if problem_type in PROBLEM_TYPES else "unknown"
    state.secondary_problem_types = [
        item for item in (secondary_problem_types or []) if item in PROBLEM_TYPES
    ]
    state.classification_confidence = classification_confidence
    state.classification_reason = classification_reason
    state.problem_facts.extend(problem_facts)
    state.tasks.extend(tasks)
    if not state.requirements:
        state.requirements.extend(infer_completion_requirements(state))
    state.phase = "solve"
    return state


def commit_step(
    state: AgentState,
    step: ReasoningStep,
    verification: StepVerification,
) -> AgentState:
    assert verification.verdict == "accept"

    state.solver_call_count += 1
    state.accepted_step_count += 1
    state.local_retry_count = 0

    created_result_ids: list[str] = []
    created_evidence_ids: list[str] = []

    for proposal in step.new_definitions:
        definition = Definition(
            id=next_definition_id(state),
            definition_type=proposal.definition_type,
            statement=proposal.statement,
            purpose=proposal.purpose,
            depends_on=proposal.depends_on,
            status="verified",
            source_step=state.accepted_step_count,
            branch_id=state.active_branch_id,
        )
        state.definitions.append(definition)
        created_evidence_ids.append(definition.id)

    for proposal in step.new_results:
        result = DerivedResult(
            id=next_result_id(state),
            result_type=proposal.result_type,
            statement=proposal.statement,
            justification=proposal.justification,
            depends_on=proposal.depends_on,
            status="verified",
            source_step=state.accepted_step_count,
            branch_id=state.active_branch_id,
        )
        state.derived_results.append(result)
        created_result_ids.append(result.id)
        created_evidence_ids.append(result.id)

    for answer in step.candidate_answers:
        candidate = register_candidate(state, value=answer, support_results=created_result_ids)
        created_evidence_ids.append(candidate.id)

    for task_id in step.closed_tasks:
        task = find_task(state, task_id)
        if task is not None:
            task.status = "done"
            task.completed_by = created_evidence_ids.copy()

    for proposal in step.new_tasks:
        maybe_add_task_proposal(state, proposal)

    active_task = choose_active_task(state)
    if active_task is not None and created_evidence_ids:
        active_task.status = "done"
        active_task.completed_by = created_evidence_ids.copy()

    refresh_completion_requirements(state)
    audit_step_progress(state, step, created_evidence_ids)

    branch = get_active_branch(state)
    if branch:
        branch.local_result_ids.extend(created_result_ids)
        branch.last_accepted_step = step.model_dump()

    return state


def reject_step(
    state: AgentState,
    step: ReasoningStep,
    verification: StepVerification,
) -> AgentState:
    state.solver_call_count += 1
    state.local_retry_count += 1
    error = ErrorRecord(
        id=next_error_id(state),
        branch_id=state.active_branch_id,
        step_summary=step.step_summary,
        category=(
            verification.error_category
            if verification.error_category != "none"
            else "other"
        ),
        reason=verification.reason,
        retry_instruction=verification.retry_instruction,
        related_ids=step.used_facts + step.used_definitions + step.used_results,
    )
    state.error_memory.append(error)
    task = find_task(state, step.current_task)
    if task is not None:
        task.last_error_id = error.id
        task.math_rejects += 1
        task.status = "open"
        if task.math_rejects >= state.max_local_retries:
            task.status = "blocked"
            task.blocked_reason = (
                f"连续数学拒绝 {task.math_rejects} 次，必须切换方法。"
            )
    return state


def record_protocol_failure(
    state: AgentState,
    task: Task,
    reason: str,
    error_id: str | None = None,
    trigger: str = "task_protocol_failure",
) -> bool:
    task.protocol_failures += 1
    task.blocked_reason = reason
    if error_id:
        task.last_error_id = error_id
    if task.protocol_failures >= state.max_local_retries:
        task.status = "blocked"
        task.blocked_reason = (
            f"连续协议失败 {task.protocol_failures} 次，必须切换方法。"
        )
        record_replan(
            state,
            trigger=trigger if trigger in REPLAN_TRIGGERS else "manual",
            reason=task.blocked_reason or reason,
            invalidate_tasks=[],
            new_tasks=[
                _build_route_reset_task(
                    state,
                    task,
                    prefix="切换路线：",
                    reason=task.blocked_reason or reason,
                )
            ],
        )
        return True
    return False


def register_candidate(
    state: AgentState,
    value: str,
    support_results: list[str],
) -> CandidateAnswer:
    existing = find_candidate_by_value(state, value)
    if existing:
        existing.support_results = list(
            dict.fromkeys([*existing.support_results, *support_results])
        )
        if existing.status in {"rejected", "conflict"}:
            existing.status = "candidate"
            existing.verification_reason = "候选由新的已验证推导重新提出，等待复核。"
            existing.verification_record = None
            _capture_candidate_source_route(state, existing)
        return existing

    candidate = CandidateAnswer(
        id=next_candidate_id(state),
        value=value,
        status="candidate",
        support_results=support_results,
        source_step=state.accepted_step_count,
    )
    _capture_candidate_source_route(state, candidate)
    state.candidates.append(candidate)
    mark_requirement_satisfied(state, "answer_candidate", [candidate.id])
    if not state.efficient_runtime:
        maybe_add_task(
            state,
            Task(
                id=next_task_id(state),
                kind="verify",
                objective=f"独立验证候选答案 {value}",
                status="open",
                priority=100,
                requirement_ids=["REQ_candidate_verified"],
                depends_on=[candidate.id],
                candidate_id=candidate.id,
                created_by="candidate_registration",
            ),
        )
    return candidate


def _capture_candidate_source_route(
    state: AgentState, candidate: CandidateAnswer
) -> None:
    candidate.source_draft_version = state.solution_draft.version
    candidate.source_solution_draft = state.solution_draft.text
    candidate.source_strategy_methods = [
        method
        for guidance in state.strategy_guidance
        if guidance.status == "active"
        for method in guidance.core_methods
    ]


def apply_candidate_verification(
    state: AgentState,
    candidate: CandidateAnswer,
    verification: CandidateVerification,
) -> AgentState:
    record = CandidateVerificationRecord(
        id=next_candidate_verification_id(state),
        candidate_id=candidate.id,
        verdict=verification.verdict,
        reason=verification.reason,
        independent_method=verification.independent_method,
        falsification_attempt=verification.falsification_attempt,
        method_type=verification.method_type or "",
        checked_claims=verification.checked_claims,
        tested_cases=verification.tested_cases,
        route_difference=verification.route_difference,
    )
    state.candidate_verifications.append(record)
    candidate.verification_record = record.id
    candidate.verification_reason = verification.reason
    if verification.verdict == "accept":
        candidate.status = "verified"
        mark_requirement_satisfied(
            state,
            "candidate_verified",
            [candidate.id, record.id],
        )
    elif verification.verdict == "conflict":
        candidate.status = "conflict"
        mark_requirement_conflict(state, "candidate_verified", [candidate.id, record.id])
    else:
        candidate.status = "rejected"

    for task in state.tasks:
        if task.candidate_id == candidate.id and task.kind == "verify":
            task.status = "done" if verification.verdict == "accept" else "invalid"
            task.completed_by = [candidate.id, record.id] if verification.verdict == "accept" else []
            if verification.verdict != "accept":
                task.invalidated_by = record.id
            task.candidate_verification_record = record.id
    refresh_completion_requirements(state)
    return state


def apply_candidate_set_verification(
    state: AgentState,
    verification: CandidateSetVerification,
) -> CandidateSetVerificationRecord:
    assessed_ids = [candidate.id for candidate in state.candidates]
    actual_verified = {
        candidate.id for candidate in state.candidates if candidate.status == "verified"
    }
    actual_rejected = {
        candidate.id for candidate in state.candidates if candidate.status == "rejected"
    }
    unresolved = [
        candidate.id
        for candidate in state.candidates
        if candidate.status in {"candidate", "conflict"}
    ]
    normalized = verification.model_copy(deep=True)
    reported_verified = set(normalized.verified_candidate_ids)
    reported_rejected = set(normalized.rejected_candidate_ids)
    if normalized.verdict == "accept" and (
        not actual_verified
        or unresolved
        or reported_verified != actual_verified
        or not reported_rejected.issubset(actual_rejected)
        or not normalized.complete_answer.strip()
    ):
        normalized.verdict = "incomplete"
        normalized.reason = (
            "集合验证输出与逐候选验证状态不一致，或缺少完整答案。"
        )
        normalized.repair_instruction = (
            normalized.repair_instruction
            or "重新核对全部候选状态，并给出包含所有正确候选的完整答案。"
        )

    record = CandidateSetVerificationRecord(
        id=next_candidate_set_verification_id(state),
        verdict=normalized.verdict,
        assessed_candidate_ids=assessed_ids,
        verified_candidate_ids=sorted(actual_verified),
        rejected_candidate_ids=sorted(actual_rejected),
        complete_answer=normalized.complete_answer,
        missing_cases=list(normalized.missing_cases),
        reason=normalized.reason,
        repair_instruction=normalized.repair_instruction,
    )
    state.candidate_set_verifications.append(record)
    refresh_completion_requirements(state)
    return record


def can_finalize(state: AgentState) -> bool:
    if not state.requirements:
        state.requirements.extend(infer_completion_requirements(state))
    refresh_completion_requirements(state)
    if any(fact.status == "invalid" for fact in state.problem_facts):
        return False
    if any(result.status == "invalid" for result in state.derived_results):
        return False
    if any(candidate.status == "conflict" for candidate in state.candidates):
        return False
    if pending_required_tasks(state):
        return False
    return bool(state.requirements) and all(
        req.status == "satisfied" for req in state.requirements
    )


def pending_required_tasks(state: AgentState) -> list[Task]:
    return [
        task
        for task in state.tasks
        if task.required and task.status in {"open", "active", "blocked"}
    ]


def can_finalize_best_effort(state: AgentState) -> bool:
    if any(candidate.status == "conflict" for candidate in state.candidates):
        return False
    usable_candidates = [
        candidate
        for candidate in state.candidates
        if candidate.status in {"candidate", "verified"} and candidate.value.strip()
    ]
    return bool(
        usable_candidates
        or state.solution_draft.text.strip()
        or any(result.status == "verified" for result in state.derived_results)
    )


def remaining_seconds(state: AgentState, now: float | None = None) -> float:
    if state.deadline_at <= 0:
        return float("inf")
    return max(0.0, state.deadline_at - (time.monotonic() if now is None else now))


def time_phase(state: AgentState, now: float | None = None) -> str:
    remaining = remaining_seconds(state, now)
    if remaining <= state.finalize_reserve_seconds:
        return "final_reserve"
    if remaining <= state.convergence_reserve_seconds:
        return "converge"
    return "normal"


def candidate_conflict_groups(state: AgentState) -> list[list[CandidateAnswer]]:
    groups: dict[str, list[CandidateAnswer]] = {}
    for candidate in state.candidates:
        if candidate.status not in {"candidate", "verified", "conflict"}:
            continue
        key = _normalize_candidate_value(candidate.value)
        if key:
            groups.setdefault(key, []).append(candidate)
    return list(groups.values())


def has_candidate_conflict(state: AgentState) -> bool:
    return len(candidate_conflict_groups(state)) > 1


def reasoning_step_to_solution_draft(
    step: ReasoningStep, version: int = 1
) -> SolutionDraft:
    claims = [
        DraftClaim(
            id=f"DRAFT-D{index}",
            claim_type="definition",
            statement=proposal.statement,
            depends_on=list(proposal.depends_on),
        )
        for index, proposal in enumerate(step.new_definitions, start=1)
    ]
    claims.extend(
        DraftClaim(
            id=f"DRAFT-R{index}",
            claim_type="result",
            statement=proposal.statement,
            depends_on=list(proposal.depends_on),
        )
        for index, proposal in enumerate(step.new_results, start=1)
    )
    text = step.solution_draft.strip() or step.step_summary.strip()
    return SolutionDraft(
        task_id=step.current_task,
        version=version,
        text=text,
        claims=claims,
        candidate_answers=list(step.candidate_answers),
        closed_tasks=list(step.closed_tasks),
        request_finalization=step.request_finalization,
    )


def validate_reasoning_step_protocol(
    state: AgentState, step: ReasoningStep, current_task: Task
) -> list[str]:
    errors: list[str] = []
    if step.current_task != current_task.id:
        errors.append(
            f"current_task={step.current_task} does not match selected {current_task.id}"
        )
    known = _known_id_map(state)
    for item_id in step.used_facts + step.used_definitions + step.used_results:
        if item_id not in known or known[item_id].status != "verified":
            errors.append(f"unknown or unverified dependency {item_id}")
    for proposal in [*step.new_definitions, *step.new_results]:
        if not proposal.statement.strip():
            errors.append("empty proposal statement")
        for dependency in proposal.depends_on:
            if dependency not in known or known[dependency].status != "verified":
                errors.append(f"unknown or unverified dependency {dependency}")
    normalized_definitions = [
        re.sub(r"\s+", "", proposal.statement) for proposal in step.new_definitions
    ]
    if len(normalized_definitions) != len(set(normalized_definitions)):
        errors.append("duplicate definition proposal")
    existing_definitions = {
        re.sub(r"\s+", "", item.statement)
        for item in state.definitions
        if item.status == "verified"
    }
    if any(item in existing_definitions for item in normalized_definitions):
        errors.append("definition duplicates authoritative state")
    task_ids = {task.id for task in state.tasks}
    for task_id in step.closed_tasks:
        if task_id not in task_ids:
            errors.append(f"cannot close unknown task {task_id}")
    if not (
        step.solution_draft.strip()
        or step.new_definitions
        or step.new_results
        or step.candidate_answers
        or step.new_tasks
    ):
        errors.append("empty solution draft and proposal batch")
    return list(dict.fromkeys(errors))


def accepted_claim_closure(
    draft: SolutionDraft,
    accepted_claim_ids: list[str],
    invalid_claim_ids: list[str],
) -> set[str]:
    all_claim_ids = {claim.id for claim in draft.claims}
    invalid = set(invalid_claim_ids) & all_claim_ids
    accepted = (set(accepted_claim_ids) & all_claim_ids) - invalid
    changed = True
    while changed:
        changed = False
        for claim in draft.claims:
            if claim.id not in accepted:
                continue
            draft_dependencies = {
                dependency for dependency in claim.depends_on if dependency in all_claim_ids
            }
            if not draft_dependencies.issubset(accepted):
                accepted.remove(claim.id)
                changed = True
    return accepted


def route(state: AgentState) -> str:
    if can_finalize(state):
        return "finalize"
    if state.solver_call_count >= state.max_solver_calls:
        return "incomplete"
    if state.accepted_step_count >= state.max_accepted_steps:
        return "incomplete"
    if state.strategy_reset_count >= state.max_strategy_resets:
        return "incomplete"
    if choose_candidate_to_verify(state) is not None:
        return "candidate_verify"
    if state.local_retry_count >= state.max_local_retries:
        if choose_open_task(state) is not None:
            return "solve"
        if any(req.status == "unsatisfied" for req in state.requirements):
            return "solve"
        return "incomplete"
    if choose_open_task(state) is None:
        if any(req.status == "unsatisfied" for req in state.requirements):
            return "solve"
        return "incomplete"
    return "solve"


def choose_candidate_to_verify(state: AgentState) -> CandidateAnswer | None:
    for candidate in state.candidates:
        if candidate.status == "candidate":
            return candidate
    return None


def rollback_invalid_result(state: AgentState, result_id: str, reason: str = "") -> AgentState:
    invalidated = set()
    target = find_result(state, result_id)
    if target is not None:
        target.status = "invalid"
        invalidated.add(target.id)

    changed = True
    while changed:
        changed = False
        for result in state.derived_results:
            if result.status == "verified" and any(dep in invalidated for dep in result.depends_on):
                result.status = "invalid"
                invalidated.add(result.id)
                changed = True

    for task in state.tasks:
        if task.status == "done" and any(rid in invalidated for rid in task.completed_by):
            task.status = "open"
            task.completed_by = []
            task.candidate_verification_record = None

    for candidate in state.candidates:
        if candidate.status in {"candidate", "verified", "conflict"} and any(
            rid in invalidated for rid in candidate.support_results
        ):
            candidate.status = "rejected"
            candidate.verification_reason = reason or "supporting result was invalidated"
    for req in state.requirements:
        if any(item_id in invalidated for item_id in req.satisfied_by):
            req.status = "unsatisfied"
            req.satisfied_by = [
                item_id for item_id in req.satisfied_by if item_id not in invalidated
            ]
            req.blocked_by.extend(sorted(invalidated))
    return state


def validate_state_invariants(state: AgentState) -> list[str]:
    errors: list[str] = []
    known = _known_id_map(state)

    if state.solution_draft.version < 0:
        errors.append("solution draft version cannot be negative")
    if state.solution_draft.status != "empty" and state.solution_draft.version < 1:
        errors.append("non-empty solution draft needs a positive version")
    if state.repair_count < 0 or state.model_replan_count < 0:
        errors.append("repair/replan counters cannot be negative")
    if state.finalize_reserve_seconds < 0 or state.convergence_reserve_seconds < 0:
        errors.append("time reserves cannot be negative")
    if state.convergence_reserve_seconds < state.finalize_reserve_seconds:
        errors.append("convergence reserve cannot be smaller than final reserve")

    accepted_claim_ids: set[str] = set()
    for claim in state.accepted_claims:
        if claim.id in accepted_claim_ids:
            errors.append(f"duplicate accepted claim {claim.id}")
        accepted_claim_ids.add(claim.id)
        if claim.source_draft_version > state.solution_draft.version:
            errors.append(f"{claim.id}: claim comes from a future draft version")
        if claim.authoritative_id and claim.authoritative_id not in known:
            errors.append(
                f"{claim.id}: unknown authoritative id {claim.authoritative_id}"
            )
        for dependency in claim.depends_on:
            if dependency.startswith("DRAFT-") and dependency not in accepted_claim_ids:
                errors.append(f"{claim.id}: unaccepted draft dependency {dependency}")

    for result in state.derived_results:
        if result.status not in {"verified", "invalid"}:
            errors.append(f"{result.id}: DerivedResult status cannot be candidate")
        for dep in result.depends_on:
            if dep not in known:
                errors.append(f"{result.id}: unknown dependency {dep}")
            elif result.status == "verified" and known[dep].status != "verified":
                errors.append(f"{result.id}: dependency {dep} is not verified")

    for candidate in state.candidates:
        if candidate.status == "verified" and not candidate.verification_record:
            errors.append(f"{candidate.id}: verified candidate needs independent verification")

    verification_by_id = {record.id: record for record in state.candidate_verifications}
    for candidate in state.candidates:
        if candidate.status != "verified" or not candidate.verification_record:
            continue
        record = verification_by_id.get(candidate.verification_record)
        if record is None or record.candidate_id != candidate.id or record.verdict != "accept":
            errors.append(f"{candidate.id}: invalid candidate verification record")
            continue
        if not (
            record.independent_method.strip()
            and record.falsification_attempt.strip()
            and record.method_type.strip()
            and record.checked_claims
            and record.tested_cases
            and record.route_difference.strip()
        ):
            errors.append(f"{candidate.id}: incomplete independent verification evidence")

    known_evidence = set(known) | {c.id for c in state.candidates} | {
        record.id for record in state.candidate_verifications
    }
    known_requirements = {req.id for req in state.requirements}
    for req in state.requirements:
        for evidence_id in req.satisfied_by:
            if evidence_id not in known_evidence:
                errors.append(f"{req.id}: satisfied_by unknown evidence {evidence_id}")
        if req.status == "satisfied" and not req.satisfied_by:
            errors.append(f"{req.id}: satisfied requirement needs supporting evidence")

    known_task_ids = {task.id for task in state.tasks}
    for task in state.tasks:
        if task.status == "done" and not task.completed_by:
            errors.append(f"{task.id}: done task must have support")
        for req_id in task.requirement_ids:
            if req_id not in known_requirements:
                errors.append(f"{task.id}: unknown requirement {req_id}")
        for dep in task.depends_on:
            if (
                dep not in known_evidence
                and dep not in known_requirements
                and dep not in known_task_ids
            ):
                errors.append(f"{task.id}: unknown dependency {dep}")

    if can_finalize(state):
        if any(candidate.status == "conflict" for candidate in state.candidates):
            errors.append("final gate passed with candidate conflict")
        if any(fact.status == "invalid" for fact in state.problem_facts):
            errors.append("final gate passed with invalid problem fact")
        if any(req.status != "satisfied" for req in state.requirements):
            errors.append("final gate passed with unsatisfied requirement")
    return errors


def snapshot_authoritative_state(state: AgentState) -> dict:
    clone = deepcopy(state)
    return {
        "problem_facts": [pf.model_dump() for pf in clone.problem_facts],
        "definitions": [d.model_dump() for d in clone.definitions],
        "derived_results": [r.model_dump() for r in clone.derived_results],
        "requirements": [r.model_dump() for r in clone.requirements],
        "tasks": [t.model_dump() for t in clone.tasks],
        "candidates": [c.model_dump() for c in clone.candidates],
    }


def infer_completion_requirements(state: AgentState) -> list[CompletionRequirement]:
    problem_type = state.problem_type if state.problem_type in PROBLEM_TYPES else "unknown"
    if problem_type == "proof":
        kinds = ["proof_complete"]
    elif problem_type == "extremum":
        kinds = [
            "answer_candidate",
            "candidate_verified",
            "lower_bound",
            "upper_bound",
            "construction_verified",
            "case_coverage",
        ]
    elif problem_type in {"combinatorics", "game"}:
        kinds = ["answer_candidate", "candidate_verified", "case_coverage"]
    else:
        kinds = ["answer_candidate", "candidate_verified"]
    if state.efficient_runtime and problem_type != "proof":
        if "candidate_set_complete" not in kinds:
            kinds.append("candidate_set_complete")
    if _looks_like_completeness_problem(state.problem):
        if "completeness" not in kinds:
            kinds.append("completeness")
    if any(task.kind == "case_analysis" for task in state.tasks):
        if "case_coverage" not in kinds:
            kinds.append("case_coverage")
    return [
        CompletionRequirement(
            id=_requirement_id_for_kind(kind),
            kind=kind,
            description=_requirement_description(kind),
        )
        for kind in kinds
    ]


def refresh_completion_requirements(state: AgentState) -> AgentState:
    if not state.requirements:
        state.requirements.extend(infer_completion_requirements(state))
    for req in state.requirements:
        req.status = "unsatisfied"
        req.satisfied_by = []
        req.blocked_by = []

    valid_candidates = [
        candidate
        for candidate in state.candidates
        if candidate.status in {"candidate", "verified"}
    ]
    verified_candidates = [
        candidate
        for candidate in state.candidates
        if candidate.status == "verified" and candidate.verification_record
    ]
    conflicts = [candidate.id for candidate in state.candidates if candidate.status == "conflict"]
    if valid_candidates:
        mark_requirement_satisfied(
            state, "answer_candidate", [candidate.id for candidate in valid_candidates]
        )
    if verified_candidates:
        support: list[str] = []
        for candidate in verified_candidates:
            support.append(candidate.id)
            if candidate.verification_record:
                support.append(candidate.verification_record)
        mark_requirement_satisfied(state, "candidate_verified", support)
    elif conflicts:
        mark_requirement_conflict(state, "candidate_verified", conflicts)

    for result in state.derived_results:
        if result.status != "verified":
            continue
        text = result.statement
        if result.result_type == "completeness":
            mark_requirement_satisfied(state, "proof_complete", [result.id])
            mark_requirement_satisfied(state, "case_coverage", [result.id])
            mark_requirement_satisfied(state, "completeness", [result.id])
        if result.result_type == "construction":
            mark_requirement_satisfied(state, "construction_verified", [result.id])
        if result.result_type == "bound":
            if _looks_like_lower_bound(text):
                mark_requirement_satisfied(state, "lower_bound", [result.id])
            if _looks_like_upper_bound(text):
                mark_requirement_satisfied(state, "upper_bound", [result.id])
    if state.candidate_set_verifications:
        latest_set_check = state.candidate_set_verifications[-1]
        current_candidate_ids = {candidate.id for candidate in state.candidates}
        if (
            latest_set_check.verdict == "accept"
            and set(latest_set_check.assessed_candidate_ids) == current_candidate_ids
        ):
            evidence = [latest_set_check.id, *latest_set_check.verified_candidate_ids]
            mark_requirement_satisfied(state, "candidate_set_complete", evidence)
            mark_requirement_satisfied(state, "completeness", evidence)
            mark_requirement_satisfied(state, "case_coverage", evidence)
        elif latest_set_check.verdict in {"incomplete", "reject"}:
            mark_requirement_conflict(
                state, "candidate_set_complete", [latest_set_check.id]
            )
    return state


def mark_requirement_satisfied(
    state: AgentState, kind: str, evidence_ids: list[str]
) -> CompletionRequirement | None:
    req = _find_requirement_by_kind(state, kind)
    if req is None:
        return None
    if req.status != "conflict":
        req.status = "satisfied"
    for evidence_id in evidence_ids:
        if evidence_id and evidence_id not in req.satisfied_by:
            req.satisfied_by.append(evidence_id)
    return req


def mark_requirement_conflict(
    state: AgentState, kind: str, evidence_ids: list[str]
) -> CompletionRequirement | None:
    req = _find_requirement_by_kind(state, kind)
    if req is None:
        return None
    req.status = "conflict"
    for evidence_id in evidence_ids:
        if evidence_id and evidence_id not in req.blocked_by:
            req.blocked_by.append(evidence_id)
    return req


def ensure_tasks_from_tasks(state: AgentState) -> AgentState:
    return state


def choose_open_task(state: AgentState) -> Task | None:
    ensure_tasks_from_tasks(state)
    available = [
        task
        for task in state.tasks
        if task.status == "open" and _task_dependencies_satisfied(state, task)
    ]
    if not available:
        return None
    return sorted(available, key=lambda task: (-task.priority, task.id))[0]


def choose_active_task(state: AgentState) -> Task | None:
    ensure_tasks_from_tasks(state)
    active = [task for task in state.tasks if task.status == "active"]
    if not active:
        return None
    return sorted(active, key=lambda task: (-task.priority, task.id))[0]


def activate_task(task: Task) -> Task:
    task.status = "active"
    task.attempts += 1
    return task


def restore_active_task(task: Task) -> Task:
    if task.status == "active":
        task.status = "open"
    return task


def maybe_add_task(state: AgentState, task: Task) -> Task:
    for existing in state.tasks:
        if (
            existing.objective.strip() == task.objective.strip()
            and existing.kind == task.kind
            and existing.status in {"open", "active"}
        ):
            return existing
    state.tasks.append(task)
    return task


def maybe_replan_from_requirements(state: AgentState, trigger: str) -> bool:
    refresh_completion_requirements(state)
    unsatisfied = [req for req in state.requirements if req.status == "unsatisfied"]
    if not unsatisfied:
        return False
    task_ids_before = {task.id for task in state.tasks}
    new_tasks = [
        Task(
            id=next_task_id(state, offset=index),
            kind=_task_kind_for_requirement(req),
            objective=f"推进完成条件：{req.description or req.kind}",
            priority=90 - index,
            requirement_ids=[req.id],
            created_by="replanner",
        )
        for index, req in enumerate(unsatisfied)
    ]
    replan = record_replan(
        state,
        trigger=trigger if trigger in REPLAN_TRIGGERS else "manual",
        reason="根据未满足的 CompletionRequirement 生成新任务。",
        new_tasks=new_tasks,
    )
    for task_id in replan.new_tasks:
        task = find_task(state, task_id)
        if task is None:
            continue
        if task.id in task_ids_before and task.status not in {"open", "active"}:
            continue
        if task.status == "open" and _task_dependencies_satisfied(state, task):
            return True
    return False


def record_replan(
    state: AgentState,
    trigger: str,
    reason: str,
    invalidate_tasks: list[str] | None = None,
    new_tasks: list[Task] | None = None,
) -> ReplanRecord:
    invalidated = invalidate_tasks or []
    created: list[str] = []
    for task_id in invalidated:
        task = find_task(state, task_id)
        if task is not None:
            task.status = "invalid"
            task.invalidated_by = trigger
    for task in new_tasks or []:
        added = maybe_add_task(state, task)
        created.append(added.id)
    record = ReplanRecord(
        id=next_replan_id(state),
        trigger=trigger,
        invalidated_tasks=invalidated,
        new_tasks=created,
        reason=reason,
    )
    state.replan_records.append(record)
    return record


def audit_step_progress(
    state: AgentState,
    step: ReasoningStep,
    created_evidence_ids: list[str],
) -> ProgressAudit:
    advanced = [
        req.id
        for req in state.requirements
        if any(evidence_id in req.satisfied_by for evidence_id in created_evidence_ids)
    ]
    active_task = find_task(state, step.current_task)
    if created_evidence_ids and advanced:
        verdict = "progress"
        state.stagnation_count = 0
        reason = "新证据推进了 CompletionRequirement。"
    elif created_evidence_ids:
        verdict = "no_progress"
        state.stagnation_count += 1
        reason = "新证据未直接推进任何 CompletionRequirement。"
    else:
        verdict = "no_progress"
        state.stagnation_count += 1
        reason = "本步没有产生新证据。"
    audit = ProgressAudit(
        id=next_progress_audit_id(state),
        step_index=state.accepted_step_count,
        verdict=verdict,
        advanced_requirements=advanced,
        task_id=active_task.id if active_task else None,
        reason=reason,
    )
    state.progress_audits.append(audit)
    if verdict == "no_progress" and not created_evidence_ids:
        maybe_replan_from_requirements(state, "no_new_evidence")
    if verdict == "no_progress" and state.stagnation_count >= 2:
        maybe_replan_from_requirements(state, "requirements_stalled")
    return audit


def find_task(state: AgentState, task_id: str) -> Task | None:
    return next((task for task in state.tasks if task.id == task_id), None)


def find_result(state: AgentState, result_id: str) -> DerivedResult | None:
    return next((r for r in state.derived_results if r.id == result_id), None)


def find_candidate_by_value(state: AgentState, value: str) -> CandidateAnswer | None:
    normalized = value.strip()
    return next((c for c in state.candidates if c.value.strip() == normalized), None)


def get_active_branch(state: AgentState) -> BranchState | None:
    if state.active_branch_id is None:
        return None
    return next((b for b in state.branches if b.id == state.active_branch_id), None)


def maybe_add_task_proposal(state: AgentState, proposal: TaskProposal) -> Task:
    for task in state.tasks:
        if (
            task.objective.strip() == proposal.statement.strip()
            and task.kind == _task_kind_from_task_type(proposal.task_type)
        ):
            ensure_tasks_from_tasks(state)
            return task
    task = Task(
        id=next_task_id(state),
        kind=proposal.task_type,
        objective=proposal.statement,
        priority=proposal.priority,
        status="open",
        depends_on=list(proposal.depends_on_tasks),
        created_by="solver",
    )
    state.tasks.append(task)
    ensure_tasks_from_tasks(state)
    return task


def next_definition_id(state: AgentState) -> str:
    return f"D{len(state.definitions) + 1}"


def next_result_id(state: AgentState) -> str:
    return f"R{len(state.derived_results) + 1}"


def next_task_id(state: AgentState, offset: int = 0) -> str:
    existing = [
        int(task.id[1:])
        for task in state.tasks
        if task.id.startswith("T") and task.id[1:].isdigit()
    ]
    return f"T{(max(existing) if existing else 0) + 1 + offset}"


def next_candidate_id(state: AgentState) -> str:
    return f"C{len(state.candidates) + 1}"


def next_error_id(state: AgentState) -> str:
    return f"E{len(state.error_memory) + 1}"


def next_candidate_verification_id(state: AgentState) -> str:
    return f"CV{len(state.candidate_verifications) + 1}"


def next_candidate_set_verification_id(state: AgentState) -> str:
    return f"CSV{len(state.candidate_set_verifications) + 1}"


def next_progress_audit_id(state: AgentState) -> str:
    return f"PA{len(state.progress_audits) + 1}"


def next_replan_id(state: AgentState) -> str:
    return f"RP{len(state.replan_records) + 1}"


def _known_id_map(state: AgentState) -> dict[str, ProblemFact | Definition | DerivedResult]:
    return {
        **{pf.id: pf for pf in state.problem_facts},
        **{d.id: d for d in state.definitions},
        **{r.id: r for r in state.derived_results},
    }


def _normalize_candidate_value(value: str) -> str:
    normalized = re.sub(r"\s+", "", value).strip().lower()
    normalized = normalized.replace("\\boxed{", "").replace("}", "")
    return normalized.strip("。.;；,，")


def _requirement_id_for_kind(kind: str) -> str:
    names = {
        "answer_candidate": "REQ_answer",
        "candidate_verified": "REQ_candidate_verified",
        "proof_complete": "REQ_proof_complete",
        "lower_bound": "REQ_lower_bound",
        "upper_bound": "REQ_upper_bound",
        "construction_verified": "REQ_construction",
        "case_coverage": "REQ_case_coverage",
        "completeness": "REQ_completeness",
        "candidate_set_complete": "REQ_candidate_set_complete",
        "consistency": "REQ_consistency",
    }
    return names.get(kind, f"REQ_{kind}")


def _requirement_description(kind: str) -> str:
    descriptions = {
        "answer_candidate": "提出可判分的候选答案",
        "candidate_verified": "独立验证候选答案满足原题",
        "proof_complete": "证明主命题且依赖链无洞",
        "lower_bound": "证明所求量的下界",
        "upper_bound": "证明所求量的上界",
        "construction_verified": "给出并验证取等或存在性构造",
        "case_coverage": "覆盖全部分类讨论",
        "completeness": "证明无漏解或无遗漏情况",
        "candidate_set_complete": "逐一验证全部候选并证明正确候选集合完备",
        "consistency": "保持证据层无冲突",
    }
    return descriptions.get(kind, kind)


def _find_requirement_by_kind(
    state: AgentState, kind: str
) -> CompletionRequirement | None:
    return next((req for req in state.requirements if req.kind == kind), None)


def _task_kind_from_task_type(task_type: str) -> str:
    mapping = {
        "verify_candidate": "verify",
        "formalize": "derive",
        "completeness": "verify",
    }
    return mapping.get(task_type, task_type)


def _task_status_from_task_status(status: str) -> str:
    mapping = {
        "in_progress": "active",
        "done": "done",
        "invalid": "invalid",
        "blocked": "blocked",
    }
    return mapping.get(status, "open")


def _requirement_ids_for_task(task_type: str) -> list[str]:
    mapping = {
        "verify_candidate": ["REQ_candidate_verified"],
        "lower_bound": ["REQ_lower_bound"],
        "upper_bound": ["REQ_upper_bound"],
        "construction": ["REQ_construction"],
        "completeness": ["REQ_completeness"],
        "candidate_set_complete": ["REQ_candidate_set_complete"],
        "proof": ["REQ_proof_complete"],
        "case_analysis": ["REQ_case_coverage"],
    }
    return mapping.get(task_type, [])


def _task_kind_for_requirement(req: CompletionRequirement) -> str:
    mapping = {
        "answer_candidate": "derive",
        "candidate_verified": "verify",
        "proof_complete": "proof",
        "lower_bound": "lower_bound",
        "upper_bound": "upper_bound",
        "construction_verified": "construction",
        "case_coverage": "case_analysis",
        "completeness": "verify",
        "candidate_set_complete": "verify",
        "consistency": "verify",
    }
    return mapping.get(req.kind, "derive")


def _build_route_reset_task(
    state: AgentState,
    task: Task,
    prefix: str,
    reason: str,
) -> Task:
    objective = task.objective.strip()
    while objective.startswith(prefix):
        objective = objective[len(prefix) :].strip()
    return Task(
        id=next_task_id(state),
        kind="replan",
        objective=f"{prefix}{objective}",
        priority=task.priority + 5,
        requirement_ids=list(task.requirement_ids),
        created_by="replanner",
        blocked_reason=reason,
    )


def _task_dependencies_satisfied(state: AgentState, task: Task) -> bool:
    known = _known_id_map(state)
    candidates = {candidate.id: candidate for candidate in state.candidates}
    requirements = {req.id: req for req in state.requirements}
    tasks = {item.id: item for item in state.tasks}
    for dep in task.depends_on:
        if dep in known and known[dep].status == "verified":
            continue
        if dep in candidates and candidates[dep].status in {"candidate", "verified"}:
            continue
        if dep in requirements and requirements[dep].status == "satisfied":
            continue
        if dep in tasks and tasks[dep].status == "done":
            continue
        return False
    return True


def _looks_like_lower_bound(text: str) -> bool:
    return any(marker in text for marker in ("下界", "至少", "不小于", "≥", ">=", "lower bound"))


def _looks_like_upper_bound(text: str) -> bool:
    return any(marker in text for marker in ("上界", "至多", "不超过", "≤", "<=", "upper bound"))


def _looks_like_completeness_problem(text: str) -> bool:
    normalized = text.lower()
    markers = (
        "所有可能",
        "所有解",
        "所有取值",
        "所有值",
        "全部解",
        "全部可能",
        "可能值",
        "完整",
        "穷尽",
        "列出所有",
        "找出所有",
        "求所有",
        "all possible",
        "all solutions",
        "all values",
        "complete set",
        "exhaustive",
        "enumerate all",
        "every possible",
    )
    return any(marker in normalized for marker in markers)
