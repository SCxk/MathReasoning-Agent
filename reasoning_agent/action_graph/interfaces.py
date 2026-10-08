"""动作图内部工具边界，便于在不调用模型时单独测试。"""
from __future__ import annotations

from typing import Any

from .action_registry import filter_available_actions
from .config import ActionGraphConfig
from .context import build_memory
from .models import ActionRuntimeState
from .tools import parse_branches, parse_decision, parse_reflection


def select_action(text: str, default_target: str):
    return parse_decision(text, default_target)


def check_node(text: str) -> dict[str, Any]:
    return parse_reflection(text)


def spawn_branches(text: str) -> list[dict[str, str]]:
    return parse_branches(text)


def load_node_memory(state: ActionRuntimeState, config: ActionGraphConfig) -> tuple[str, str, list[str]]:
    return build_memory(state, config)


def summarize_node(state: ActionRuntimeState) -> dict[str, Any]:
    """仅基于已审核 claim 更新覆盖与候选状态，绝不审核草稿。"""
    state.refresh_candidates()
    for candidate in state.supported_candidates():
        for target in candidate.covered_subquestion_ids:
            state.subquestion_status[target] = "covered"
    return {
        "covered": [key for key, value in state.subquestion_status.items() if value == "covered"],
        "remaining": [key for key, value in state.subquestion_status.items() if value != "covered"],
        "supported_candidates": [item.id for item in state.supported_candidates()],
    }


def available_actions(state: ActionRuntimeState, config: ActionGraphConfig, target_id: str, depth: int = 0):
    rejected = {(item.action, item.target_id) for item in state.rejected_routes}
    return filter_available_actions(depth=depth, remaining_seconds=state.budget.remaining(), rejected=rejected, target_id=target_id, max_depth=config.action_max_branch_depth)
