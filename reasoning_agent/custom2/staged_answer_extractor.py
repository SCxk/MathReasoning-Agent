from __future__ import annotations

from dataclasses import dataclass
import re

from reasoning_agent.custom.parsers.answer_normalizer import normalize_objective_answer


_SECTION_RE = re.compile(
    r"^\s*##\s*最终答案\s*$([\s\S]*?)(?=^\s*##\s+|\Z)",
    re.MULTILINE,
)
_PLACEHOLDERS = (
    "见上文", "见上", "同上", "无法确定", "无法判断", "不确定", "待定",
    "unknown", "uncertain", "incomplete", "cannot determine", "未能提取",
)


@dataclass(frozen=True)
class StagedAnswerExtraction:
    answer: str | None
    reason: str


def extract_staged_answer(response: str) -> StagedAnswerExtraction:
    """Extract an answer from a staged response without solving the problem.

    Models occasionally return a useful answer before completing all four
    presentation sections (especially when a request is close to its wall
    clock limit).  The fixed ``## 最终答案`` section remains the preferred
    source, but a final boxed expression or an explicit answer line is a safe
    best-effort fallback.  Losing an already generated answer is worse than
    returning it with an incomplete-solution trace.
    """

    text = str(response or "").replace("\r\n", "\n").replace("\r", "\n")
    match = _SECTION_RE.search(text)
    if not match:
        fallback = _extract_unsectioned_answer(text)
        if fallback is not None:
            return StagedAnswerExtraction(fallback, "unsectioned_answer")
        return StagedAnswerExtraction(None, "missing_final_answer_section")
    section = match.group(1).strip()
    if not section:
        return StagedAnswerExtraction(None, "empty_final_answer_section")
    if _has_placeholder(section):
        return StagedAnswerExtraction(None, "placeholder_final_answer")
    if not _balanced_latex(section):
        return StagedAnswerExtraction(None, "malformed_latex")

    boxed = _boxed_fragments(section)
    if boxed:
        answer = _clean_lines("\n".join(boxed))
    else:
        answer = _clean_lines(section)
        answer = _strip_answer_label(answer)
        if not answer or _has_placeholder(answer):
            return StagedAnswerExtraction(None, "unusable_final_answer")
        answer = f"\\boxed{{{answer}}}"
    if not answer or _has_placeholder(answer) or not _balanced_latex(answer):
        return StagedAnswerExtraction(None, "unusable_or_malformed_answer")
    return StagedAnswerExtraction(answer, "ok")


def render_staged_response(response: str, answer_mode: str = "other") -> str:
    """Render the durable staged draft according to the question's answer type.

    Objective questions need a compact, machine-comparable answer.  Proof
    questions are different: returning only the boxed conclusion would erase
    the argument that makes the answer valid, so the complete proof draft is
    retained (apart from internal executable-check blocks).
    """
    text = str(response or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if answer_mode == "proof":
        proof = re.sub(r"```check[ \t]*\n[\s\S]*?```", "", text, flags=re.I)
        return proof.strip() or "无法确定唯一答案"

    extraction = extract_staged_answer(text)
    if extraction.answer is None:
        return "无法确定唯一答案"
    answer = extraction.answer
    if answer_mode in {"choice", "judgment", "fill_blank"}:
        value = _objective_value(answer, answer_mode)
        if value:
            return f"\\boxed{{{value}}}"
    return answer


def _objective_value(answer: str, answer_mode: str) -> str:
    fragments = _boxed_fragments(answer)
    contents = [_boxed_content(fragment) for fragment in fragments]
    raw = "\n".join(contents) if contents else answer
    if answer_mode == "choice":
        translated = raw.translate(str.maketrans("ＡＢＣＤＥａｂｃｄｅ", "ABCDEABCDE"))
        letters = re.findall(r"(?<![A-Z])[A-E](?![A-Z])", translated.upper())
        if not letters:
            letters = re.findall(r"[A-E]", translated.upper())
        return "".join(dict.fromkeys(letters))
    return normalize_objective_answer(raw, answer_mode).strip()


def _boxed_content(fragment: str) -> str:
    opening = fragment.find("{")
    end = _balanced_group_end(fragment, opening) if opening >= 0 else None
    return fragment[opening + 1:end - 1] if opening >= 0 and end else fragment


def _extract_unsectioned_answer(text: str) -> str | None:
    """Recover a plainly formatted answer from a truncated model response."""

    boxed = _boxed_fragments(text)
    if boxed:
        candidate = _clean_lines(boxed[-1])
        if candidate and not _has_placeholder(candidate) and _balanced_latex(candidate):
            return candidate

    # Keep this deliberately narrow: only lines explicitly labelled as an
    # answer are eligible, so intermediate equations are not mistaken for the
    # final result.
    labelled = re.findall(
        r"(?im)^\s*(?:最终答案|答案|结论|final answer|answer)\s*(?:为|是|:|：)?\s*(.+?)\s*$",
        text,
    )
    for value in reversed(labelled):
        candidate = _clean_lines(_strip_answer_label(value))
        if candidate and not _has_placeholder(candidate) and _balanced_latex(candidate):
            return f"\\boxed{{{candidate}}}"
    return None


def _boxed_fragments(text: str) -> list[str]:
    fragments: list[str] = []
    cursor = 0
    while True:
        match = re.search(r"\\boxed\s*\{", text[cursor:])
        if not match:
            break
        start = cursor + match.start()
        opening = text.find("{", start)
        end = _balanced_group_end(text, opening)
        if end is None:
            return []
        fragments.append(text[start:end])
        cursor = end
    return fragments


def _balanced_group_end(text: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{" and not _escaped(text, index):
            depth += 1
        elif text[index] == "}" and not _escaped(text, index):
            depth -= 1
            if depth == 0:
                return index + 1
            if depth < 0:
                return None
    return None


def _balanced_latex(text: str) -> bool:
    depth = 0
    for index, character in enumerate(text):
        if character == "{" and not _escaped(text, index):
            depth += 1
        elif character == "}" and not _escaped(text, index):
            depth -= 1
            if depth < 0:
                return False
    if depth != 0:
        return False
    if text.count("$") % 2:
        return False
    for opening, closing in ((r"\(", r"\)"), (r"\[", r"\]")):
        if text.count(opening) != text.count(closing):
            return False
    return True


def _escaped(text: str, index: int) -> bool:
    backslashes = 0
    index -= 1
    while index >= 0 and text[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def _clean_lines(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw).strip()
        line = line.strip(" \t\r\n。；;，,")
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def _strip_answer_label(text: str) -> str:
    return re.sub(
        r"^(?:(?:最终答案|答案|结果|结论|answer|final answer)\s*(?:为|是|:|：)?\s*)+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _has_placeholder(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return True
    if lowered in _PLACEHOLDERS:
        return True
    compact = re.sub(r"[\s。.!！?？:：；;]+", "", lowered)
    return any(marker in compact for marker in _PLACEHOLDERS if len(marker) >= 2)
