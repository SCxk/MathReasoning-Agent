"""题面结构触发的专项解题要求。

这些规则只分析当前题文本，不产生答案或调用模型；Solver、修复和审查阶段
复用同一入口，避免不同节点各自维护关键词而发生漂移。
"""

from __future__ import annotations

import re


_ALL_SOLUTIONS_RE = re.compile(
    r"(?i)find\s+all|determine\s+all|all\s+possible|every\s+possible|"
    r"所有可能|全部(?:的)?(?:解|值|情况|可能)|求所有|找出所有|确定所有|哪些"
)
_EXTREMAL_RE = re.compile(
    r"(?i)最大|最小|最多|最少|至多|至少|最优|最短|最长|极值|"
    r"\b(?:maximum|minimum|maximal|minimal|largest|smallest|greatest|least|"
    r"at\s+most|at\s+least|optimal)\b"
)
_MOD_CODOMAIN_RE = re.compile(
    r"(?:\\rightarrow|\\to|→|->)\s*\\?(?:mathbb\s*\{?\s*F\s*\}?_\{?2\}?|F_?2\b|"
    r"GF\(2\)|\\?mathbb\s*\{?\s*Z\s*\}?\s*/\s*2)"
)
_FUNC_SUM_RE = re.compile(r"([a-zA-Z])\s*\([^()]{1,60}\)\s*\+\s*\1\s*\(")
_OPEN_BOUND_RE = re.compile(
    r"(?i)\bbetween\b[^,.;]{1,40}\band\b|strictly\s+(?:between|less|greater)|"
    r"开区间|严格(?:小于|大于|介于|单调)|(?<![\\])<(?!=)"
)
_ORDINAL_RANK_RE = re.compile(
    r"(?i)\b\d+\s*[$}\s]*(?:st|nd|rd|th)\b[^.\n]{0,40}"
    r"\b(?:largest|smallest|greatest|least|biggest|term|element|number|value)\b|"
    r"第\s*\$?\s*[0-9一二三四五六七八九十k]+\s*\$?\s*(?:大|小|个|项|位)"
)
_FEASIBILITY_RE = re.compile(
    r"(?i)\bis it possible\b|\bcan (?:we|you|one|it)\b|\bdoes there exist\b|"
    r"是否(?:可能|存在|能)|能否|可否"
)
_COUNT_ASK_RE = re.compile(
    r"(?i)\b(?:minimum|maximum|smallest|largest|fewest|greatest)\s+number\b|"
    r"\bhow many\b|最少(?:需要)?(?:多少|几)|最多(?:能|可以)?(?:多少|几)|需要多少|数量是多少"
)


def structure_instruction(problem: str) -> str:
    """Return the structure-specific prompt suffix used by staged reasoning."""
    text = str(problem or "")
    parts: list[str] = []
    if _MOD_CODOMAIN_RE.search(text) and _FUNC_SUM_RE.search(text):
        parts.append(
            "[值域聚合警告] 函数值域是 F_2/模 2 结构时，所求函数值之和必须在该结构中"
            "聚合；逐项值求出后按模 2（异或）相加，最终不能提交普通整数和。"
        )
    if _ALL_SOLUTIONS_RE.search(text):
        parts.append(
            "[全部解检查单] 题目要求所有解/值：必须证明每个解支的必要性、充分性和无遗漏，"
            "最终答案列出全部分支，不能只验证一个构造。"
        )
    extremal = bool(_EXTREMAL_RE.search(text))
    if extremal:
        parts.append(
            "[极值题对照检查] 必须同时给出匹配的上界或下界与达到界的合法构造；"
            "用小规模精确实例或结构不同的候选交叉检查，单一构造的自洽不构成最优性证明。"
        )
    if extremal and _OPEN_BOUND_RE.search(text):
        parts.append(
            "[端点可达性检查] 严格不等式/开区间的临界值不可默认取到；对候选临界值给出"
            "全部变量的具体构造并逐条代回每个严格不等式。若只能在端点取等，必须修正结论。"
        )
    if _ORDINAL_RANK_RE.search(text):
        parts.append(
            "[序号对齐检查] 问第 k 项/第 k 大或小对象时，先列出前 3 个具体对象，"
            "核对从 1 开始的序号与通项后再代入 k，防止差一。"
        )
    if _FEASIBILITY_RE.search(text) and _COUNT_ASK_RE.search(text):
        parts.append(
            "[可行性与数量检查] 先用构造、反例或不变量证明可行性/不可能性，再给出数量；"
            "不可能性必须排除同类小规模反例，并验证不变量对每种允许操作的贡献确实固定。"
        )
    return "\n".join(parts)
