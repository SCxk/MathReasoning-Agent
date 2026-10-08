from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionSpec:
    name: str
    description: str
    branches: bool = False


ACTION_REGISTRY: dict[str, ActionSpec] = {
    "analyze": ActionSpec("analyze", "澄清对象、目标和等价模型"),
    "associate": ActionSpec("associate", "选择适用定理、公式或表示"),
    "derive": ActionSpec("derive", "推导一个指定的中间结论或计算"),
    "prove_bound": ActionSpec("prove_bound", "证明上界或下界并处理达到条件"),
    "construct": ActionSpec("construct", "构造对象并逐项验证"),
    "classify": ActionSpec("classify", "建立有限、互斥且覆盖的分类", True),
    "induct": ActionSpec("induct", "建立基例与归纳步骤", True),
    "negate": ActionSpec("negate", "通过反设导出矛盾", True),
    "test_claim": ActionSpec("test_claim", "代回、边界、反例或程序检验指定命题"),
    "rethink": ActionSpec("rethink", "依据失败原因切换表示或路线"),
    "finish": ActionSpec("finish", "声明证据足以收束"),
}

# 只有真正完成推导、构造或验证的动作，才允许产出可供 Finalizer
# 使用的 AnswerCandidate。分析、选法和分支动作只能提交 AcceptedClaim。
ANSWER_PRODUCING_ACTIONS = frozenset({
    "derive", "prove_bound", "construct", "test_claim",
})


def filter_available_actions(*, depth: int, remaining_seconds: float, rejected: set[tuple[str, str]], target_id: str, max_depth: int) -> list[ActionSpec]:
    result = []
    for spec in ACTION_REGISTRY.values():
        if spec.branches and depth >= max_depth:
            continue
        if (spec.name, target_id) in rejected:
            continue
        if remaining_seconds <= 0 and spec.name != "finish":
            continue
        result.append(spec)
    return result
