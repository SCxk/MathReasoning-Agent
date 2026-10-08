from dataclasses import dataclass, field
import os


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class AgentConfig:
    # custom2 高效流程默认开启；关闭后回退到旧的逐 ReasoningStep 状态机。
    custom2_efficient_runtime: bool = field(
        default_factory=lambda: env_flag("CUSTOM2_EFFICIENT_RUNTIME", True)
    )
    # 正式评测单题总时限为 20 分钟。Agent 只据此决定是否发起下一次调用。
    custom2_total_budget_seconds: float = 1200.0
    custom2_platform_deadline_headroom_seconds: float = 0.0
    # Once this much internal time remains, return the strongest saved draft
    # instead of spending the delivery window on another audit or arbitration.
    staged_best_candidate_return_seconds: float = 25.0
    staged_new_work_cutoff_seconds: float = 300.0
    custom2_finalize_reserve_seconds: float = 300.0
    custom2_convergence_reserve_seconds: float = 360.0
    # A failed audit may require several genuinely different derivations, but
    # keep the staged runtime bounded so repair loops cannot consume the whole
    # per-problem deadline.
    custom2_max_repairs: int = 3
    custom2_max_model_replans: int = 2
    custom2_max_solver_calls: int = 8
    custom2_solver_context_max_chars: int = 24000
    # custom2 Solver 的单次输出预算。JSON repair 也使用相同预算，避免长推理被截断。
    custom2_solver_max_tokens: int = 131072
    # strict 与 best-effort Finalizer 共用的单次输出预算。
    custom2_finalizer_max_tokens: int = 8192

    # 单题内最多真实调用模型的次数，防止 ReAct 循环失控。
    max_model_calls: int = 36
    # 是否在正式解题前先生成竞赛解题策略；该调用不计入 max_model_calls。
    enable_strategy_preprocess: bool = True
    # 单题内预处理策略生成调用次数上限，第一版固定最多一次。
    max_strategy_preprocess_calls: int = 2
    # 是否启用每个 solve_step 后的独立数学逻辑校验；不计入 max_model_calls。
    enable_step_logic_verifier: bool = True
    # 单题内最多调用 step verifier 的次数，和主解题模型调用预算分开统计。
    max_step_verify_calls: int = 16
    # verifier 明确拒绝后，最多让 generator 重做多少次，避免坏题目反复卡死。
    max_logic_retries: int = 6
    # 单题内最多保留多少条逻辑错误记忆，用于避免 generator/verifier 重复同类错误。
    max_error_memory_items: int = 12
    # 单题内最多执行工具的次数；工具失败也会计入调用预算。
    max_tool_calls: int = 16
    # 底层模型/工具交互循环的最大步数，作为总保险丝。
    max_loop_steps: int = 32
    # 单个候选最多允许模型拆成多少个 solve_step；用完后必须收敛到 final_answer。
    max_solve_steps: int = 32
    # debug_trace 和本地兜底 raw response 副本的最大保存字符数；不截断真实解析内容。
    max_trace_chars: int = 12000
    # 是否在最终返回中包含 debug_trace；当前默认开启，便于本地观察模型/工具交互。
    emit_debug_trace: bool = field(
        default_factory=lambda: env_flag("REASONING_AGENT_DEBUG_TRACE", True)
    )

    # 底层作答 loop 的采样温度，默认偏保守。
    tool_loop_temperature: float = 0.1
    # 解题策略预处理使用低温度，目标是稳定产出约束和风险提示。
    strategy_preprocess_temperature: float = 0.0
    # 逻辑校验器使用更低温度，优先稳定、保守地指出推理问题。
    step_verifier_temperature: float = 0.0
    # 默认关闭平台 client 的思考模式，以控制单题延迟。
    thinking_mode: bool = False
    # 底层作答 loop 的初始 max_tokens；失败重试时会按 max_token_retry 递减。
    tool_loop_max_tokens: int = 0
    # 单次 step verifier 的输出预算，只需要 verdict/reason/retry_instruction。
    step_verifier_max_tokens: int = 4096
    # 单次策略预处理输出预算；custom 与 custom2 均使用该配置。
    strategy_preprocess_max_tokens: int = 4096

    custom2_solver_protocol: str = field(
        default_factory=lambda: os.environ.get("CUSTOM2_SOLVER_PROTOCOL", "json").strip().lower()
    )
    custom2_text_thinking_mode: str = field(
        default_factory=lambda: os.environ.get("CUSTOM2_TEXT_THINKING_MODE", "false").strip().lower()
    )
    custom2_text_context_max_chars: int = 96000
    custom2_text_control_max_tokens: int = 8192
    custom2_text_extract_answer: bool = True
    custom2_text_budget_recovery: bool = field(
        default_factory=lambda: env_flag("CUSTOM2_TEXT_BUDGET_RECOVERY", True)
    )
    custom2_text_program_checks: bool = field(
        default_factory=lambda: env_flag("CUSTOM2_TEXT_PROGRAM_CHECKS", True)
    )
    custom2_text_check_max_steps: int = 20000
    custom2_text_check_timeout_seconds: float = 1.0
    custom2_text_max_tasks: int = 24
    custom2_text_task_max_tokens: int = 16384
    # staged runtime: each injected client request is capped at 12 minutes;
    # the last four minutes are reserved for emergency integration.
    staged_client_max_wait_seconds: float = 720.0
    # Reserve two minutes for final answer integration while allowing the
    # 10-minute primary solver and a six-minute compact recovery to coexist
    # inside the 20-minute per-problem envelope.
    staged_convergence_seconds: float = 1080.0
    # staged runtime 的各阶段独立控制思考模式和输出预算。
    staged_classifier_thinking_mode: bool = False
    staged_classifier_max_tokens: int = 8192
    staged_classifier_timeout_seconds: float = 180.0
    staged_strategy_thinking_mode: bool = False
    staged_strategy_max_tokens: int = 8192
    staged_strategy_timeout_seconds: float = 360.0
    staged_strategy_temperature: float = 0.3
    # 策略规划器先看按题面筛选的技能节选；完整/最终技能材料仍由其输出的章节选择决定。
    staged_strategy_skill_material_max_chars: int = 8000
    # 策略规划将检索到的方法卡转成当前题的可执行路线与证明义务。
    staged_strategy_model_enabled: bool = field(
        default_factory=lambda: env_flag("STAGED_STRATEGY_MODEL_ENABLED", False)
    )
    # staged runtime 的本地策略案例检索；资源不可用时无阻塞退回现有流程。
    staged_strategy_retrieval_enabled: bool = field(
        default_factory=lambda: env_flag("STAGED_STRATEGY_RETRIEVAL_ENABLED", True)
    )
    staged_strategy_retrieval_mode: str = field(
        default_factory=lambda: os.environ.get(
            "STAGED_STRATEGY_RETRIEVAL_MODE", "lexical"
        ).strip().lower()
    )
    staged_strategy_retrieval_top_k: int = 2
    staged_strategy_retrieval_max_tokens: int = 512
    staged_strategy_retrieval_timeout_seconds: float = 360.0
    staged_strategy_retrieval_pool_seconds: float = 360.0
    staged_strategy_retrieval_thinking_mode: bool = False
    staged_strategy_card_max_chars: int = 12000
    staged_strategy_trace_max_chars: int = 12000
    staged_solver_compact_by_default: bool = False
    # One runtime-owned switch for cost/latency-sensitive evaluation.  When
    # enabled, no full primary solver request is issued: all derivations use
    # the bounded compact solver path.  Disable only to restore the long-form
    # primary solver experiment.
    staged_compact_reasoning_only: bool = field(
        default_factory=lambda: env_flag("STAGED_COMPACT_REASONING_ONLY", True)
    )
    staged_solver_thinking_mode: bool = False
    staged_solver_repair_thinking_mode: bool = True
    staged_solver_max_tokens: int = 16384 + 8192
    # Complex staged problems get up to ten minutes for the primary solver;
    # the runtime still clamps this by the 20-minute per-problem deadline and
    # reserves time for recovery/finalization.
    staged_solver_timeout_seconds: float = 660.0
    staged_solver_repair_timeout_seconds: float = 300.0
    staged_solver_compressed_retry_enabled: bool = True
    staged_solver_compressed_thinking_mode: bool = True
    staged_primary_solver_temperature: float = 0.3
    staged_repair_solver_temperature: float = 0.8
    staged_solver_compressed_max_tokens: int = 131072
    # Primary compact-only solve gets a longer single request; audit-triggered
    # compact repairs keep the smaller recovery budget below.
    staged_primary_compact_timeout_seconds: float = 660.0
    staged_solver_compressed_call_estimate_seconds: float = 660.0
    staged_targeted_audit_thinking_mode: bool = False
    staged_targeted_audit_max_tokens: int = 16384
    # The first audit is a focused fault finder, not a second full solve.
    # Keep enough wall-clock budget for an audited compact re-derivation.
    staged_targeted_audit_timeout_seconds: float = 360.0
    # If an audit response cannot be parsed after local shape recovery, issue
    # one compact, no-thinking retry with the original response and rejection
    # reason so the auditor can regenerate a schema-compliant report.
    staged_audit_retry_max_tokens: int = 4096
    staged_audit_retry_timeout_seconds: float = 60.0
    # A separate low-temperature gate checks that the Solver did not relax or
    # reverse constraints while translating the problem into a mathematical model.
    staged_model_fidelity_enabled: bool = field(
        default_factory=lambda: env_flag("STAGED_MODEL_FIDELITY_ENABLED", True)
    )
    staged_model_fidelity_max_tokens: int = 4096
    # Fidelity checks reason over one Solver draft but do not need the full
    # Solver budget. The first attempt uses this half-size thinking ceiling.
    staged_model_fidelity_thinking_max_tokens: int = 65536
    staged_model_fidelity_timeout_seconds: float = 200.0
    staged_model_fidelity_thinking_mode: bool = False
    staged_constraint_ledger_max_chars: int = 12000
    # Emergency integration and candidate arbitration are time-bounded control
    # paths.  Keep them concise by default rather than spending their deadline
    # window on hidden reasoning.
    staged_emergency_thinking_mode: bool = False
    staged_emergency_max_tokens: int = 8192
    staged_emergency_timeout_seconds: float = 300.0
    staged_final_arbitrator_timeout_seconds: float = 600.0
    staged_trace_solution_max_chars: int = 12000

    # Action Graph runtime: 与 custom2_staged 完全独立的配置命名空间。
    action_total_budget_seconds: float = 1200.0
    action_finalizer_reserve_seconds: float = 150.0
    action_return_reserve_seconds: float = 30.0
    action_reflector_reserve_seconds: float = 60.0
    action_preprocess_pool_seconds: float = 240.0
    action_profile_pool_seconds: float = 120.0
    action_strategy_pool_seconds: float = 180.0
    action_strategy_retrieval_pool_seconds: float = 90.0
    action_planner_pool_seconds: float = 180.0
    action_executor_pool_seconds: float = 720.0
    action_reflector_pool_seconds: float = 210.0
    action_finalizer_pool_seconds: float = 120.0
    action_safety_pool_seconds: float = 115.0
    action_max_primary_nodes: int = 5
    action_max_node_attempts: int = 6
    action_max_branch_depth: int = 2
    action_max_children_per_branch: int = 3
    action_max_open_branches: int = 3
    action_max_repairs_per_node: int = 1
    action_max_repairs_total: int = 1
    action_max_rethinks: int = 1
    action_max_planner_protocol_repairs: int = 1
    action_max_network_recovery_calls: int = 1
    action_max_model_calls: int = 20
    action_max_program_checks: int = 8
    action_bootstrap_thinking_mode: bool = False
    action_bootstrap_max_tokens: int = 8192
    action_bootstrap_timeout_seconds: float = 120.0
    action_model_preprocess_thinking_mode: bool = False
    action_model_preprocess_max_tokens: int = 8192
    action_model_preprocess_timeout_seconds: float = 150.0
    action_profile_thinking_mode: bool = False
    action_profile_max_tokens: int = 8192
    action_profile_timeout_seconds: float = 90.0
    action_strategy_thinking_mode: bool = False
    action_strategy_max_tokens: int = 8192
    action_strategy_timeout_seconds: float = 120.0
    action_strategy_retrieval_enabled: bool = True
    action_strategy_retrieval_top_k: int = 2
    action_strategy_retrieval_max_tokens: int = 512
    action_strategy_retrieval_timeout_seconds: float = 60.0
    action_strategy_retrieval_thinking_mode: bool = False
    # Action Graph: 控制调用要求确定性；解题与重想动作保留受控探索。
    action_control_temperature: float = 0.0
    action_executor_temperature: float = 0.2
    action_rethink_temperature: float = 0.35
    action_branch_temperature: float = 0.3
    action_repair_temperature: float = 0.1
    action_emergency_temperature: float = 0.1
    action_strategy_card_max_chars: int = 12000
    action_planner_thinking_mode: bool = False
    action_planner_max_tokens: int = 8192
    action_planner_timeout_seconds: float = 120.0
    action_executor_thinking_mode: bool = False
    action_executor_max_tokens: int = 16384
    action_executor_timeout_seconds: float = 420.0
    action_compressed_thinking_mode: bool = False
    action_compressed_max_tokens: int = 8192
    action_compressed_timeout_seconds: float = 270.0
    action_reflector_thinking_mode: bool = False
    action_reflector_max_tokens: int = 8192
    action_reflector_timeout_seconds: float = 120.0
    action_finalizer_thinking_mode: bool = False
    action_finalizer_max_tokens: int = 8192
    action_finalizer_timeout_seconds: float = 150.0
    action_planner_context_max_chars: int = 24000
    action_executor_context_max_chars: int = 48000
    action_problem_view_max_chars: int = 24000
    action_accepted_memory_max_chars: int = 10000
    action_failure_memory_max_chars: int = 4000
    action_skill_material_max_chars: int = 12000
    action_trace_max_chars: int = 12000
    action_emit_debug_trace: bool = False
