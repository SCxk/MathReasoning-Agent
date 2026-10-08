from typing import Literal

from pydantic import BaseModel, Field


class DefinitionProposal(BaseModel):
    # 这里没有 id 和 status。
    # ID 与 authoritative status 由 Runtime 在 verifier accept 后分配。
    definition_type: Literal["variable", "notation", "object", "auxiliary"]
    statement: str
    purpose: str = ""
    depends_on: list[str] = Field(default_factory=list)


class ResultProposal(BaseModel):
    # 同样没有 id/status。
    # 这是候选结果，而不是 state 中的正式 Result。
    result_type: Literal[
        "equation",
        "inequality",
        "identity",
        "derived_fact",
        "case_result",
        "bound",
        "construction",
        "contradiction",
        "completeness",
    ]
    statement: str
    justification: str
    depends_on: list[str] = Field(default_factory=list)


class TaskProposal(BaseModel):
    task_type: Literal[
        "formalize",
        "derive",
        "compute",
        "case_analysis",
        "verify_candidate",
        "completeness",
        "lower_bound",
        "upper_bound",
        "construction",
        "proof",
        "sanity_check",
    ]
    statement: str
    priority: int = 0
    required: bool = True
    depends_on_tasks: list[str] = Field(default_factory=list)


class ReasoningStep(BaseModel):
    type: Literal["reasoning_step"]

    # 本轮主要试图解决的 Task ID。
    current_task: str

    # 本轮主动使用的 authoritative 前提。
    used_facts: list[str] = Field(default_factory=list)
    used_definitions: list[str] = Field(default_factory=list)
    used_results: list[str] = Field(default_factory=list)

    # 本轮做了什么的简短摘要。
    step_summary: str

    # 完整自然语言解答或当前宏任务的完整证明草稿。
    solution_draft: str = ""

    # 新定义 proposal。
    new_definitions: list[DefinitionProposal] = Field(default_factory=list)

    # 新推导 proposal。
    new_results: list[ResultProposal] = Field(default_factory=list)

    # 新发现的候选最终答案。
    # Runtime 会为它们创建 CandidateAnswer(status="candidate")。
    candidate_answers: list[str] = Field(default_factory=list)

    # Solver 认为本轮已经完成的 Task。
    # 注意：只是关闭申请。
    # Verifier accept 后 Runtime 才真正 status=done。
    closed_tasks: list[str] = Field(default_factory=list)

    # Solver 认为推理中出现的新 Task。
    # 只是 proposal，Runtime/Planner 负责审核。
    new_tasks: list[TaskProposal] = Field(default_factory=list)

    # Solver 认为已经可以结束。
    # 只是“申请 final”，没有结束权限。
    request_finalization: bool = False


class CheckItem(BaseModel):
    passed: bool
    reason: str = ""


class StepVerification(BaseModel):
    verdict: Literal["accept", "reject"]
    logical_validity: CheckItem = Field(default_factory=lambda: CheckItem(passed=True))
    definition_consistency: CheckItem = Field(default_factory=lambda: CheckItem(passed=True))
    algebra_correctness: CheckItem = Field(default_factory=lambda: CheckItem(passed=True))
    quantifier_correctness: CheckItem = Field(default_factory=lambda: CheckItem(passed=True))
    dependency_validity: CheckItem = Field(default_factory=lambda: CheckItem(passed=True))
    actual_progress: CheckItem = Field(default_factory=lambda: CheckItem(passed=True))
    task_completion_validity: CheckItem = Field(
        default_factory=lambda: CheckItem(passed=True)
    )
    reason: str
    retry_instruction: str = ""
    error_category: Literal[
        "none",
        "algebra_error",
        "definition_drift",
        "quantifier_error",
        "unsupported_claim",
        "dependency_error",
        "incomplete_case_analysis",
        "repeated_route",
        "candidate_failure",
        "other",
    ] = "none"

class CandidateVerification(BaseModel):
    verdict: Literal["accept", "reject", "conflict"]
    reason: str
    independent_method: str = ""
    falsification_attempt: str = ""
    method_type: Literal[
        "direct_substitution",
        "alternate_representation",
        "boundary_analysis",
        "counterexample_search",
        "small_case_enumeration",
        "independent_derivation",
        "other",
    ] | None = None
    checked_claims: list[str] = Field(default_factory=list)
    tested_cases: list[str] = Field(default_factory=list)
    route_difference: str = ""
    failed_route_assessment: Literal[
        "not_applicable", "not_reused", "repaired", "unresolved"
    ] = "not_applicable"
    failed_route_reason: str = ""


class FinalAnswer(BaseModel):
    answer: str
    reasoning_summary: str = ""


class DraftClaim(BaseModel):
    id: str
    claim_type: Literal["definition", "result"]
    statement: str
    depends_on: list[str] = Field(default_factory=list)


class SolutionDraft(BaseModel):
    task_id: str
    version: int = 1
    text: str = ""
    claims: list[DraftClaim] = Field(default_factory=list)
    candidate_answers: list[str] = Field(default_factory=list)
    closed_tasks: list[str] = Field(default_factory=list)
    request_finalization: bool = False


class CritiqueOutput(BaseModel):
    verdict: Literal["accept", "repair", "reject_route"]
    accepted_claims: list[str] = Field(default_factory=list)
    invalid_claims: list[str] = Field(default_factory=list)
    candidate_assessment: Literal[
        "supported", "uncertain", "conflict", "absent"
    ] = "absent"
    reason: str = ""
    repair_instruction: str = ""
    failed_route_summary: str = ""
    failed_route_assessment: Literal[
        "not_applicable", "not_reused", "repaired", "unresolved"
    ] = "not_applicable"
    failed_route_reason: str = ""


class CandidateSetVerification(BaseModel):
    verdict: Literal["accept", "incomplete", "reject"]
    verified_candidate_ids: list[str] = Field(default_factory=list)
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    complete_answer: str = ""
    missing_cases: list[str] = Field(default_factory=list)
    reason: str = ""
    repair_instruction: str = ""


class DomainClassificationOutput(BaseModel):
    primary_category: str = "unknown"
    secondary_categories: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""


class FormalizationOutput(BaseModel):
    problem_facts: list[dict] = Field(default_factory=list)


class StrategyOutput(BaseModel):
    execution_mode: Literal["direct", "draft", "macro"] = "draft"
    problem_type: str = "unknown"
    selected_skill_ids: list[str] = Field(default_factory=list)
    core_methods: list[str] = Field(default_factory=list)
    phase_plan: list[str] = Field(default_factory=list)
    risk_controls: list[str] = Field(default_factory=list)
    do_not: list[str] = Field(default_factory=list)
    first_step_instruction: str = ""
    initial_task_revisions: list[dict] = Field(default_factory=list)
    macro_tasks: list[dict] = Field(default_factory=list)
    sanitization_warnings: list[str] = Field(default_factory=list)


class ReplanOutput(BaseModel):
    diagnosis: str = ""
    avoid_routes: list[str] = Field(default_factory=list)
    reuse_results: list[str] = Field(default_factory=list)
    new_tasks: list[dict] = Field(default_factory=list)
    first_step_instruction: str = ""
