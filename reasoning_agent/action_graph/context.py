from __future__ import annotations

from .config import ActionGraphConfig
from .models import ActionRuntimeState


def bounded_text(text: str, limit: int) -> tuple[str, bool]:
    text = str(text or "")
    if len(text) <= limit:
        return text, False
    # 不在明显的 LaTeX 定界符中间截断；退到最近换行，失败则保留前缀并标记。
    cut = text.rfind("\n", 0, limit)
    if cut < max(1, limit // 2):
        cut = limit
    return text[:cut].rstrip(), True


def source_packet(state: ActionRuntimeState, config: ActionGraphConfig, target_id: str) -> tuple[str, list[str]]:
    packet = state.problem_packet
    warnings: list[str] = []
    text = packet.compact_view if packet.compact_view_safe else packet.normalized_text
    view, was_cut = bounded_text(text, config.action_problem_view_max_chars)
    if was_cut:
        target = next((item for item in packet.subquestions if item.id == target_id), None)
        pieces = [target.text] if target else []
        pieces.extend(record.raw for record in packet.formulas)
        pieces.extend(item.value for item in packet.numbers)
        pieces.extend(item.text for item in packet.subquestions)
        safe_pieces = []
        used = 0
        for piece in pieces:
            if not piece or piece in safe_pieces or used + len(piece) > config.action_problem_view_max_chars:
                continue
            safe_pieces.append(piece)
            used += len(piece) + 1
        view = "\n".join(safe_pieces) or view
        warnings.append("context_truncated")
    return view, warnings


def build_memory(state: ActionRuntimeState, config: ActionGraphConfig) -> tuple[str, str, list[str]]:
    accepted = "\n".join(f"[{item.id}] {item.text}" for item in state.accepted_claims.values() if item.valid)
    rejected = "\n".join(f"[{item.action}/{item.target_id}] {item.reason}" for item in state.rejected_routes)
    accepted, a_cut = bounded_text(accepted, config.action_accepted_memory_max_chars)
    rejected, r_cut = bounded_text(rejected, config.action_failure_memory_max_chars)
    warnings = ["context_truncated"] if a_cut or r_cut else []
    return accepted, rejected, warnings
