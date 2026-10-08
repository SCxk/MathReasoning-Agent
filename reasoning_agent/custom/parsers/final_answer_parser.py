from typing import Any

from reasoning_agent.custom.parsers.answer_normalizer import (
    OBJECTIVE_MODES,
    detect_question_mode,
    format_answer_for_output,
    normalize_objective_answer,
    objective_answer_is_usable,
    sanitize_boxed_answer_text,
)


def normalize_final_response(
    answer: Any,
    *,
    problem: str = "",
    problem_type: str | None = None,
    mode: str | None = None,
) -> str:
    answer = sanitize_boxed_answer_text(answer)
    resolved_mode = mode or detect_question_mode(problem, problem_type)
    if resolved_mode in OBJECTIVE_MODES:
        normalized = normalize_objective_answer(answer, resolved_mode)
        if objective_answer_is_usable(normalized, resolved_mode):
            return normalized
        return "无法确定唯一答案"

    if resolved_mode == "proof":
        proof = format_answer_for_output(answer, resolved_mode)
        return proof or "无法确定唯一答案"

    # Preserve the legacy behavior when no question context is available. This
    # keeps internal/fallback callers backward compatible while public solve
    # paths pass the raw problem and receive mode-aware normalization.
    if resolved_mode == "other" and not problem and not problem_type and mode is None:
        return _legacy_normalize_final_response(answer)

    formatted = format_answer_for_output(answer, resolved_mode)
    if not formatted:
        return "无法确定唯一答案"
    return ensure_boxed_final_response(formatted)


def _legacy_normalize_final_response(answer: Any) -> str:
    text = str(answer or "").strip()
    if not text:
        return "无法确定唯一答案"

    for prefix in ("最终答案：", "最终答案:", "答案：", "答案:", "Answer:", "Final Answer:"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()

    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`").strip()
    text = text or "无法确定唯一答案"
    return ensure_boxed_final_response(text)


def ensure_boxed_final_response(text: str) -> str:
    normalized = sanitize_boxed_answer_text(text).strip()
    if not normalized or "\\boxed" in normalized:
        return normalized
    if normalized == "无法确定唯一答案":
        return normalized

    conclusion = _boxable_conclusion(normalized)
    if conclusion == normalized:
        return f"\\boxed{{{conclusion}}}"
    if conclusion:
        return f"{normalized}\n\n\\boxed{{{conclusion}}}"
    return normalized


def _boxable_conclusion(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""

    candidate = lines[-1]
    for prefix in ("最终答案为", "最终答案是", "答案为", "答案是", "因此", "故"):
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix) :].strip()
            break
    candidate = candidate.strip(" 。.，,；;：:")

    if len(lines) == 1 and len(candidate) <= 120:
        return candidate
    if len(candidate) <= 80 and not candidate.endswith(("。", ".", "；", ";")):
        return candidate
    return ""


def fallback_answer(ctx: Any) -> str:
    for candidate in reversed(getattr(ctx, "candidates", [])):
        answer = normalize_final_response(getattr(candidate, "answer", ""))
        if answer:
            return answer
    for raw in reversed(getattr(ctx, "raw_responses", [])):
        answer = normalize_final_response(raw)
        if answer:
            return answer
    return "无法确定唯一答案"
