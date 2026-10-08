import re
import time
from typing import Any

from pydantic import ValidationError

from reasoning_agent.custom.parsers.json_parser import extract_json_object
from reasoning_agent.custom2.context import (
    build_candidate_set_verifier_messages,
    build_critique_messages,
    build_candidate_verifier_messages,
    build_step_verifier_messages,
)
from reasoning_agent.custom2.models import AgentState, CandidateAnswer, ProblemFact
from reasoning_agent.custom2.model_call import (
    ModelCallBudgetExhausted,
    ModelCallTimedOut,
    call_model,
)
from reasoning_agent.custom2.schemas import (
    CandidateSetVerification,
    CandidateVerification,
    CheckItem,
    CritiqueOutput,
    ReasoningStep,
    StepVerification,
    SolutionDraft,
)


class FormalizationVerifier:
    def verify_problem_fact(self, problem: str, fact: ProblemFact) -> bool:
        source = fact.source_text.strip()
        if not source:
            return False
        return _compact(source) in _compact(problem)


class StepVerifier:
    def __init__(self, client: Any | None = None, max_tokens: int = 4096) -> None:
        self.client = client
        self.max_tokens = max_tokens

    def verify(
        self,
        state: AgentState,
        step: ReasoningStep,
        debug_trace: list[dict] | None = None,
    ) -> StepVerification:
        structural = self._verify_structural(state, step)
        if structural.verdict == "reject":
            return structural
        if self.client is None or not callable(getattr(self.client, "chat", None)):
            return structural
        llm_result = self._verify_with_llm(state, step, debug_trace)
        return llm_result or structural

    def _verify_structural(
        self,
        state: AgentState,
        step: ReasoningStep,
    ) -> StepVerification:
        known = {
            **{pf.id: pf for pf in state.problem_facts},
            **{d.id: d for d in state.definitions},
            **{r.id: r for r in state.derived_results},
        }
        used = step.used_facts + step.used_definitions + step.used_results
        for item_id in used:
            if item_id not in known:
                return _reject_dependency(f"引用了不存在的前提 {item_id}")
            if known[item_id].status != "verified":
                return _reject_dependency(f"引用了非 verified 前提 {item_id}")

        for proposal in step.new_definitions:
            for dep in proposal.depends_on:
                if dep not in known:
                    return _reject_dependency(f"定义依赖不存在的 ID {dep}")
                if known[dep].status != "verified":
                    return _reject_dependency(f"定义依赖非 verified ID {dep}")
            symbol = _extract_definition_symbol(proposal.statement)
            if symbol and _symbol_conflicts(symbol, proposal.statement, state):
                return StepVerification(
                    verdict="reject",
                    definition_consistency=CheckItem(
                        passed=False, reason=f"定义符号 {symbol} 与已有定义冲突"
                    ),
                    reason=f"定义符号 {symbol} 与已有定义冲突",
                    retry_instruction="换用新符号，或沿用已有定义的含义。",
                    error_category="definition_drift",
                )

        for proposal in step.new_results:
            for dep in proposal.depends_on:
                if dep not in known:
                    return _reject_dependency(f"推导结果依赖不存在的 ID {dep}")
                if known[dep].status != "verified":
                    return _reject_dependency(f"推导结果依赖非 verified ID {dep}")

        for task_id in step.closed_tasks:
            if not any(task.id == task_id for task in state.tasks):
                return StepVerification(
                    verdict="reject",
                    task_completion_validity=CheckItem(
                        passed=False, reason=f"申请关闭不存在的 Task {task_id}"
                    ),
                    reason=f"申请关闭不存在的 Task {task_id}",
                    retry_instruction="只关闭当前 state 中存在且本步确实完成的 Task。",
                    error_category="dependency_error",
                )
        if step.closed_tasks and not (step.new_results or step.candidate_answers):
            return StepVerification(
                verdict="reject",
                task_completion_validity=CheckItem(
                    passed=False,
                    reason="关闭 Task 必须由本步新 evidence 支持",
                ),
                reason="closed_tasks 只是关闭申请；没有 new evidence 时不能关闭 Task。",
                retry_instruction="先提出可验证的 DerivedResult 或 CandidateAnswer，再申请关闭对应 Task。",
                error_category="unsupported_claim",
            )

        if not (
            step.new_definitions
            or step.new_results
            or step.candidate_answers
            or step.closed_tasks
            or step.new_tasks
        ):
            return StepVerification(
                verdict="reject",
                actual_progress=CheckItem(passed=False, reason="本步没有状态 proposal"),
                reason="本步没有提出可验证的新定义、推导、候选答案或关闭申请。",
                retry_instruction="提出一个可独立验证的最小推进。",
                error_category="unsupported_claim",
            )

        return StepVerification(
            verdict="accept",
            reason="结构检查通过；proposal 可提交 Runtime commit。",
        )

    def _verify_with_llm(
        self,
        state: AgentState,
        step: ReasoningStep,
        debug_trace: list[dict] | None = None,
    ) -> StepVerification | None:
        messages = build_step_verifier_messages(state, step)
        for attempt in range(2):
            if (
                attempt > 0
                and state.efficient_runtime
                and state.deadline_at > 0
                and state.deadline_at - time.monotonic()
                <= state.finalize_reserve_seconds
            ):
                break
            try:
                response = call_model(
                    self.client,
                    state,
                    debug_trace,
                    "step_verifier",
                    messages=messages,
                    temperature=0.0,
                    thinking_mode=False,
                    max_tokens=self.max_tokens,
                )
                content = response.content
                data = extract_json_object(content or "")
                if not data:
                    raise ValueError("step verifier did not contain a valid JSON object")
                return StepVerification.model_validate(data)
            except (Exception, ValidationError) as exc:
                if isinstance(exc, (ModelCallBudgetExhausted, ModelCallTimedOut)):
                    return None
                if attempt == 0:
                    messages.append(
                        {
                            "role": "user",
                            "content": _build_json_retry_message(
                                protocol_name="StepVerification",
                                required_fields=(
                                    "verdict, logical_validity, definition_consistency, "
                                    "algebra_correctness, quantifier_correctness, "
                                    "dependency_validity, actual_progress, "
                                    "task_completion_validity, reason, retry_instruction, "
                                    "error_category"
                                ),
                                error=str(exc),
                                response_excerpt=str(locals().get("content", "")),
                            ),
                        }
                    )
                    continue
                return None


class CandidateVerifier:
    def __init__(self, client: Any | None = None, max_tokens: int = 4096) -> None:
        self.client = client
        self.max_tokens = max_tokens

    def verify(
        self,
        state: AgentState,
        candidate: CandidateAnswer,
        debug_trace: list[dict] | None = None,
        *,
        allow_finalize_reserve: bool = False,
    ) -> CandidateVerification:
        if self.client is None or not callable(getattr(self.client, "chat", None)):
            return CandidateVerification(
                verdict="reject",
                reason="未配置独立 Candidate Verifier，不能把候选升级为 verified。",
            )
        messages = build_candidate_verifier_messages(state, candidate)
        for attempt in range(2):
            if (
                attempt > 0
                and state.efficient_runtime
                and state.deadline_at > 0
                and state.deadline_at - time.monotonic()
                <= state.finalize_reserve_seconds
            ):
                break
            try:
                response = call_model(
                    self.client,
                    state,
                    debug_trace,
                    "candidate_verifier",
                    allow_finalize_reserve=allow_finalize_reserve,
                    messages=messages,
                    temperature=0.0,
                    thinking_mode=False,
                    max_tokens=self.max_tokens,
                )
                content = response.content
                data = extract_json_object(content or "")
                if not data:
                    raise ValueError("candidate verifier did not contain a valid JSON object")
                verification = CandidateVerification.model_validate(data)
                if verification.verdict == "accept":
                    protocol_errors = _candidate_verification_protocol_errors(
                        candidate, verification
                    )
                    if protocol_errors:
                        raise ValueError(
                            "candidate verifier accept lacks independent evidence: "
                            + "; ".join(protocol_errors)
                        )
                return _enforce_candidate_failed_route_memory(state, verification)
            except (Exception, ValidationError) as exc:
                if isinstance(exc, (ModelCallBudgetExhausted, ModelCallTimedOut)):
                    return CandidateVerification(
                        verdict="conflict",
                        reason="候选验证因运行时间不足未完成。",
                    )
                if attempt == 0:
                    messages.append(
                        {
                            "role": "user",
                            "content": _build_json_retry_message(
                                protocol_name="CandidateVerification",
                                required_fields=(
                                    "verdict, reason, independent_method, "
                                    "falsification_attempt, method_type, checked_claims, "
                                    "tested_cases, route_difference, "
                                    "failed_route_assessment, failed_route_reason"
                                ),
                                error=str(exc),
                                response_excerpt=str(locals().get("content", "")),
                            ),
                        }
                    )
                    continue
                break
        return CandidateVerification(
            verdict="reject",
            reason="Candidate Verifier 未返回合法验证结果。",
        )


def _candidate_verification_protocol_errors(
    candidate: CandidateAnswer,
    verification: CandidateVerification,
) -> list[str]:
    errors: list[str] = []
    for field_name in (
        "independent_method",
        "falsification_attempt",
        "route_difference",
    ):
        if not getattr(verification, field_name).strip():
            errors.append(f"missing {field_name}")
    if verification.method_type is None:
        errors.append("missing method_type")
    if not any(item.strip() for item in verification.checked_claims):
        errors.append("missing checked_claims")
    if not any(item.strip() for item in verification.tested_cases):
        errors.append("missing tested_cases")

    independent = _compact(verification.independent_method)
    source_parts = [
        candidate.source_solution_draft,
        *candidate.source_strategy_methods,
    ]
    if len(independent) >= 12 and any(
        independent in _compact(part) or _compact(part) in independent
        for part in source_parts
        if len(_compact(part)) >= 12
    ):
        errors.append("independent_method repeats solver route")
    if verification.method_type and _source_uses_method_type(
        source_parts, verification.method_type
    ):
        errors.append("method_type already used by solver route")
    return errors


def _source_uses_method_type(source_parts: list[str], method_type: str) -> bool:
    terms_by_type = {
        "direct_substitution": ("代回", "代入原", "substitut"),
        "alternate_representation": ("换元", "另一表示", "等价表示", "transform"),
        "boundary_analysis": ("边界", "端点", "极端情形", "boundary"),
        "counterexample_search": ("反例", "推翻", "counterexample"),
        "small_case_enumeration": ("枚举", "穷举", "小规模", "small case", "enumerat"),
    }
    terms = terms_by_type.get(method_type, ())
    source = " ".join(source_parts).lower()
    return bool(terms) and any(term in source for term in terms)


class CandidateSetVerifier:
    def __init__(self, client: Any | None = None, max_tokens: int = 4096) -> None:
        self.client = client
        self.max_tokens = max_tokens

    def verify(
        self,
        state: AgentState,
        debug_trace: list[dict] | None = None,
    ) -> CandidateSetVerification:
        if self.client is None or not callable(getattr(self.client, "chat", None)):
            return CandidateSetVerification(
                verdict="incomplete",
                reason="未配置 CandidateSetVerifier。",
                repair_instruction="重新检查全部候选并证明候选集合完备。",
            )
        messages = build_candidate_set_verifier_messages(state)
        content = ""
        for attempt in range(2):
            if (
                attempt > 0
                and state.efficient_runtime
                and state.deadline_at > 0
                and state.deadline_at - time.monotonic()
                <= state.finalize_reserve_seconds
            ):
                break
            try:
                response = call_model(
                    self.client,
                    state,
                    debug_trace,
                    "candidate_set_verifier",
                    messages=messages,
                    temperature=0.0,
                    thinking_mode=False,
                    max_tokens=self.max_tokens,
                )
                content = response.content
                data = extract_json_object(content or "")
                if not data:
                    raise ValueError(
                        "candidate set verifier did not contain a valid JSON object"
                    )
                return CandidateSetVerification.model_validate(data)
            except (Exception, ValidationError) as exc:
                if isinstance(exc, (ModelCallBudgetExhausted, ModelCallTimedOut)):
                    return CandidateSetVerification(
                        verdict="incomplete",
                        reason="候选集合完备性验证因运行时间不足未完成。",
                        repair_instruction="保留现有候选，但不得视为已完成完备性证明。",
                    )
                if attempt == 0:
                    messages.append(
                        {
                            "role": "user",
                            "content": _build_json_retry_message(
                                protocol_name="CandidateSetVerification",
                                required_fields=(
                                    "verdict, verified_candidate_ids, "
                                    "rejected_candidate_ids, complete_answer, "
                                    "missing_cases, reason, repair_instruction"
                                ),
                                error=str(exc),
                                response_excerpt=content,
                            ),
                        }
                    )
        return CandidateSetVerification(
            verdict="incomplete",
            reason="CandidateSetVerifier 未返回合法 JSON。",
            repair_instruction="重新检查全部候选并证明候选集合完备。",
        )


class DraftCritic:
    def __init__(self, client: Any | None = None, max_tokens: int = 4096) -> None:
        self.client = client
        self.max_tokens = max_tokens

    def critique(
        self,
        state: AgentState,
        step: ReasoningStep,
        draft: SolutionDraft,
        debug_trace: list[dict] | None = None,
    ) -> CritiqueOutput:
        if self.client is None or not callable(getattr(self.client, "chat", None)):
            return CritiqueOutput(
                verdict="repair",
                invalid_claims=[claim.id for claim in draft.claims],
                candidate_assessment="uncertain" if draft.candidate_answers else "absent",
                reason="未配置数学 Critique client。",
                repair_instruction="重新检查完整草稿并补齐关键论证。",
            )
        messages = build_critique_messages(state, step, draft)
        content = ""
        for attempt in range(2):
            if (
                attempt > 0
                and state.efficient_runtime
                and state.deadline_at > 0
                and state.deadline_at - time.monotonic()
                <= state.finalize_reserve_seconds
            ):
                break
            try:
                response = call_model(
                    self.client,
                    state,
                    debug_trace,
                    "draft_critic",
                    messages=messages,
                    temperature=0.0,
                    thinking_mode=False,
                    max_tokens=self.max_tokens,
                )
                content = response.content
                data = extract_json_object(content or "")
                if not data:
                    raise ValueError("critique did not contain a valid JSON object")
                critique = CritiqueOutput.model_validate(data)
                return _enforce_critique_failed_route_memory(state, draft, critique)
            except (Exception, ValidationError) as exc:
                if attempt == 0:
                    messages.append(
                        {
                            "role": "user",
                            "content": _build_json_retry_message(
                                protocol_name="CritiqueOutput",
                                required_fields=(
                                    "verdict, accepted_claims, invalid_claims, "
                                    "candidate_assessment, reason, repair_instruction, "
                                    "failed_route_summary, failed_route_assessment, "
                                    "failed_route_reason"
                                ),
                                error=str(exc),
                                response_excerpt=content,
                            ),
                        }
                    )
        return CritiqueOutput(
            verdict="repair",
            invalid_claims=[claim.id for claim in draft.claims],
            candidate_assessment="uncertain" if draft.candidate_answers else "absent",
            reason="Critique 未返回合法 JSON。",
            repair_instruction="复核整份草稿并重新提交合法、完整的论证。",
        )


def _enforce_critique_failed_route_memory(
    state: AgentState,
    draft: SolutionDraft,
    critique: CritiqueOutput,
) -> CritiqueOutput:
    """Prevent an accept from silently bypassing unresolved failed-route memory."""

    if critique.verdict != "accept" or not state.error_memory:
        return critique
    assessment = critique.failed_route_assessment
    reason = critique.failed_route_reason.strip()
    overlap = _has_explicit_failed_route_overlap(state, draft.text)
    repaired = assessment == "repaired" and _describes_route_repair(reason)
    if assessment == "not_reused" and not overlap:
        return critique
    if repaired:
        return critique
    return CritiqueOutput(
        verdict="reject_route",
        accepted_claims=[],
        invalid_claims=[claim.id for claim in draft.claims],
        candidate_assessment="uncertain" if draft.candidate_answers else "absent",
        reason=(
            "Runtime failed-route gate rejected Critic accept：当前草稿复用了最近失败路线，"
            "或 Critic 未明确证明旧反例/逻辑缺口已经解决。"
        ),
        repair_instruction="改用不同核心方法；若要恢复旧路线，必须明确重述旧错误并给出消除反例的可检查证明。",
        failed_route_summary=reason or "failed route assessment missing or unresolved",
        failed_route_assessment="unresolved",
        failed_route_reason=reason,
    )


def _enforce_candidate_failed_route_memory(
    state: AgentState,
    verification: CandidateVerification,
) -> CandidateVerification:
    """Require candidate verification to explicitly resolve recent route failures."""

    if verification.verdict != "accept" or not state.error_memory:
        return verification
    assessment = verification.failed_route_assessment
    reason = verification.failed_route_reason.strip()
    overlap = _has_explicit_failed_route_overlap(state, state.solution_draft.text)
    if assessment == "not_reused" and not overlap:
        return verification
    if assessment == "repaired" and _describes_route_repair(reason):
        return verification
    return CandidateVerification(
        verdict="reject",
        reason=(
            "Runtime failed-route gate：候选仍依赖最近被否定的路线，"
            "或独立验证没有说明旧反例/逻辑缺口如何被解决。"
            + (f" 审查说明：{reason}" if reason else "")
        ),
        failed_route_assessment="unresolved",
        failed_route_reason=reason,
    )


def _has_explicit_failed_route_overlap(state: AgentState, current_text: str) -> bool:
    current = _compact_route_text(current_text)
    if not current:
        return False
    for error in state.error_memory[-6:]:
        failed = _compact_route_text(f"{error.step_summary} {error.reason}")
        if _longest_common_substring_length(current, failed) >= 12:
            return True
    return False


def _compact_route_text(text: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(text).lower())


def _longest_common_substring_length(left: str, right: str) -> int:
    threshold = 12
    if len(left) < threshold or len(right) < threshold:
        return 0
    shorter, longer = sorted((left, right), key=len)
    for index in range(len(shorter) - threshold + 1):
        if shorter[index : index + threshold] in longer:
            return threshold
    return 0


def _describes_route_repair(reason: str) -> bool:
    normalized = reason.lower()
    repair_markers = (
        "修复", "旧错误", "原错误", "反例", "缺口", "不再假设", "改为",
        "repair", "counterexample", "previous error", "gap", "instead",
    )
    return len(reason.strip()) >= 12 and any(marker in normalized for marker in repair_markers)


def _reject_dependency(reason: str) -> StepVerification:
    return StepVerification(
        verdict="reject",
        dependency_validity=CheckItem(passed=False, reason=reason),
        reason=reason,
        retry_instruction="只引用当前 authoritative state 中存在且 status=verified 的 P/D/R。",
        error_category="dependency_error",
    )


def _build_json_retry_message(
    protocol_name: str,
    required_fields: str,
    error: str,
    response_excerpt: str,
) -> str:
    excerpt = " ".join(str(response_excerpt or "").split())[:1200]
    return (
        f"上一条输出不是合法 {protocol_name} JSON，必须重新输出。\n"
        f"解析错误：{error[:1000]}\n"
        f"原始输出片段：{excerpt}\n\n"
        "请只重发一个 JSON 对象，不要解释，不要 Markdown。\n"
        f"必须包含字段：{required_fields}。\n"
        "JSON 字符串内部不得出现未转义的英文双引号；中文引用请用 '单引号'、"
        "“中文引号” 或《书名号》。"
    )


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _extract_definition_symbol(statement: str) -> str | None:
    match = re.search(r"(?:令|设|记)?\s*([A-Za-z][A-Za-z0-9_]*|[a-zA-Z]\\?_\{?n\}?)\s*(?:表示|为|=)", statement)
    if match:
        return match.group(1)
    match = re.search(r"([A-Za-z][A-Za-z0-9_]*)", statement)
    return match.group(1) if match else None


def _symbol_conflicts(symbol: str, statement: str, state: AgentState) -> bool:
    normalized = _compact(statement)
    for definition in state.definitions:
        if definition.status != "verified":
            continue
        old_symbol = _extract_definition_symbol(definition.statement)
        if old_symbol == symbol and _compact(definition.statement) != normalized:
            return True
    return False
