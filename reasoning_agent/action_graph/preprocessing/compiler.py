from __future__ import annotations

import re

from ..models import ExtractedItem, FormulaRecord, ProblemPacket, SourceSpan, Subquestion


_UNICODE_REPLACEMENTS = {
    "≤": r"\\le", "≥": r"\\ge", "≠": r"\\ne", "∈": r"\\in",
    "∉": r"\\notin", "∑": r"\\sum", "∏": r"\\prod", "∞": r"\\infty",
}
_SUBQUESTION = re.compile(r"(?:^|\n)\s*(?:[-*+]\s+|\([0-9一二三四五六七八九十]+\)|\(?[0-9一二三四五六七八九十]+\)?[\.、]|\([a-zA-Z]\)|\(?[a-zA-Z]\)?[\.、])\s*")
_FORMULA = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$|\\\[.*?\\\]|\\\(.*?\\\)", re.S)
_NUMBER = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?(?:/\d+)?")
_DOMAIN = re.compile(r"(?:整数|正整数|非负整数|有理数|实数|复数|整数集|自然数|[A-Za-z][A-Za-z0-9_]*\s*∈\s*[A-Za-zℤℚℝℂ]+)")
_VARIABLE = re.compile(r"(?<![A-Za-z])[A-Za-z](?:_[0-9]+)?(?![A-Za-z])")
_TARGET = re.compile(r"(?:求(?:证|值|出|所有)?|证明|计算|Determine|Find|Compute|Prove)[^。；;\n]*", re.I)


def normalize_text(raw: str) -> tuple[str, list[int]]:
    """机械规范化并保存每个 normalized 字符对应的 raw 偏移。"""
    chars: list[str] = []
    mapping: list[int] = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == "\r":
            if index + 1 < len(raw) and raw[index + 1] == "\n":
                index += 1
            chars.append("\n")
            mapping.append(index)
        elif char in _UNICODE_REPLACEMENTS:
            replacement = _UNICODE_REPLACEMENTS[char]
            chars.extend(replacement)
            mapping.extend([index] * len(replacement))
        else:
            chars.append(char)
            mapping.append(index)
        index += 1
    return "".join(chars), mapping


def _span(raw: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(start=max(0, start), end=min(len(raw), end), text=raw[max(0, start):min(len(raw), end)])


def _balanced_latex(text: str) -> bool:
    depth = 0
    escaped = False
    for char in text:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _subquestions(raw: str) -> list[Subquestion]:
    matches = list(_SUBQUESTION.finditer(raw))
    if not matches:
        return [Subquestion("q1", raw.strip(), _span(raw, 0, len(raw)))]
    result: list[Subquestion] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        text = raw[start:end].strip()
        result.append(Subquestion(f"q{index + 1}", text, _span(raw, start, end)))
    prefix = raw[:matches[0].start()].strip()
    if prefix:
        # 题目共同条件保留在每个子问题的原文区间外，compact view 会单独保存。
        result[0] = Subquestion("q1", prefix + "\n" + result[0].text, _span(raw, 0, result[0].span.end))
    return result


def _compact(raw: str, normalized: str, formulas: list[FormulaRecord], numbers: list[ExtractedItem], subs: list[Subquestion]) -> tuple[str, bool]:
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    candidate = "\n".join(lines)
    required = [item.value for item in numbers] + [item.normalized for item in formulas]
    # 仅在字面对象完整保留时允许使用 compact view。
    safe = all(item in candidate for item in required) and all(sub.text.strip() for sub in subs)
    return (candidate if safe else normalized), safe


def _complexity(raw: str, subs: list[Subquestion]) -> tuple[str, list[str]]:
    signals = []
    low_terms = ("计算", "求值", "evaluate", "calculate")
    high_terms = ("证明", "所有", "分类", "构造", "存在", "for all", "prove")
    lowered = raw.casefold()
    if len(subs) > 1:
        signals.append("multiple_subquestions")
    if any(term.casefold() in lowered for term in high_terms):
        signals.append("proof_or_case_structure")
    if len(raw) > 4000 or len(signals) >= 2:
        return "high", signals
    if len(subs) == 1 and any(term.casefold() in lowered for term in low_terms) and len(raw) < 800:
        return "low", signals + ["short_calculation"]
    return "medium", signals


def preprocess_problem(problem: str) -> ProblemPacket:
    raw = str(problem or "")
    normalized, mapping = normalize_text(raw)
    warnings: list[str] = []
    formulas: list[FormulaRecord] = []
    for match in _FORMULA.finditer(raw):
        formula = match.group(0)
        balanced = _balanced_latex(formula)
        if not balanced:
            warnings.append("unbalanced_latex")
        formulas.append(FormulaRecord(formula, formula, _span(raw, match.start(), match.end()), balanced))
    numbers = [ExtractedItem("number", match.group(0), _span(raw, match.start(), match.end())) for match in _NUMBER.finditer(raw)]
    domains = [ExtractedItem("domain", match.group(0), _span(raw, match.start(), match.end())) for match in _DOMAIN.finditer(raw)]
    variables = [ExtractedItem("variable", match.group(0), _span(raw, match.start(), match.end()), "syntax", 0.6) for match in _VARIABLE.finditer(raw)]
    targets = [ExtractedItem("target", match.group(0), _span(raw, match.start(), match.end()), "target_regex", 0.8) for match in _TARGET.finditer(raw)]
    subs = _subquestions(raw)
    # 条件抽取保持保守：以句子/分号为单位，避免自由语义改写。
    conditions = [
        ExtractedItem("condition", match.group(0), _span(raw, match.start(), match.end()), "sentence", 0.7)
        for match in re.finditer(r"[^。；;\n]+(?:[。；;]|$)", raw)
        if any(token in match.group(0) for token in ("若", "设", "满足", "其中", "given", "let"))
    ]
    compact, compact_safe = _compact(raw, normalized, formulas, numbers, subs)
    complexity, signals = _complexity(raw, subs)
    known = "\n".join(item.value for item in conditions)
    needed = "\n".join(item.value for item in targets) or "\n".join(item.text for item in subs)
    requirements_view = f"已知：\n{known}\n需要：\n{needed}".strip()
    return ProblemPacket(
        raw, normalized, mapping, subs, formulas, numbers, conditions, domains,
        variables, targets, requirements_view, compact, compact_safe, complexity, signals, warnings,
    )
