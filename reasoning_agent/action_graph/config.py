from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionGraphConfig:
    """Action Graph 独有配置；所有时长最终受 1200 秒硬上限约束。"""

    action_total_budget_seconds: float = 1200.0
    action_finalizer_reserve_seconds: float = 150.0
    action_return_reserve_seconds: float = 30.0
    action_reflector_reserve_seconds: float = 60.0
    action_preprocess_pool_seconds: float = 240.0
    action_profile_pool_seconds: float = 120.0
    action_strategy_pool_seconds: float = 420.0
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
    action_bootstrap_timeout_seconds: float = 90.0
    action_model_preprocess_thinking_mode: bool = False
    action_model_preprocess_max_tokens: int = 8192
    action_model_preprocess_timeout_seconds: float = 150.0
    action_profile_thinking_mode: bool = False
    action_profile_max_tokens: int = 8192
    action_profile_timeout_seconds: float = 90.0
    action_strategy_thinking_mode: bool = False
    action_strategy_max_tokens: int = 8192
    action_strategy_timeout_seconds: float = 420.0
    action_strategy_retrieval_enabled: bool = True
    action_strategy_retrieval_top_k: int = 2
    action_strategy_retrieval_max_tokens: int = 512
    action_strategy_retrieval_timeout_seconds: float = 60.0
    action_strategy_retrieval_thinking_mode: bool = False
    # 控制节点必须稳定地遵守 JSON/分类协议；求解动作才保留有限探索性。
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
    action_executor_timeout_seconds: float = 600.0
    action_compressed_thinking_mode: bool = False
    action_compressed_max_tokens: int = 8192
    action_compressed_timeout_seconds: float = 420.0
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

    @classmethod
    def from_object(cls, value: object | None) -> "ActionGraphConfig":
        if isinstance(value, cls):
            return value
        values = {
            name: getattr(value, name, default.default)
            for name, default in cls.__dataclass_fields__.items()
        }
        return cls(**values)
