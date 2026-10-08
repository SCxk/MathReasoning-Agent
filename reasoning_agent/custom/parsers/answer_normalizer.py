from __future__ import annotations

import ast
from dataclasses import dataclass
from difflib import SequenceMatcher
import math
import re
from typing import Any, Literal


QuestionMode = Literal[
    "choice",
    "judgment",
    "fill_blank",
    "computation",
    "proof",
    "other",
]

OBJECTIVE_MODES = {"choice", "judgment", "fill_blank"}
_UNUSABLE_MARKERS = (
    "无法确定",
    "无法判断",
    "不能确定",
    "不确定",
    "不知道",
    "未能形成",
    "没有可靠",
    "暂无答案",
    "待求",
    "待定",
    "unknown",
    "uncertain",
    "cannot determine",
    "thinking process",
    "we need to",
    "let's analyze",
    "[truncated]",
    "已截断",
)
_LABEL_RE = re.compile(
    r"^\s*(?:(?:最终答案|答案|结论|选择|answer|final\s+answer)\s*(?:为|是)?\s*[:：]?\s*)+",
    re.IGNORECASE,
)
_BOXED_DESCRIPTION_PREFIX_RE = re.compile(
    r"^(?:(?:thus|therefore|hence)\s*[,，:]?\s*)?"
    r"(?:(?:the\s+)?(?:final\s+)?(?:answer|result|function)\s*"
    r"(?:is|equals|=|:|：)\s*|"
    r"(?:最终答案|答案|结果|所求函数|函数表达式)\s*(?:为|是|=|:|：)\s*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AnswerMatchResult:
    matched: bool
    method: str
    preferred_answer: str
    reason: str = ""


def detect_question_mode(
    problem: str = "",
    problem_type: str | None = None,
) -> QuestionMode:
    """Infer output mode conservatively from the raw problem and coarse type."""

    source = str(problem or "")
    lowered_type = str(problem_type or "").strip().lower()
    option_labels = re.findall(
        r"(?:^|[\s\n])(?:[（(]?[A-EＡ-Ｅ][）).．、:：])",
        source,
        flags=re.MULTILINE,
    )
    if len(option_labels) >= 2 or "多项选择" in source or "单项选择" in source:
        return "choice"
    if re.search(r"判断题|判断(?:下列|以下).*?(?:正误|对错)|正确还是错误|是否正确", source):
        return "judgment"
    if re.search(r"填空题|填入空格|填在横线|_{3,}|＿{3,}|\(\s*\\quad\s*\)", source):
        return "fill_blank"
    if lowered_type == "proof" or re.search(r"证明|求证", source):
        return "proof"
    if lowered_type in {
        "numeric",
        "equation",
        "sequence",
        "extremum",
        "functional_equation",
        "number_theory",
        "数值分析",
    }:
        return "computation"
    if re.search(r"求(?:值|解|所有|最[大小]|范围)|计算|解方程", source):
        return "computation"
    return "other"


def normalize_objective_answer(answer: Any, mode: str) -> str:
    """Canonicalize an objective answer without attempting to solve it again."""

    text = _prepare_answer_text(answer)
    if mode == "choice":
        text = text.translate(str.maketrans("ＡＢＣＤＥａｂｃｄｅ", "ABCDEABCDE")).upper()
        letters = re.findall(r"(?<![A-Z])[A-E](?![A-Z])", text)
        if not letters:
            compact = re.sub(r"[\s,，、/\\;；和与及或]+", "", text)
            if compact and re.fullmatch(r"[A-E]+", compact):
                letters = list(compact)
        unique = list(dict.fromkeys(letters))
        return "、".join(unique)
    if mode == "judgment":
        compact = re.sub(r"\s+", "", text).lower()
        if re.search(r"不正确|不对|错误|false|×|✗|叉", compact):
            return "错误"
        if re.search(r"正确|对|true|√|✓", compact):
            return "正确"
        return ""
    if mode == "fill_blank":
        return text.strip(" \t\r\n。；;")
    return text


def objective_answer_is_usable(answer: Any, mode: str) -> bool:
    text = str(answer or "").strip()
    if not text or _contains_unusable_marker(text):
        return False
    if mode == "choice":
        return bool(re.fullmatch(r"[A-E](?:、[A-E])*", text))
    if mode == "judgment":
        return text in {"正确", "错误"}
    if mode == "fill_blank":
        if len(text) > 500 or len(text.splitlines()) > 3:
            return False
        return not re.match(
            r"^(?:分析|思路|推理|首先|我们需要|题目要求|thinking)\b",
            text,
            flags=re.IGNORECASE,
        )
    return False


def format_answer_for_output(answer: Any, mode: str = "other") -> str:
    """Perform conservative, deterministic cleanup immediately before delivery."""

    raw_text = sanitize_boxed_answer_text(answer).strip()
    text = _strip_code_fence(raw_text)
    text = _LABEL_RE.sub("", text).strip()
    boxed = _last_boxed_content(text)
    if boxed is not None and _is_only_boxed_answer(text):
        text = boxed.strip()
    if not text or _contains_unusable_marker(text):
        return ""
    if mode == "proof":
        return text.strip()

    literal = _humanize_python_literal(text)
    if literal is not None:
        text = literal
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if mode == "computation" and "\n" not in text and len(text) <= 160:
        canonical = _canonical_simple_expression(text)
        if canonical:
            return canonical
    return text


def sanitize_boxed_answer_text(answer: Any) -> str:
    """Remove prose wrappers accidentally placed inside ``\\boxed{...}``."""

    text = str(answer or "")
    chunks: list[str] = []
    cursor = 0
    while True:
        match = re.search(r"\\boxed\s*\{", text[cursor:])
        if match is None:
            chunks.append(text[cursor:])
            break
        start = cursor + match.start()
        opening = text.find("{", start)
        content, end = _balanced_group(text, opening)
        if content is None:
            chunks.append(text[cursor:])
            break
        cleaned = _clean_boxed_content(content)
        changed = cleaned != content
        chunks.append(text[cursor:start])
        chunks.append(f"\\boxed{{{cleaned}}}")
        cursor = end
        if changed and cursor < len(text) and text[cursor] in {'"', "'", "”", "’"}:
            cursor += 1
    return "".join(chunks)


def _clean_boxed_content(content: str) -> str:
    cleaned = content.strip()
    cleaned = re.sub(
        r"^\\text\{\s*(?:(?:thus|therefore|hence)\s*[,，:]?\s*)?"
        r"(?:(?:the\s+)?(?:final\s+)?(?:answer|result|function)\s*"
        r"(?:is|equals|=|:|：)|(?:最终答案|答案|结果|所求函数)\s*(?:为|是|=|:|：))"
        r"\s*\}\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = _BOXED_DESCRIPTION_PREFIX_RE.sub("", cleaned).strip()
    return cleaned.strip('"\'“”‘’ ')


class AnswerMatcher:
    """Compare computation answers by structure, value and symbolic equivalence."""

    def match_answers(self, reasoning_answer: Any, reference_answer: Any) -> bool:
        return self._match_computation_detailed(
            reasoning_answer, reference_answer
        ).matched

    def _match_computation_detailed(
        self,
        reasoning_answer: Any,
        reference_answer: Any,
    ) -> AnswerMatchResult:
        left = _prepare_answer_text(reasoning_answer)
        right = _prepare_answer_text(reference_answer)
        preferred = left or right
        if not _computation_answer_is_usable(left) or not _computation_answer_is_usable(right):
            return AnswerMatchResult(False, "unusable", preferred, "答案为空或含占位内容")

        structured_left = _parse_structured_answer(left)
        structured_right = _parse_structured_answer(right)
        if structured_left is not None and structured_right is not None:
            if structured_left.keys() != structured_right.keys():
                return AnswerMatchResult(False, "structured", preferred, "字段集合不同")
            for key in structured_left:
                result = self._match_scalar(structured_left[key], structured_right[key])
                if not result.matched:
                    return AnswerMatchResult(False, "structured", preferred, f"字段 {key} 不等价")
            return AnswerMatchResult(True, "structured", preferred)

        return self._match_scalar(left, right)

    def _match_scalar(self, left: str, right: str) -> AnswerMatchResult:
        preferred = left or right
        normalized_left = _comparison_text(left)
        normalized_right = _comparison_text(right)
        if normalized_left == normalized_right:
            return AnswerMatchResult(True, "exact", preferred)

        left_float = _to_float(normalized_left)
        right_float = _to_float(normalized_right)
        if left_float is not None and right_float is not None:
            matched = math.isclose(left_float, right_float, rel_tol=1e-9, abs_tol=1e-10)
            return AnswerMatchResult(matched, "numeric", preferred)

        symbolic = _symbolic_equivalent(normalized_left, normalized_right)
        if symbolic is not None:
            return AnswerMatchResult(symbolic, "symbolic", preferred)

        similarity = SequenceMatcher(None, normalized_left, normalized_right).ratio()
        return AnswerMatchResult(
            similarity >= 0.96,
            "string_similarity",
            preferred,
            f"similarity={similarity:.3f}",
        )


def _prepare_answer_text(answer: Any) -> str:
    text = _strip_code_fence(str(answer or "").strip())
    text = _LABEL_RE.sub("", text).strip()
    boxed = _last_boxed_content(text)
    if boxed is not None:
        text = boxed.strip()
    text = re.split(
        r"[；;]\s*(?:依据|理由|解释|说明|因为|所以|故)\s*[:：]",
        text,
        maxsplit=1,
    )[0]
    return text.strip()


def _strip_code_fence(text: str) -> str:
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return text


def _last_boxed_content(text: str) -> str | None:
    starts = list(re.finditer(r"\\boxed\s*\{", text))
    for match in reversed(starts):
        opening = text.find("{", match.start())
        depth = 0
        for index in range(opening, len(text)):
            if text[index] == "{" and (index == 0 or text[index - 1] != "\\"):
                depth += 1
            elif text[index] == "}" and (index == 0 or text[index - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    return text[opening + 1 : index]
    return None


def _is_only_boxed_answer(text: str) -> bool:
    """Return true only when boxed content is the whole answer, apart from punctuation."""

    match = re.fullmatch(r"\s*\\boxed\s*\{.*\}\s*[。.!！]?\s*", text, re.DOTALL)
    return match is not None


def _contains_unusable_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _UNUSABLE_MARKERS)


def _computation_answer_is_usable(text: str) -> bool:
    return bool(text.strip()) and not _contains_unusable_marker(text)


def _parse_structured_answer(text: str) -> dict[str, str] | None:
    parts = [part.strip() for part in re.split(r"[;；\n]+", text) if part.strip()]
    if not parts or not all("=" in part for part in parts):
        return None
    result: dict[str, str] = {}
    for part in parts:
        key, value = part.split("=", 1)
        key = re.sub(r"\s+", "", key)
        if not key or not value.strip() or key in result:
            return None
        result[key] = value.strip()
    return result


def _comparison_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().strip("。；;"))


def _to_float(text: str) -> float | None:
    try:
        value = float(text)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _normalize_math_syntax(text: str) -> str:
    value = text.strip().strip("$ ")
    value = value.replace("\\left", "").replace("\\right", "")
    value = value.replace("\\pi", "pi").replace("π", "pi")
    value = value.replace("×", "*").replace("·", "*").replace("⋅", "*")
    value = value.replace("÷", "/").replace("^", "**")
    value = _replace_latex_command(value, "frac", lambda a, b: f"(({a})/({b}))")
    value = _replace_latex_command(value, "sqrt", lambda a: f"sqrt({a})")
    value = re.sub(r"√\s*\(([^()]*)\)", r"sqrt(\1)", value)
    value = re.sub(r"√\s*([A-Za-z0-9.]+)", r"sqrt(\1)", value)
    value = _replace_latex_matrix(value)
    value = re.sub(r"(?<=\d)(?=(?:pi|sqrt\(|[A-Za-z]))", "*", value)
    value = re.sub(r"(?<=\))(?=(?:pi|sqrt\(|[A-Za-z0-9]))", "*", value)
    value = re.sub(r"(?<=pi)(?=(?:sqrt\(|[A-Za-z0-9(]))", "*", value)
    return value


def _replace_latex_command(text: str, command: str, builder: Any) -> str:
    token = f"\\{command}"
    while token in text:
        start = text.rfind(token)
        cursor = start + len(token)
        groups: list[str] = []
        required = 2 if command == "frac" else 1
        valid = True
        for _ in range(required):
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            if cursor >= len(text) or text[cursor] != "{":
                valid = False
                break
            group, cursor = _balanced_group(text, cursor)
            if group is None:
                valid = False
                break
            groups.append(group)
        if not valid:
            break
        text = text[:start] + builder(*groups) + text[cursor:]
    return text


def _balanced_group(text: str, opening: int) -> tuple[str | None, int]:
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index], index + 1
    return None, opening


def _replace_latex_matrix(text: str) -> str:
    pattern = re.compile(
        r"\\begin\{(?:p|b|v|V)?matrix\}(.*?)\\end\{(?:p|b|v|V)?matrix\}",
        re.DOTALL,
    )

    def convert(match: re.Match[str]) -> str:
        rows = []
        for row in re.split(r"\\\\", match.group(1)):
            entries = [entry.strip() for entry in row.split("&")]
            rows.append("[" + ",".join(entries) + "]")
        return "Matrix([" + ",".join(rows) + "])"

    return pattern.sub(convert, text)


def _symbolic_equivalent(left: str, right: str) -> bool | None:
    try:
        import sympy

        left_expr = sympy.sympify(_normalize_math_syntax(left), evaluate=True)
        right_expr = sympy.sympify(_normalize_math_syntax(right), evaluate=True)
        difference = sympy.simplify(left_expr - right_expr)
        if difference == 0:
            return True
        symbols = sorted(left_expr.free_symbols | right_expr.free_symbols, key=str)
        if not symbols:
            return bool(difference == 0)
        successful = 0
        for seed in (2, 3, 5, 7, 11):
            substitutions = {
                symbol: sympy.Rational(seed + index, index + 1)
                for index, symbol in enumerate(symbols)
            }
            try:
                numeric = complex(sympy.N(difference.subs(substitutions), 30))
            except Exception:  # noqa: BLE001 - invalid sample points are skipped.
                continue
            if not (math.isfinite(numeric.real) and math.isfinite(numeric.imag)):
                continue
            successful += 1
            if abs(numeric) > 1e-9:
                return False
        return True if successful >= 3 else None
    except Exception:  # noqa: BLE001 - symbolic parsing is an optional match path.
        return None


def _canonical_simple_expression(text: str) -> str:
    if "=" in text or re.search(r"[。！？!?：:]", text):
        return ""
    try:
        import sympy

        expression = sympy.sympify(_normalize_math_syntax(text), evaluate=True)
        if expression.free_symbols and len(expression.free_symbols) > 8:
            return ""
        return str(sympy.simplify(expression))
    except Exception:  # noqa: BLE001 - retain the original when parsing is unsafe.
        return ""


def _humanize_python_literal(text: str) -> str | None:
    if not text.startswith(("[", "(", "{")):
        return None
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None
    if isinstance(value, dict):
        return "；".join(f"{key}={item}" for key, item in value.items())
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    return None
