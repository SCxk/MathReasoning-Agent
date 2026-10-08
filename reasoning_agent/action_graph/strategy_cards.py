"""Bounded strategy-example cards for Action Graph prompts and trace."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategyCardBundle:
    planner: str
    executor: str
    planner_truncated: bool = False
    executor_truncated: bool = False


def build_strategy_cards(results: list[dict[str, Any]], *, max_chars: int) -> StrategyCardBundle:
    """Render ranked result cards, dropping whole low-ranked cards on overflow."""
    planner_cards: list[str] = []
    executor_cards: list[str] = []
    planner_size = executor_size = 0
    planner_truncated = executor_truncated = False
    for rank, result in enumerate(results, 1):
        summary = _card(result, rank, include_example=False)
        full = _card(result, rank, include_example=True)
        if planner_size + len(summary) <= max_chars:
            planner_cards.append(summary)
            planner_size += len(summary)
        else:
            planner_truncated = True
        if executor_size + len(full) <= max_chars:
            executor_cards.append(full)
            executor_size += len(full)
        else:
            executor_truncated = True
    return StrategyCardBundle(
        planner="\n\n".join(planner_cards),
        executor="\n\n".join(executor_cards),
        planner_truncated=planner_truncated,
        executor_truncated=executor_truncated,
    )


def trace_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return stable score metadata without serializing an embedding or example twice."""
    return [
        {
            "rank": rank,
            "id": item.get("id"),
            "name": str(item.get("name", "")),
            "score": _number(item.get("score")),
            "raw_score": _number(item.get("raw_score")),
            "structure_score": _number(item.get("structure_score")),
        }
        for rank, item in enumerate(results, 1)
    ]


def bound_card_text(text: str, max_chars: int) -> tuple[str, bool]:
    """Keep complete cards only, so trace never silently cuts an example."""
    if len(text) <= max_chars:
        return text, False
    cards = [card for card in text.split("\n\n") if card]
    kept: list[str] = []
    used = 0
    for card in cards:
        separator = 2 if kept else 0
        if used + separator + len(card) > max_chars:
            break
        kept.append(card)
        used += separator + len(card)
    return "\n\n".join(kept), True


def _card(item: dict[str, Any], rank: int, *, include_example: bool) -> str:
    lines = [
        f"【策略 {rank}：{item.get('name', 'unknown')}】",
        "该案例仅作方法参考；必须核验其适用条件并独立推出当前题结论。",
        f"标签：{_joined(item.get('tags'))}",
        f"描述：{item.get('description', '')}",
        f"适用条件：{_joined(item.get('applicability'))}",
        "步骤：" + _steps(item.get("steps")),
    ]
    if include_example:
        example = item.get("example") if isinstance(item.get("example"), dict) else {}
        lines.extend([
            "【参考例题】",
            str(example.get("problem", "")),
            "【参考解法】",
            str(example.get("solution", "")),
        ])
    return "\n".join(lines)


def _joined(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    return str(value or "")


def _steps(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    return "；".join(
        f"{item.get('step', '')}：{item.get('detail', '')}" if isinstance(item, dict) else str(item)
        for item in value
    )


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
