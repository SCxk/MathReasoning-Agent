from typing import Literal

from pydantic import BaseModel, Field


class ProblemFact(BaseModel):
    # Runtime 分配的稳定 ID，例如 P1、P2、P3。
    # 不允许模型自行决定 authoritative ID。
    id: str

    # 题目事实的类别。
    #
    # given_value:
    #   题目直接给出的数值，例如“面积为48”“n=2025”。
    #
    # relation:
    #   题目直接给出的对象关系，例如“长比宽多2”。
    #
    # domain_constraint:
    #   题目或数学对象天然带来的定义域/取值约束，
    #   例如“边长为正”“n为正整数”。
    #
    # condition:
    #   其他直接条件，例如“a,b,c互不相同”。
    #
    # target:
    #   对求解目标的结构化描述，例如“求所有可能的a_2025”。
    fact_type: Literal[
        "given_value",
        "relation",
        "domain_constraint",
        "condition",
        "target",
    ]

    # 经过规范化后的题目事实。
    statement: str

    # 对应原题中的证据文本。
    # 用于 Formalization Verifier 回查是否忠实于原题。
    source_text: str

    # 当前事实的可信状态。
    #
    # verified:
    #   已经确认与原题一致，可以作为后续求解的基础条件。
    #
    # invalid:
    #   Formalizer 曾错误抽取该事实，后续 Audit 或重新核验发现错误。
    #
    # 注意：
    #   authoritative state 中不保存 candidate ProblemFact。
    #   Formalizer 的候选事实在 verifier 通过前只存在于临时输出中。
    status: Literal["verified", "invalid"] = "verified"


class Definition(BaseModel):
    # Runtime 分配的 ID，例如 D1、D2。
    id: str

    # 定义类型。
    #
    # variable:
    #   定义一个未知量，例如“令 x 为宽”。
    #
    # notation:
    #   定义一个符号或表达式，例如“记 S_n = ...”。
    #
    # object:
    #   定义集合、图、区域、序列等数学对象。
    #
    # auxiliary:
    #   为方便推理引入的辅助对象，例如辅助点、辅助函数。
    definition_type: Literal["variable", "notation", "object", "auxiliary"]

    # 定义本身。
    statement: str

    # 定义为什么被引入。
    #
    # 对 definition 而言，这不是“证明理由”，
    # 而是用途说明，例如“用于表示长方形的宽”。
    purpose: str = ""

    # 定义引用了哪些 ProblemFact / Definition。
    #
    # 例如：
    # “令 x 表示宽”通常不依赖其他对象，因此为空。
    # “记 y=x+2 表示长”可能依赖 D1 和 P2。
    depends_on: list[str] = Field(default_factory=list)

    # 定义状态。
    #
    # verified:
    #   定义合法、没有与题目或已有定义冲突，可以继续使用。
    #
    # invalid:
    #   后续发现定义存在符号冲突、对象偷换或不合法，应停止使用。
    #
    # 同样不保存 candidate 状态；
    # 候选定义在 Step/Formalization Verifier 通过前不进入 state.definitions。
    status: Literal["verified", "invalid"] = "verified"

    # 哪个 reasoning step 创建了它。
    source_step: int | None = None

    # 属于哪个解题分支。
    branch_id: str | None = None


class DerivedResult(BaseModel):
    # Runtime 分配 ID，例如 R1、R2。
    id: str

    # 推导结果类型。
    #
    # equation:
    #   等式或方程，例如 x(x+2)=48。
    #
    # inequality:
    #   不等式，例如 x>=3。
    #
    # identity:
    #   恒等关系。
    #
    # derived_fact:
    #   一般逻辑/代数/几何中间结论。
    #
    # case_result:
    #   某个分类讨论分支得到的结果。
    #
    # bound:
    #   上界、下界、估计。
    #
    # construction:
    #   一个显式构造已经成功建立。
    #
    # contradiction:
    #   反证过程中得到矛盾。
    #
    # completeness:
    #   “所有情况已覆盖”“没有其他解”等完整性结论。
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

    # 数学结论本身。
    statement: str

    # 当前结论的局部推导依据。
    #
    # 例如：
    # “由长方形面积公式结合 P1、P2、D1 得到”
    #
    # 注意：
    #   justification 不是 authoritative truth，
    #   它是 Solver 对推导依据的说明，
    #   Step Verifier 会检查这个说明是否真的成立。
    justification: str

    # 当前结论依赖的 authoritative ID。
    #
    # 可以引用：
    # P*  ProblemFact
    # D*  Definition
    # R*  已 VERIFIED 的 DerivedResult
    depends_on: list[str] = Field(default_factory=list)

    # Result 的状态。
    #
    # verified:
    #   Step Verifier 已经确认该结论成立，
    #   可以被后续 Solver 当作已知结果使用。
    #
    # invalid:
    #   曾经 verified，但后续 Audit / Rollback
    #   发现该结论或它的依赖链有问题。
    #
    # 这里故意没有 candidate：
    # Solver 刚提出的新结果只存在于 ReasoningStep.new_results，
    # 通过 verifier 后才创建 DerivedResult(status="verified")。
    status: Literal["verified", "invalid"] = "verified"

    # 产生该结果的 accepted step 编号。
    source_step: int | None = None

    # 所属分支。
    branch_id: str | None = None


class Task(BaseModel):
    # Runtime 分配 ID，例如 T1、T2。
    id: str

    # Task 是“下一步做什么”，不表示整题是否完成。
    kind: Literal[
        "formalize",
        "derive",
        "compute",
        "verify",
        "verify_candidate",
        "repair",
        "replan",
        "finalize",
        "case_analysis",
        "lower_bound",
        "upper_bound",
        "construction",
        "proof",
        "sanity_check",
        "completeness",
    ]

    # 当前任务目标。
    objective: str

    # 数值越大优先级越高。
    priority: int = 0

    # 必需任务会阻止严格收尾，直到完成或被显式替换为 invalid。
    required: bool = True

    # Task 生命周期。
    status: Literal["open", "active", "done", "invalid", "blocked"] = "open"

    # 依赖 Requirement / Evidence / Task ID。运行时只选择依赖已满足的任务。
    depends_on: list[str] = Field(default_factory=list)

    # 该任务主要服务哪些 CompletionRequirement。
    requirement_ids: list[str] = Field(default_factory=list)

    # 已尝试次数，用于触发 repair/replan。
    attempts: int = 0

    # 同一 Task 上累计的数学拒绝次数。
    math_rejects: int = 0

    # 同一 Task 上累计的协议/格式失败次数。
    protocol_failures: int = 0

    # 哪些 verified evidence 支持该任务被标记为 done。
    completed_by: list[str] = Field(default_factory=list)

    # 兼容 candidate verification 等任务的关联信息。
    candidate_id: str | None = None

    # 候选相关任务绑定到候选产生时的草稿版本，避免复用旧路线的检查结果。
    candidate_source_draft_version: int | None = None
    candidate_verification_record: str | None = None

    # 审计字段。
    created_by: str = "formalizer"
    invalidated_by: str | None = None
    blocked_reason: str = ""
    last_error_id: str | None = None


class CompletionRequirement(BaseModel):
    # Runtime 分配 ID，例如 REQ_answer。
    id: str

    # Requirement 是 final gate 的唯一完成标准。
    kind: Literal[
        "answer_candidate",
        "candidate_verified",
        "proof_complete",
        "lower_bound",
        "upper_bound",
        "construction_verified",
        "case_coverage",
        "completeness",
        "candidate_set_complete",
        "consistency",
    ]

    # 当前完成状态。
    status: Literal["unsatisfied", "satisfied", "conflict"] = "unsatisfied"

    # 哪些 verified evidence / verification record 支撑满足。
    satisfied_by: list[str] = Field(default_factory=list)

    # 哪些 invalid / conflict evidence 阻塞它。
    blocked_by: list[str] = Field(default_factory=list)

    # 给 planner/solver 的简短目标说明。
    description: str = ""


class ProgressAudit(BaseModel):
    id: str
    step_index: int
    verdict: Literal["progress", "no_progress", "conflict"]
    advanced_requirements: list[str] = Field(default_factory=list)
    repeated_evidence: list[str] = Field(default_factory=list)
    task_id: str | None = None
    reason: str = ""


class ReplanRecord(BaseModel):
    id: str
    trigger: Literal[
        "task_rejected_twice",
        "task_protocol_failure",
        "no_new_evidence",
        "no_executable_task",
        "requirements_stalled",
        "model_replan",
        "finalizer_failed",
        "manual",
    ]
    invalidated_tasks: list[str] = Field(default_factory=list)
    new_tasks: list[str] = Field(default_factory=list)
    reason: str = ""


class StrategyGuidance(BaseModel):
    # StrategyGuidance 只是 Prompt 层的路线建议，不是 authoritative math state。
    # 它不能作为 ProblemFact / Definition / DerivedResult / CandidateAnswer 使用。
    id: str

    # 策略生命周期。
    #
    # active:
    #   当前可注入 Solver prompt 的策略建议。
    #
    # stale:
    #   后续换路或重新规划后不再优先使用的旧策略。
    #
    # invalid:
    #   策略输出被发现包含不可靠答案泄露或明显错误路线。
    status: Literal["active", "stale", "invalid"] = "active"

    # 粗粒度题型判断，仅作提示，不覆盖 AgentState.problem_type。
    problem_type: str = "unknown"

    # 生成该策略时注入的领域技能手册。
    selected_skill_ids: list[str] = Field(default_factory=list)

    # 建议使用的核心变形、工具或观察方向。
    core_methods: list[str] = Field(default_factory=list)

    # 建议的阶段性路线。不是 Task，不参与 final gate。
    phase_plan: list[str] = Field(default_factory=list)

    # 风险控制：提醒 Solver 避免跳步、偷换定义、漏情况等。
    risk_controls: list[str] = Field(default_factory=list)

    # 明确禁止的做法。
    do_not: list[str] = Field(default_factory=list)

    # 对第一步的简短建议。只能是路线建议，不能是结论。
    first_step_instruction: str = ""

    # 清洗策略时产生的警告。
    sanitization_warnings: list[str] = Field(default_factory=list)


class SolutionDraftState(BaseModel):
    version: int = 0
    task_id: str | None = None
    text: str = ""
    status: Literal["empty", "proposed", "repairing", "accepted", "rejected"] = "empty"


class AcceptedClaim(BaseModel):
    id: str
    claim_type: Literal["definition", "result"]
    statement: str
    source_draft_version: int
    authoritative_id: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class CandidateAnswer(BaseModel):
    # Runtime 分配 ID，例如 C1、C2。
    id: str

    # 候选最终答案的规范化表示。
    value: str

    # Candidate 生命周期状态。
    #
    # candidate:
    #   Solver 已经提出该答案，
    #   但还没有经过独立 Candidate Verification。
    #
    # verified:
    #   已经独立检查该候选在其声明粒度上满足原题；
    #   多候选合并后的 completeness 由 CandidateSetVerification 单独检查。
    #
    # rejected:
    #   候选答案不满足原题、来自错误推导或被反例否定。
    #
    # conflict:
    #   当前候选本身仍有未解决歧义；不同的 verified 候选不必然冲突，
    #   它们可能共同组成多解答案。
    status: Literal["candidate", "verified", "rejected", "conflict"] = "candidate"

    # 哪些 VERIFIED Result 支持该候选答案。
    support_results: list[str] = Field(default_factory=list)

    # 来源 step。
    source_step: int | None = None

    # 候选产生时的求解路线快照，供后续独立验证对照。
    source_draft_version: int = 0
    source_solution_draft: str = ""
    source_strategy_methods: list[str] = Field(default_factory=list)

    # Candidate Verifier 的检查摘要。
    verification_reason: str = ""

    # 独立 Candidate Verification 记录 ID。
    verification_record: str | None = None


class BranchState(BaseModel):
    # Runtime 分配，例如 B1、B2。
    id: str

    # 路线的简短描述。
    idea: str

    # Branch 生命周期。
    status: Literal[
        "unexplored",
        "active",
        "blocked",
        "failed",
        "completed",
        "abandoned",
    ] = "unexplored"

    # 该分支本地连续失败次数。
    retry_count: int = 0

    # 该分支产生的 VERIFIED Result ID。
    local_result_ids: list[str] = Field(default_factory=list)

    # 最近一个被 verifier 接受的局部 step。
    # 只作为短期上下文，不是 authoritative truth 的替代品。
    last_accepted_step: dict | None = None


class ErrorRecord(BaseModel):
    # Runtime 分配 E1、E2，可选。
    id: str

    # 错误发生在哪条 branch。
    branch_id: str | None = None

    # 出错 step 的简短摘要。
    step_summary: str

    # 错误类别。
    category: Literal[
        "algebra_error",
        "definition_drift",
        "quantifier_error",
        "unsupported_claim",
        "dependency_error",
        "incomplete_case_analysis",
        "repeated_route",
        "candidate_failure",
        "other",
    ] = "other"

    # verifier 给出的失败原因。
    reason: str

    # 下一次若仍尝试相近路线，应明确修复什么。
    retry_instruction: str

    # 与错误相关的 P/D/R/C ID。
    related_ids: list[str] = Field(default_factory=list)


class CandidateVerificationRecord(BaseModel):
    id: str
    candidate_id: str
    verdict: Literal["accept", "reject", "conflict"]
    reason: str
    independent_method: str = ""
    falsification_attempt: str = ""
    method_type: str = ""
    checked_claims: list[str] = Field(default_factory=list)
    tested_cases: list[str] = Field(default_factory=list)
    route_difference: str = ""


class CandidateSetVerificationRecord(BaseModel):
    id: str
    verdict: Literal["accept", "incomplete", "reject"]
    assessed_candidate_ids: list[str] = Field(default_factory=list)
    verified_candidate_ids: list[str] = Field(default_factory=list)
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    complete_answer: str = ""
    missing_cases: list[str] = Field(default_factory=list)
    reason: str = ""
    repair_instruction: str = ""


class AgentState(BaseModel):
    # ------------------------------
    # 1. 原始输入
    # ------------------------------
    problem: str

    # 题型。
    problem_type: Literal[
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
        "probability",
        "stochastic_processes",
        "statistical_inference",
        "linear_regression",
        "linear_algebra",
        "abstract_algebra",
        "advanced_olympiad_mathematics",
        "numerical_analysis",
        "differential_geometry",
        "measure_theory",
        "complex_analysis",
        "ordinary_differential_equations",
        "functional_analysis",
        "partial_differential_equations",
        "operations_research",
        "mathematical_analysis",
        "topology",
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
    ] = "unknown"
    secondary_problem_types: list[str] = Field(default_factory=list)
    classification_confidence: float = 0.0
    classification_reason: str = ""
    selected_skill_ids: list[str] = Field(default_factory=list)

    # ------------------------------
    # 2. Runtime 当前阶段
    # ------------------------------
    phase: Literal[
        "analyze",
        "formalize",
        "plan",
        "solve",
        "verify",
        "critique",
        "repair",
        "audit",
        "candidate_verify",
        "candidate_set_verify",
        "finalize",
        "done",
        "incomplete",
    ] = "analyze"

    execution_mode: Literal["direct", "draft", "macro"] = "draft"
    solution_draft: SolutionDraftState = Field(default_factory=SolutionDraftState)
    accepted_claims: list[AcceptedClaim] = Field(default_factory=list)
    repair_count: int = 0
    model_replan_count: int = 0
    model_call_count: int = 0
    started_at: float = 0.0
    deadline_at: float = 0.0
    best_candidate_deadline_at: float = 0.0
    finalize_reserve_seconds: float = 120.0
    convergence_reserve_seconds: float = 360.0
    finalize_mode: Literal["strict", "best_effort"] = "strict"
    finalize_reason: str = ""
    efficient_runtime: bool = False
    solver_context_max_chars: int = 24000
    failed_route_fingerprints: list[str] = Field(default_factory=list)

    # ------------------------------
    # 3. Authoritative 数学状态
    # ------------------------------
    problem_facts: list[ProblemFact] = Field(default_factory=list)
    definitions: list[Definition] = Field(default_factory=list)
    derived_results: list[DerivedResult] = Field(default_factory=list)
    requirements: list[CompletionRequirement] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    candidates: list[CandidateAnswer] = Field(default_factory=list)

    # ------------------------------
    # 4. 路线与失败记忆
    # ------------------------------
    branches: list[BranchState] = Field(default_factory=list)
    active_branch_id: str | None = None
    error_memory: list[ErrorRecord] = Field(default_factory=list)
    candidate_verifications: list[CandidateVerificationRecord] = Field(default_factory=list)
    candidate_set_verifications: list[CandidateSetVerificationRecord] = Field(
        default_factory=list
    )
    progress_audits: list[ProgressAudit] = Field(default_factory=list)
    replan_records: list[ReplanRecord] = Field(default_factory=list)
    strategy_guidance: list[StrategyGuidance] = Field(default_factory=list)

    # ------------------------------
    # 5. 运行统计
    # ------------------------------
    accepted_step_count: int = 0
    solver_call_count: int = 0
    local_retry_count: int = 0
    stagnation_count: int = 0
    strategy_reset_count: int = 0

    # ------------------------------
    # 6. Budget
    # ------------------------------
    max_solver_calls: int = 20
    max_accepted_steps: int = 20
    max_local_retries: int = 2
    max_strategy_resets: int = 3
    max_repairs: int = 1
    max_model_replans: int = 2
