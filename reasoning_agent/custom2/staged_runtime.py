from __future__ import annotations

import json
import re
import time
from typing import Any, Mapping

from reasoning_agent.custom2.model_call import ModelResponse, call_model
from reasoning_agent.custom2.models import AgentState
from reasoning_agent.custom2.program_checks import check_expression, numeric_equalities, requested_checks
from reasoning_agent.custom2.solution_parser import infer_profile
from reasoning_agent.custom2.problem_requirements import structure_instruction
from reasoning_agent.custom2.staged_answer_extractor import (
    extract_staged_answer, render_staged_response,
)
from reasoning_agent.custom2.staged_models import StagedAudit, StagedModelFidelity, StagedStrategy
from reasoning_agent.custom2.staged_prompts import (
    STAGED_AUDIT_PROMPT, STAGED_COMPACT_SOLVER_INSTRUCTION,
    STAGED_COMPACT_SOLVER_PROMPT,
    STAGED_COMPRESSED_SOLVER_INSTRUCTION,
    STAGED_DIRECT_EMERGENCY_PROMPT, STAGED_EMERGENCY_PROMPT, STAGED_MODEL_FIDELITY_PROMPT,
    STAGED_SOLVER_PROMPT,
    STAGED_SOLVER_SYSTEM_PROMPT, STAGED_STRATEGY_PROMPT,
)
from reasoning_agent.custom2.state_manager import remaining_seconds
from reasoning_agent.custom2.strategy_skills import (
    ALLOWED_SKILL_CATEGORIES,
    retrieve_skill_material,
    select_strategy_skills,
    skill_catalog,
    theorem_cards,
)
from reasoning_agent.custom2.text_models import ProblemProfile
from reasoning_agent.custom2.text_prompts import PROFILE_PROMPT
from reasoning_agent.custom.parsers.json_parser import extract_json_object, make_json_safe
from reasoning_agent.strategy_retrieval import (
    build_structure_messages,
    get_shared_strategy_retriever,
    normalize_retrieval_text,
)
from reasoning_agent.lexical_strategy_retrieval import get_shared_lexical_strategy_retriever
from reasoning_agent.action_graph.strategy_cards import (
    bound_card_text,
    build_strategy_cards,
    trace_results,
)


_SOLUTION_SECTIONS = ("## 问题分析", "## 详细解题步骤", "## 最终答案", "## 关键验证点")
_COMPRESSED_PREFILL = "## 问题分析\n"


def effective_staged_budget_seconds(config: Any) -> tuple[float, float, float]:
    """Keep time for returning a result before the platform's hard deadline."""
    configured = min(1200.0, max(0.0, float(
        getattr(config, "custom2_total_budget_seconds", 1200.0)
    )))
    headroom = min(configured, max(0.0, float(
        getattr(config, "custom2_platform_deadline_headroom_seconds", 0.0)
    )))
    return configured, headroom, configured - headroom
_RAW_FORMULA_PATTERN = re.compile(r"\\\([\s\S]*?\\\)|\$[^$\n]+\$")
_CONSTRAINT_CUE_PATTERN = re.compile(
    r"\b(?:all|each|exactly|only|must|such that|if|then|start|end|permutation|"
    r"integer|distinct|adjacent|nonnegative)\b|"
    r"任意|每个|恰好|仅|必须|满足|起点|终点|排列|整数|互异|相邻|边界",
    re.I,
)


class StagedReasoningRuntime:
    """Classification/strategy plus one complete solve, with gated audit recovery."""

    def __init__(self, client: Any, config: Any) -> None:
        self.client = client
        self.config = config
        self.trace: list[dict] = []
        self.debug_trace: list[dict] = []
        self.state: AgentState | None = None
        self._last_call_error: tuple[str, str] | None = None
        self._last_model_response: ModelResponse | None = None
        self._last_structured_response = ""
        self._last_solver_partial = ""
        self._last_structured_response = ""
        self._strategy_retrieval_text = ""
        self._constraint_ledger = ""
        self._strategy_results: list[dict[str, Any]] = []
        self._planner_strategy_cards = ""
        self._solver_strategy_cards = ""
        self._audit_skill_summary = ""
        self._persistent_avoidance: list[str] = []
        self._best_candidate_draft = ""
        self._best_candidate_source = ""
        self._answer_mode = "other"

    def run(self, problem: str, metadata: dict | None = None) -> dict:
        started = time.monotonic()
        self.trace, self.debug_trace = [], []
        self._last_solver_partial = ""
        self._strategy_retrieval_text = ""
        self._constraint_ledger = ""
        self._strategy_results = []
        self._planner_strategy_cards = ""
        self._solver_strategy_cards = ""
        self._audit_skill_summary = ""
        self._persistent_avoidance = []
        self._best_candidate_draft = ""
        self._best_candidate_source = ""
        self._answer_mode = "other"
        self._constraint_ledger = self._build_constraint_ledger(problem)
        configured_budget, deadline_headroom, total_budget = effective_staged_budget_seconds(
            self.config
        )
        convergence_budget = min(
            total_budget,
            max(0.0, float(getattr(self.config, "staged_convergence_seconds", 960.0))),
        )
        final_reserve = min(
            total_budget,
            max(
                0.0,
                float(getattr(self.config, "custom2_finalize_reserve_seconds", 120.0)),
                total_budget - convergence_budget,
            ),
        )
        self.state = AgentState(
            problem=problem, efficient_runtime=True, started_at=started,
            deadline_at=started + total_budget,
            best_candidate_deadline_at=started + max(
                0.0,
                total_budget - max(0.0, float(getattr(
                    self.config, "staged_best_candidate_return_seconds", 25.0
                ))),
            ),
            finalize_reserve_seconds=final_reserve,
        )
        self._convergence_budget = convergence_budget
        self._record(
            "staged_runtime_started",
            workflow="profile_strategy_single_solver",
            configured_budget_seconds=configured_budget,
            platform_deadline_headroom_seconds=deadline_headroom,
            effective_budget_seconds=total_budget,
        )
        self._record(
            "constraint_ledger_prepared",
            source="raw_problem",
            content=self._constraint_ledger,
        )
        profile = self._profile(problem)
        self._answer_mode = profile.answer_mode
        self._retrieve_strategy_examples(problem, profile)
        strategy = self._strategy(problem, profile)
        skills, material = retrieve_skill_material(
            strategy.skill_domains,
            strategy.skill_sections,
            fallback_category=profile.domain,
            problem=problem,
        )
        if not material:
            skills = select_strategy_skills(profile.domain, [], top_k=2)
            material = "\n\n".join(f"【{s.category}】\n{s.prompt}" for s in skills)
        cards = theorem_cards([s.category for s in skills])
        if cards:
            material = cards + "\n\n" + material
        self._audit_skill_summary = self._build_audit_skill_summary(skills)
        self._record(
            "strategy_skills_loaded",
            domain=profile.domain,
            skills=[{"category": s.category, "path": s.path} for s in skills],
        )
        trace_limit = max(
            0, int(getattr(self.config, "staged_trace_solution_max_chars", 12000))
        )
        trace_material = material[:trace_limit]
        self._record(
            "skill_material_injected",
            target="strategy_and_solver",
            skills=[
                {
                    "category": s.category,
                    "path": s.path,
                    "chars": len(s.prompt),
                }
                for s in skills
            ],
            total_chars=len(material),
            content=trace_material,
            truncated=len(material) > trace_limit,
        )
        draft = self._solve(problem, profile, strategy, material, attempt=1)
        if draft:
            self._save_candidate(draft, source="primary_solver")
        if draft is None:
            # A timed-out request may still have produced a usable boxed
            # answer before its fixed sections were complete.  Preserve that
            # answer before spending the remaining budget on emergency work.
            partial_answer = self._extract_or_reject(self._last_solver_partial)
            if partial_answer != "无法确定唯一答案":
                self._save_candidate(self._last_solver_partial, source="solver_partial")
                self._record("partial_answer_preserved", source="solver_partial")
                return self._result(self._saved_candidate_answer(self._last_solver_partial))
            emergency = self._emergency_solve(
                problem, profile, strategy, "Solver 未在收敛阀值前返回完整解答"
            )
            self._save_candidate(emergency, source="emergency")
            return self._result(self._saved_candidate_answer(emergency))
        if self._convergence_due():
            self._record("convergence_deadline_reached", action="return_existing_solution")
            return self._result(self._saved_candidate_answer(draft))
        checks = self._local_checks(problem, profile, strategy, draft)
        high_risk = strategy.risk_level != "low" or not checks["ok"]
        needs_audit = high_risk
        self._record("local_checks_completed", ok=checks["ok"], high_risk=high_risk,
                     checks=checks["summary"])
        if needs_audit:
            if self._convergence_due():
                self._record("convergence_deadline_reached", action="skip_audit_return_existing_solution")
                return self._result(self._saved_candidate_answer(draft))
            fidelity = self._model_fidelity(problem, draft, strategy)
            self._record(
                "model_fidelity_completed",
                verdict=fidelity.verdict,
                first_fatal_error=fidelity.first_fatal_error[:300],
                additional_errors=[issue.model_dump() for issue in fidelity.additional_errors],
            )
            audit = (
                self._fidelity_failure_as_audit(fidelity)
                if fidelity.verdict == "fail"
                else self._audit(problem, profile, strategy, draft, checks)
            )
            self._remember_audit_findings(audit)
            self._record("targeted_audit_completed", **self._audit_trace_data(audit))
            # Numerical geometry answers need an explicit independent
            # trigonometric/coordinate recomputation; a bare audit pass is not
            # enough because an internally consistent diagram argument can
            # still have the wrong ratio.
            if (
                audit.verdict == "pass"
                and profile.answer_mode == "computation"
                and re.search(r"直角三角形|right triangle", problem, re.I)
                and re.search(r"比值|ratio", problem, re.I)
                and not re.search(
                    r"坐标|正弦|余弦|正切|sin|cos|tan|代入|复算|coordinate",
                    f"{audit.evidence} {audit.counterexample_or_evidence}",
                    re.I,
                )
            ):
                audit = audit.model_copy(update={
                    "verdict": "fail",
                    "first_fatal_error": "几何比值未提供独立三角函数/坐标复算证据。",
                    "required_changes": ["独立用正弦定理或坐标代入复算比值"],
                    "replacement_route": "分别求出两段长度后约分并检查角度方向",
                })
            format_violation = "non_concept_final_answer_contains_chinese" in checks["summary"]
            if format_violation and audit.verdict == "pass":
                # A logically sound draft can still violate the output
                # protocol.  Turn this into a targeted repair rather than
                # allowing a Chinese prose answer for a formulaic problem.
                audit = audit.model_copy(update={
                    "verdict": "fail",
                    "first_fatal_error": (
                        "非概念题的最终答案必须改写为公式、符号、坐标方程或数值，"
                        "不能使用中文自然语言短语。"
                    ),
                })
                self._record(
                    "format_violation_repair_requested",
                    reason="non_concept_final_answer_contains_chinese",
                )
            if audit.verdict == "uncertain":
                # An uncertain audit is not evidence that the candidate is
                # safe. Convert it into a bounded repair request so the
                # solver must independently re-check the unresolved claim.
                audit = audit.model_copy(update={
                    "verdict": "fail",
                    "first_fatal_error": (
                        audit.first_fatal_error.strip()
                        or "审计无法独立确认最终答案；必须重新推导并完成可执行验证。"
                    ),
                    "required_changes": [
                        *audit.required_changes,
                        "从原题独立重算最终答案并给出边界或代回验证",
                    ],
                })
                self._record("uncertain_audit_repair_requested")
            if audit.verdict == "fail" and audit.first_fatal_error.strip():
                original_draft = draft
                repair_source = draft
                repair_audit_input = audit
                repair_accepted = False
                # Keep every usable, independently generated candidate.  A
                # failed repair is evidence, not an instruction to erase an
                # earlier route that may be stronger or even correct.
                arbitration_candidates: list[dict[str, Any]] = []
                if extract_staged_answer(original_draft).answer is not None:
                    arbitration_candidates.append({
                        "attempt": 1,
                        "draft": original_draft,
                        "audit": audit,
                    })
                max_repairs = max(
                    0, int(getattr(self.config, "custom2_max_repairs", 4))
                )
                for repair_index in range(1, max_repairs + 1):
                    if self._best_candidate_return_due():
                        self._record(
                            "convergence_deadline_reached",
                            action="stop_repairs_return_existing_solution",
                            repairs_attempted=repair_index - 1,
                        )
                        break
                    if self._convergence_due():
                        self._record(
                            "convergence_deadline_reached",
                            action="stop_repairs_allow_final_arbitration",
                            repairs_attempted=repair_index - 1,
                        )
                        break
                    repaired = self._solve(
                        problem, profile, strategy, material,
                        attempt=repair_index + 1,
                        previous=repair_source,
                        audit=repair_audit_input,
                    )
                    if not repaired:
                        self._record(
                            "repair_rejected",
                            repair_index=repair_index,
                            reason="repair_no_usable_response",
                        )
                        break
                    self._save_candidate(repaired, source=f"repair_{repair_index}")
                    previous_answer = extract_staged_answer(repair_source).answer
                    repaired_answer = extract_staged_answer(repaired).answer
                    same_answer = (
                        previous_answer is not None
                        and repaired_answer is not None
                        and re.sub(r"\s+", "", previous_answer).strip("$\\{}")
                        == re.sub(r"\s+", "", repaired_answer).strip("$\\{}")
                    )
                    if repaired.strip() == repair_source.strip() or same_answer:
                        self._record(
                            "repair_answer_unchanged",
                            repair_index=repair_index,
                            reason=(
                                "repair_answer_unchanged"
                                if same_answer else "repair_identical_to_previous"
                            ),
                        )
                    repair_checks = self._local_checks(
                        problem, profile, strategy, repaired
                    )
                    repair_fidelity = self._model_fidelity(problem, repaired, strategy)
                    self._record(
                        "repair_model_fidelity_completed",
                        repair_index=repair_index,
                        verdict=repair_fidelity.verdict,
                        first_fatal_error=repair_fidelity.first_fatal_error[:300],
                        additional_errors=[issue.model_dump() for issue in repair_fidelity.additional_errors],
                    )
                    repair_audit = (
                        self._fidelity_failure_as_audit(repair_fidelity)
                        if repair_fidelity.verdict == "fail"
                        else self._audit(
                            problem, profile, strategy, repaired, repair_checks
                        )
                    )
                    self._remember_audit_findings(repair_audit)
                    self._record("repair_audit_completed", repair_index=repair_index,
                                 **self._audit_trace_data(repair_audit))
                    if extract_staged_answer(repaired).answer is not None:
                        arbitration_candidates.append({
                            "attempt": repair_index + 1,
                            "draft": repaired,
                            "audit": repair_audit,
                        })
                    if repair_audit.verdict == "pass":
                        draft = repaired
                        # A passed repair is the selected answer.  The durable
                        # fallback still contains the primary draft unless it
                        # is explicitly replaced here.
                        self._save_candidate(
                            repaired,
                            source=f"repair_{repair_index}",
                            replace=True,
                        )
                        repair_accepted = True
                        self._record(
                            "repair_accepted",
                            repair_index=repair_index,
                        )
                        break
                    self._record(
                        "repair_rejected",
                        repair_index=repair_index,
                        reason="repair_audit_not_pass",
                        verdict=repair_audit.verdict,
                    )
                    # Continue from the newest attempted derivation so the
                    # next repair can address the latest audit feedback, while
                    # retaining the original draft as the safe fallback.
                    repair_source = repaired
                    repair_audit_input = repair_audit
                else:
                    draft = original_draft
                if not repair_accepted:
                    if self._best_candidate_return_due():
                        draft = self._select_deadline_candidate(
                            arbitration_candidates, original_draft,
                        )
                        self._record(
                            "best_candidate_returned",
                            reason="best_candidate_return_threshold",
                            candidate_count=len(arbitration_candidates),
                        )
                        return self._result(self._saved_candidate_answer(draft))
                    arbitrated = self._final_arbitrate(
                        problem, profile, strategy, original_draft,
                        repair_source, repair_audit_input,
                        candidates=arbitration_candidates,
                    )
                    if arbitrated and extract_staged_answer(arbitrated).answer is not None:
                        draft = arbitrated
                        self._save_candidate(arbitrated, source="final_arbitration", replace=True)
                        self._record(
                            "final_arbitration_selected",
                            candidate_count=len(arbitration_candidates),
                        )
                    else:
                        # The original candidate is the stable fallback.  It
                        # is not assumed correct, but unlike the latest draft
                        # it is not selected merely because it was produced
                        # last after an unresolved repair loop.
                        draft = (
                            self._select_deadline_candidate(
                                arbitration_candidates, original_draft,
                            )
                            if self._best_candidate_return_due()
                            else self._best_candidate_draft or original_draft
                        )
                        self._record(
                            "final_arbitration_unavailable_original_preserved",
                            candidate_count=len(arbitration_candidates),
                        )
        return self._result(self._saved_candidate_answer(draft))

    def _extract_or_reject(self, draft: str) -> str:
        extracted = extract_staged_answer(draft)
        self._record("answer_extraction", status=extracted.reason,
                     extracted=extracted.answer is not None)
        return extracted.answer or "无法确定唯一答案"

    def recover_unhandled_exception(self, exc: Exception) -> dict:
        """Return a JSON-safe best effort result when staged orchestration fails.

        Model-call failures are normally handled inside ``_call``.  This is the
        final guard for unrelated failures such as local retrieval or parser
        errors, after a Solver candidate may already have been saved.
        """
        try:
            self._record(
                "staged_runtime_recovered_exception",
                error_type=type(exc).__name__,
                message=str(exc)[:500],
                saved_candidate=bool(self._best_candidate_draft),
            )
            answer = self._saved_candidate_answer()
            result = self._result(answer)
        except Exception as recovery_exc:
            # Never let diagnostic recovery recreate the empty-response error.
            trace = list(self.trace) if isinstance(self.trace, list) else []
            trace.append({
                "type": "staged_runtime_recovery_failed",
                "time": time.time(),
                "data": {"error_type": type(recovery_exc).__name__},
            })
            result = {
                "final_response": "无法确定唯一答案",
                "solve_status": "failed",
                "trace": trace,
                "debug_trace": self.debug_trace if isinstance(self.debug_trace, list) else [],
            }
        return make_json_safe(result)

    def _save_candidate(self, draft: str, *, source: str, replace: bool = False) -> bool:
        """Persist a usable draft before later checks or recovery can fail."""
        candidate = str(draft or "").strip()
        extracted = extract_staged_answer(candidate)
        if extracted.answer is None:
            return False
        if self._best_candidate_draft and not replace:
            return True
        self._best_candidate_draft = candidate
        self._best_candidate_source = source
        self._record(
            "best_candidate_saved",
            source=source,
            extraction=extracted.reason,
        )
        return True

    def _saved_candidate_answer(self, fallback: str = "") -> str:
        """Prefer the durable candidate over a newer unresolved draft."""
        candidate = self._best_candidate_draft or fallback
        if self._answer_mode == "proof":
            rendered = render_staged_response(candidate, self._answer_mode)
            self._record("proof_response_rendered", chars=len(rendered))
            return rendered
        return self._extract_or_reject(candidate)

    def _select_deadline_candidate(
        self, candidates: list[dict[str, Any]], fallback: str,
    ) -> str:
        """Choose the plurality answer at hard cutoff, preserving first-candidate ties."""
        ordered: list[tuple[str, str]] = []
        counts: dict[str, int] = {}
        for record in candidates:
            draft = str(record.get("draft") or "").strip()
            answer = extract_staged_answer(draft).answer
            if answer is None:
                continue
            normalized = re.sub(r"\s+", "", answer)
            if not normalized:
                continue
            if normalized not in counts:
                ordered.append((normalized, draft))
                counts[normalized] = 0
            counts[normalized] += 1
        if not ordered:
            return self._best_candidate_draft or fallback
        winning_key, winning_draft = ordered[0]
        for key, draft in ordered[1:]:
            if counts[key] > counts[winning_key]:
                winning_key, winning_draft = key, draft
        self._save_candidate(winning_draft, source="deadline_plurality", replace=True)
        self._record(
            "deadline_candidate_selected",
            distinct_answer_count=len(ordered),
            winning_count=counts[winning_key],
            tie=sum(count == counts[winning_key] for count in counts.values()) > 1,
        )
        return winning_draft

    def _remember_audit_findings(self, audit: StagedAudit) -> None:
        """Persist rejected analogies and shortcuts for the current problem only."""
        candidates = [*audit.forbidden_reuse]
        for issue in audit.additional_errors:
            candidates.extend(issue.forbidden_reuse)
            if issue.prevention_rule.strip():
                candidates.append(issue.prevention_rule)
        for candidate in candidates:
            normalized = re.sub(r"\s+", " ", str(candidate or "")).strip()
            if normalized and normalized not in self._persistent_avoidance:
                self._persistent_avoidance.append(normalized)

    def _persistent_avoidance_context(self) -> str:
        if not self._persistent_avoidance:
            return ""
        return (
            "【本题跨轮防类比清单】以下模型、捷径或类比已经被本题审查否定。"
            "后续推导不得复用，也不得换词后重新引入；任何类似结论必须从原题重新证明：\n- "
            + "\n- ".join(self._persistent_avoidance)
        )

    @staticmethod
    def _audit_trace_data(audit: StagedAudit) -> dict[str, Any]:
        """Retain every audit field while bounding individual free-text values."""
        def bound(value: str, limit: int = 1200) -> str:
            text = str(value or "")
            return text if len(text) <= limit else text[:limit].rstrip() + "[已截断]"

        payload = audit.model_dump()
        for name in (
            "first_fatal_error", "evidence", "repair_instruction", "invalid_claim",
            "counterexample_or_evidence", "replacement_route",
        ):
            payload[name] = bound(payload[name])
        payload["additional_errors"] = [
            {
                **issue.model_dump(),
                "invalid_claim": bound(issue.invalid_claim),
                "evidence": bound(issue.evidence),
                "affected_reasoning": bound(issue.affected_reasoning),
                "prevention_rule": bound(issue.prevention_rule),
            }
            for issue in audit.additional_errors
        ]
        return payload

    def _record_solution_steps(self, draft: str, attempt: int) -> None:
        """Record only the bounded detailed-step section, never the full response."""
        match = re.search(
            r"^\s*##\s*详细解题步骤\s*$([\s\S]*?)(?=^\s*##\s+|\Z)",
            draft,
            re.MULTILINE,
        )
        content = match.group(1).strip() if match else ""
        limit = max(0, int(getattr(self.config, "staged_trace_solution_max_chars", 12000)))
        truncated = len(content) > limit
        if truncated:
            content = content[:limit].rstrip() + "\n[详细步骤已截断]"
        self._record(
            "solution_steps_recorded",
            attempt=attempt,
            content=content,
            content_length=len(match.group(1).strip()) if match else 0,
            truncated=truncated,
        )

    def _convergence_due(self) -> bool:
        assert self.state is not None
        configured = getattr(self, "_convergence_budget", 960.0)
        return_window = max(0.0, float(getattr(
            self.config, "staged_new_work_cutoff_seconds", 150.0
        )))
        threshold = configured
        if self.state.best_candidate_deadline_at > 0:
            threshold = min(threshold, max(0.0, (
                self.state.deadline_at - self.state.started_at - return_window
            )))
        return time.monotonic() - self.state.started_at >= threshold

    def _best_candidate_return_due(self) -> bool:
        assert self.state is not None
        return self.state.best_candidate_deadline_at > 0 and time.monotonic() >= self.state.best_candidate_deadline_at

    def _emergency_solve(self, problem: str, profile: ProblemProfile,
                         strategy: StagedStrategy, reason: str) -> str:
        partial = self._last_solver_partial.strip()
        call_type = "emergency_integrator" if partial else "emergency_direct_solver"
        system_prompt = STAGED_EMERGENCY_PROMPT if partial else STAGED_DIRECT_EMERGENCY_PROMPT
        payload = {
            "problem": problem, "profile": profile.model_dump(), "strategy": strategy.model_dump(),
            "partial_solution": partial, "reason": reason,
            "special_requirements": self._build_special_requirements(problem, profile),
        }
        self._record("emergency_solve_started", mode="integrate" if partial else "direct")
        response = self._call(call_type, system_prompt, payload,
                              # Preserve the established emergency output ceiling even
                              # when its hidden-thinking mode is disabled.
                              max_tokens=self._thinking_max_tokens(),
                              allow_finalize=True,
                              max_timeout_seconds=float(getattr(
                                  self.config, "staged_emergency_timeout_seconds", 300.0,
                              )))
        if response and (
            self._has_complete_solution_sections(response)
            or extract_staged_answer(response).answer is not None
        ):
            return response.strip()
        return "## 问题分析\n在总时间阀值内未能生成完整解答。\n\n## 详细解题步骤\n已有模型请求未返回可用完整推导。\n\n## 最终答案\n无法确定唯一答案。\n\n## 关键验证点\n- 发生了请求或时间预算耗尽。"

    def _final_arbitrate(
        self,
        problem: str,
        profile: ProblemProfile,
        strategy: StagedStrategy,
        original_draft: str,
        latest_draft: str,
        latest_audit: StagedAudit,
        *,
        candidates: list[dict[str, Any]] | None = None,
    ) -> str | None:
        """Make one bounded evidence-based final choice after repairs fail."""
        candidate_records = candidates or [
            {"attempt": 1, "draft": original_draft, "audit": latest_audit},
            {"attempt": "latest", "draft": latest_draft, "audit": latest_audit},
        ]
        evidence_parts = [
            "【仲裁候选说明】候选按生成顺序排列，不代表后者更可靠；"
            "每个候选的审计仅在其包含可核验证据时才可用作否定依据。"
        ]
        seen_drafts: set[str] = set()
        for record in candidate_records:
            candidate_draft = str(record.get("draft") or "").strip()
            normalized = re.sub(r"\s+", "", candidate_draft)
            if not candidate_draft or normalized in seen_drafts:
                continue
            seen_drafts.add(normalized)
            candidate_audit = record.get("audit")
            audit_payload = (
                candidate_audit.model_dump()
                if isinstance(candidate_audit, StagedAudit)
                else latest_audit.model_dump()
            )
            answer = extract_staged_answer(candidate_draft).answer or "（未抽取到明确答案）"
            evidence_parts.append(
                f"【候选 {record.get('attempt', '?')}｜答案：{answer}】\n"
                + candidate_draft[:6000]
                + "\n【该候选的审核记录】\n"
                + json.dumps(audit_payload, ensure_ascii=False, indent=2)[:3500]
            )
        evidence_parts.extend([
            "【检索策略小结】\n" + (self._planner_strategy_cards or "（无）")[:5000],
            "【相关技能小结】\n" + (self._audit_skill_summary or "（无）")[:3000],
        ])
        evidence = "\n\n".join(evidence_parts)
        reason = (
            "多轮修复未获审计通过。现在必须在全部候选路线之间仲裁，而不是默认采用最后一版。"
            "逐项比较候选对原题的保真度、可复算推导、策略适用条件和审计的实际证据；"
            "没有草稿原文和题面/反例/复算支撑的审计 fail 只能视为未决疑点，不能据此否定候选。"
            "优先选择能闭合最多关键义务且未被可核验证据推翻的答案；若候选答案冲突，做最小必要重算裁决。"
            "不得因候选较新、篇幅较长或审计措辞更强就默认选择它。"
            "必须输出四个完整章节和一个明确最终答案。"
        )
        self._record("final_arbitration_started")
        response = self._call(
            "final_arbitrator", STAGED_EMERGENCY_PROMPT,
            {
                "problem": problem,
                "profile": profile.model_dump(),
                "strategy": strategy.model_dump(),
                "partial_solution": evidence,
                "reason": reason,
                "special_requirements": self._build_special_requirements(problem, profile),
            },
            # Arbitration keeps the prior emergency output ceiling while
            # running without hidden thinking by default.
            max_tokens=self._thinking_max_tokens(),
            allow_finalize=True,
            max_timeout_seconds=float(getattr(
                self.config, "staged_final_arbitrator_timeout_seconds", 120.0,
            )),
        )
        if response and (
            self._has_complete_solution_sections(response)
            or extract_staged_answer(response).answer is not None
        ):
            return response.strip()
        self._record("final_arbitration_failed")
        return None

    def _profile(self, problem: str) -> ProblemProfile:
        allowed = ", ".join(ALLOWED_SKILL_CATEGORIES)
        profile_prompt = (
            f"{PROFILE_PROMPT}\n"
            f"domain 只能逐字使用以下英文名称之一：{allowed}；"
            "无法明确归入专门课程时使用 advanced_olympiad_mathematics。"
        )
        payload = self._structured("classifier", profile_prompt, {"problem": problem})
        proposed = None
        if payload:
            try:
                proposed = ProblemProfile.model_validate(payload)
            except Exception:
                proposed = None
        profile = infer_profile(problem, proposed)
        self._record("problem_profile", domain=profile.domain, answer_mode=profile.answer_mode,
                     obligations=profile.obligations)
        return profile

    def _strategy(self, problem: str, profile: ProblemProfile) -> StagedStrategy:
        if not bool(getattr(self.config, "staged_strategy_model_enabled", False)):
            strategy = StagedStrategy(
                problem_type=profile.answer_mode,
                warnings=["已跳过模型策略规划；使用 Profile、本地技能和策略检索卡直接求解"],
            )
            self._record(
                "strategy_skipped",
                reason="model_strategy_disabled",
                risk_level=strategy.risk_level,
            )
            return strategy
        planning_skills, planning_material = retrieve_skill_material(
            (),
            (),
            fallback_category=profile.domain,
            problem=problem,
            max_chars=max(0, int(getattr(
                self.config, "staged_strategy_skill_material_max_chars", 8000
            ))),
        )
        planning_cards = theorem_cards([skill.category for skill in planning_skills])
        if planning_cards:
            planning_material = planning_cards + "\n\n" + planning_material
        planning_trace_limit = max(
            0, int(getattr(self.config, "staged_trace_solution_max_chars", 12000))
        )
        self._record(
            "strategy_skill_material_injected",
            target="strategy_planner",
            skills=[
                {"category": skill.category, "path": skill.path, "chars": len(skill.prompt)}
                for skill in planning_skills
            ],
            total_chars=len(planning_material),
            content=planning_material[:planning_trace_limit],
            truncated=len(planning_material) > planning_trace_limit,
        )
        payload = {
            "problem": problem,
            "profile": profile.model_dump(),
            "constraint_ledger": self._constraint_ledger,
            "special_requirements": self._build_special_requirements(problem, profile),
            "strategy_skill_material": planning_material or "（无匹配技能节选）",
            "skill_catalog": skill_catalog(),
            "skill_selection_rule": (
                "从目录中选择最相关的最多两个领域和最多八个章节；"
                "只能返回目录中出现的领域/章节标题，不要复制技能正文。"
            ),
        }
        if self._planner_strategy_cards:
            payload["strategy_case_summaries"] = self._planner_strategy_cards
        data = self._structured("strategy", STAGED_STRATEGY_PROMPT, payload)
        if not isinstance(data, dict):
            strategy = StagedStrategy(risk_level="high", warnings=["策略输出无法解析，转入高风险审查"])
        else:
            # Strategy is advisory context, not a trust boundary. A single
            # overlong explanation must not discard otherwise useful section
            # identifiers and force an unrelated fallback skill selection.
            strategy = StagedStrategy.model_construct(**self._normalize_strategy_payload(data))
            self._record("strategy_unvalidated_payload_accepted",
                         fields=sorted(str(key) for key in data.keys()))
        # Do not let a weak strategy classification disable verification for
        # long-form derivations.  Only short objective/choice prompts are
        # safe to treat as low risk without a full audit.
        if (
            strategy.risk_level == "low"
            and profile.answer_mode not in {"choice", "judgment", "fill_blank"}
            and len(problem) > 320
        ):
            strategy = strategy.model_copy(update={
                "risk_level": "high",
                "warnings": [*strategy.warnings, "长题面且非客观题，强制进行独立审计"],
            })
        self._record("strategy_committed", risk_level=strategy.risk_level,
                     obligations=strategy.proof_obligations,
                     key_theorems=strategy.key_theorems,
                     skill_domains=strategy.skill_domains,
                     skill_sections=strategy.skill_sections)
        return strategy

    @staticmethod
    def _normalize_strategy_payload(data: Mapping[str, Any]) -> dict[str, Any]:
        """Coerce advisory JSON shapes without reintroducing all-or-nothing validation."""
        list_fields = (
            "proof_obligations", "checks", "key_theorems", "warnings",
            "skill_domains", "skill_sections",
        )
        scalar_fields = ("problem_type", "main_method", "backup_method")
        normalized: dict[str, Any] = {}
        for field in scalar_fields:
            if field in data:
                normalized[field] = StagedReasoningRuntime._strategy_text(data[field])
        for field in list_fields:
            if field not in data:
                continue
            value = data[field]
            values = value if isinstance(value, (list, tuple)) else [value]
            normalized[field] = [
                StagedReasoningRuntime._strategy_text(item)
                for item in values if item is not None
            ]
        risk_level = str(data.get("risk_level", "medium")).strip().lower()
        normalized["risk_level"] = (
            risk_level if risk_level in {"low", "medium", "high"} else "medium"
        )
        return normalized

    @staticmethod
    def _strategy_text(value: Any) -> str:
        if isinstance(value, Mapping):
            name = str(value.get("name", "") or "").strip()
            detail = "；".join(
                str(value.get(key, "") or "").strip()
                for key in ("applicability", "condition", "detail", "description")
                if str(value.get(key, "") or "").strip()
            )
            if name and detail:
                return f"{name}：{detail}"
            if name:
                return name
            return json.dumps(dict(value), ensure_ascii=False, sort_keys=True)
        return str(value or "").strip()

    def _build_constraint_ledger(self, problem: str) -> str:
        """Preserve raw constraint wording without interpreting it via a model."""
        limit = max(0, int(getattr(
            self.config, "staged_constraint_ledger_max_chars", 12000,
        )))
        raw_lines = [line.strip() for line in problem.splitlines() if line.strip()]
        source_lines = [
            line for line in raw_lines
            if _RAW_FORMULA_PATTERN.search(line) or _CONSTRAINT_CUE_PATTERN.search(line)
        ]
        if not source_lines:
            source_lines = [problem.strip()]
        formulas = list(dict.fromkeys(_RAW_FORMULA_PATTERN.findall(problem)))
        formula_block = "\n".join(formulas)
        source_block = "\n".join(dict.fromkeys(source_lines))
        ledger = "【原题约束原文（不得改写）】\n" + source_block
        if formula_block:
            ledger += "\n\n【原题数学公式锚点（逐字保留）】\n" + formula_block
        if limit and len(ledger) > limit:
            # Formula anchors have priority because they are the exact
            # operator-level constraints a later model may otherwise relax.
            prefix = "【原题数学公式锚点（逐字保留）】\n" + formula_block
            if len(prefix) >= limit:
                return prefix[:limit]
            remaining = limit - len(prefix) - 2
            return prefix + "\n\n" + source_block[:max(0, remaining)]
        return ledger[:limit] if limit else ""

    @staticmethod
    def _build_special_requirements(problem: str, profile: ProblemProfile) -> str:
        """Turn structural risk signals in the raw problem into solver obligations.

        These are not candidate-specific hints: every clause either applies to all
        derivations or is enabled by a property visible in the current problem.
        Keeping the requirements in the user prompt makes them survive compact and
        repair paths instead of relying on a long system-side reminder.
        """
        requirements = [
            "先写出对象、转移/关系和答案对象的精确定义；每个从局部条件推出的全局结构"
            "都必须给出证明，不能把观察到的模式当作引理。",
            "计数、分类或递推必须说明编码与原对象之间的双向对应，分别排除重复计数和漏计；"
            "有限小规模只可校验递推，不能代替一般证明。",
        ]
        text = problem.lower()
        coordinate_vertices = bool(re.search(
            r"ordered\s+pairs?|有序对|\(\s*x\s*,\s*y\s*\)|"
            r"\(x\s*,\s*y\)", problem, re.I,
        ))
        permutation_cover = bool(re.search(r"permutations?\s+.*elements|排列.*元素", problem, re.I))
        hamiltonian = bool(re.search(r"哈密尔顿|hamiltonian", problem, re.I)) or (
            coordinate_vertices and permutation_cover
        )
        grid = bool(re.search(r"网格|棋盘|grid|board|列|行", problem, re.I)) or coordinate_vertices
        periodic = bool(re.search(
            r"模\s*\d+|mod(?:ulo)?\s*\d+|周期|循环|环面|wrap.?around|cyclic|"
            r"\bcycle\b|\bC_\d+\b|[-−]\s*1\D{0,12}(?:or|或)\D{0,12}\d{2,}|"
            r"\d{2,}\D{0,12}(?:or|或)\D{0,12}[-−]\s*1", text, re.I,
        ))
        ordered_transition = bool(re.search(
            r"x\s*(?:_|\\_)?i\s*[-−]\s*x\s*(?:_|\\_)?\{?i\s*\+\s*1\}?|"
            r"x_i\s*[-−]\s*x_\{?i\+1\}?|有向|directed|顺序|ordered", problem, re.I,
        ))
        if hamiltonian and grid:
            requirements.extend([
                "哈密尔顿计数必须以每个顶点最终入/出度、端点和整体单一路径为约束；"
                "不得把局部度数满足误当作连通且无子环。",
                "按切割面/frontier 给出有限状态：至少说明边界未配对端的度数、连通分量、"
                "起终端标记及最后闭合筛选如何更新。",
            ])
        if hamiltonian and grid and periodic and ordered_transition:
            requirements.extend([
                "周期有向坐标中，‘不能反向走’不推出列坐标全局单调，也不推出离开某列后"
                "不能经完整周期回到该列的另一个顶点；必须显式分析这种回返。",
                "若使用‘每列连续块访问’、蛇形唯一性或每个切口固定穿越次数，必须先从题面证明；"
                "无法证明时不得以此缩小状态空间。",
                "状态转移计数必须说明‘合法路径前缀 -> 状态’和‘接受状态 -> 唯一完整路径’的对应，"
                "并在周期首尾连接处排除过早闭合的子环与端点不符的状态。",
            ])
        if profile.answer_mode in {"computation", "proof", "derivation"}:
            requirements.append(
                "最终数值或闭式须由递推、状态转移、双射或独立计算之一推出，并给出至少一个"
                "实际小规模/边界实例的输入与结果作为交叉核验。"
            )
        if profile.answer_mode == "proof":
            requirements.extend([
                "这是证明题：最终输出必须保留完整证明链，至少明确命题、关键引理或定义、"
                "逐步推出关系以及结论闭合；不能只返回一个数值或\\boxed{}结论。",
                "最终答案章节只总结已证明的命题/解集/构造，证明正文必须留在详细解题步骤中；"
                "必要性、充分性、无遗漏、边界或构造验证按题面要求逐项写出。",
            ])
        elif profile.answer_mode == "choice":
            requirements.append(
                "这是选择题：逐项判定选项后，最终输出只保留完整选项字母集合；不要把解释混入最终答案。"
            )
        elif profile.answer_mode == "judgment":
            requirements.append(
                "这是判断题：最终输出只保留‘正确’或‘错误’，必要的理由放在详细步骤中。"
            )
        elif profile.answer_mode == "fill_blank":
            requirements.append(
                "这是填空题：最终输出只保留题面要求的完整术语、数值或表达式，按空位顺序列出。"
            )
        elif profile.answer_mode == "computation":
            requirements.append(
                "这是计算/求解题：最终输出优先给出可直接判分的数值、表达式、集合或方程，"
                "推导和验证放在前面的章节。"
            )
        requirements.extend(
            line.strip() for line in structure_instruction(problem).splitlines()
            if line.strip()
        )
        return "\n".join(f"- {item}" for item in requirements)

    def _retrieve_strategy_examples(self, problem: str, profile: ProblemProfile | None = None) -> None:
        """Retrieve one script-equivalent strategy bundle under staged budgets."""
        if not bool(getattr(self.config, "staged_strategy_retrieval_enabled", True)):
            self._record("staged_strategy_retrieval_skipped", reason="disabled")
            return
        top_k = getattr(self.config, "staged_strategy_retrieval_top_k", 2)
        if not isinstance(top_k, int) or top_k < 1:
            self._record("staged_strategy_retrieval_skipped", reason="invalid_top_k")
            return
        assert self.state is not None
        pool = max(0.0, float(getattr(self.config, "staged_strategy_retrieval_pool_seconds", 90.0)))
        if pool <= 0 or remaining_seconds(self.state) <= self.state.finalize_reserve_seconds:
            self._record("staged_strategy_retrieval_degraded", reason="budget_insufficient")
            return
        started = time.monotonic()
        try:
            messages = build_structure_messages(problem)
            raw = self._call(
                "strategy_retrieval",
                "你是数学题结构化检索分析器。",
                {},
                max_tokens=int(getattr(self.config, "staged_strategy_retrieval_max_tokens", 512)),
                max_timeout_seconds=min(
                    pool,
                    max(0.001, float(getattr(self.config, "staged_strategy_retrieval_timeout_seconds", 60.0))),
                ),
                thinking_mode=bool(getattr(self.config, "staged_strategy_retrieval_thinking_mode", False)),
                temperature=0.0,
                messages_override=messages,
            )
            retrieval_text = normalize_retrieval_text(raw)
            if time.monotonic() - started > pool:
                raise TimeoutError("strategy_retrieval_pool_exhausted")
            mode = str(getattr(self.config, "staged_strategy_retrieval_mode", "lexical")).strip().lower()
            if mode == "disabled":
                self._record("staged_strategy_retrieval_skipped", reason="mode_disabled", mode=mode)
                return
            if mode == "lexical":
                retrieved = get_shared_lexical_strategy_retriever().retrieve_for_structure(
                    problem, retrieval_text, top_k=top_k,
                    metadata={"domain": profile.domain, "obligations": " ".join(profile.obligations)}
                    if profile else None,
                )
            elif mode == "legacy_embedding":
                retrieved = get_shared_strategy_retriever().retrieve_for_structure(
                    problem, retrieval_text, top_k=top_k,
                )
            else:
                raise ValueError("invalid staged_strategy_retrieval_mode")
            if time.monotonic() - started > pool:
                raise TimeoutError("strategy_retrieval_pool_exhausted")
            self._strategy_retrieval_text = retrieved["retrieval_text"]
            self._strategy_results = list(retrieved["results"])
            cards = build_strategy_cards(
                self._strategy_results,
                max_chars=max(0, int(getattr(self.config, "staged_strategy_card_max_chars", 12000))),
            )
            self._planner_strategy_cards = cards.planner
            self._solver_strategy_cards = cards.executor
            trace_limit = max(0, int(getattr(self.config, "staged_strategy_trace_max_chars", 12000)))
            planner_cards, planner_truncated = bound_card_text(cards.planner, trace_limit)
            solver_cards, solver_truncated = bound_card_text(cards.executor, trace_limit)
            self._record(
                "staged_strategy_retrieval_completed",
                mode=mode,
                index_version=retrieved.get("index_version", "legacy_embedding"),
                retrieval_text=self._strategy_retrieval_text[:trace_limit],
                results=trace_results(self._strategy_results),
                planner_cards=planner_cards,
                solver_cards=solver_cards,
                planner_cards_truncated=cards.planner_truncated or planner_truncated,
                solver_cards_truncated=cards.executor_truncated or solver_truncated,
            )
        except Exception as exc:
            self._record(
                "staged_strategy_retrieval_degraded",
                reason="runtime_or_resource_failure",
                error_type=type(exc).__name__,
            )

    def _solve(self, problem: str, profile: ProblemProfile, strategy: StagedStrategy,
               material: str, *, attempt: int, previous: str = "", audit: StagedAudit | None = None) -> str | None:
        solver_material = material
        if re.search(r"直角三角形|right triangle", problem, re.I) and re.search(r"比值|ratio", problem, re.I):
            # Long olympiad skill files can drown out a short coordinate
            # computation.  Use a focused card for this structurally simple
            # subtype while retaining the full material for other attempts.
            solver_material = (
                theorem_cards([profile.domain, "differential_geometry"])
                + "\n\n"
                "坐标模板：令 X=(0,0)、XY 为 x 轴、XZ=1；若 ∠X=A，则 "
                "Y=(cos A,0), Z=(cos A,sin A)，射线 θ 与 YZ 的交点纵坐标为 cos(A)tan(θ)。"
            )
        repair_context = ""
        if previous and audit:
            retrieval_query = "\n".join((
                audit.error_type,
                audit.first_fatal_error,
                audit.invalid_claim,
                audit.counterexample_or_evidence,
                audit.replacement_route,
                audit.repair_instruction,
                " ".join(audit.required_changes),
                " ".join(audit.forbidden_reuse),
                *(
                    " ".join((
                        issue.error_type, issue.invalid_claim, issue.evidence,
                        issue.affected_reasoning, issue.prevention_rule,
                        " ".join(issue.required_changes),
                        " ".join(issue.forbidden_reuse),
                    ))
                    for issue in audit.additional_errors
                ),
                " ".join(self._persistent_avoidance),
                previous[:6000],
            ))
            repair_skills, repair_material = retrieve_skill_material(
                strategy.skill_domains,
                (),
                fallback_category=profile.domain,
                problem=problem,
                retrieval_query=retrieval_query,
                max_chars=18000,
            )
            if repair_material.strip():
                repair_cards = theorem_cards([skill.category for skill in repair_skills])
                solver_material = (
                    (repair_cards + "\n\n" if repair_cards else "")
                    + repair_material
                )
                self._record(
                    "repair_skill_material_refreshed",
                    attempt=attempt,
                    skills=[{"category": skill.category, "path": skill.path} for skill in repair_skills],
                    query_signals=[
                        signal for signal in (
                            audit.error_type, audit.replacement_route,
                        ) if signal
                    ],
                    total_chars=len(solver_material),
                )
            # After the first failed repair, carrying the entire previous
            # derivation forward tends to anchor the solver to the same
            # invalid model. Keep the audit's concrete failure evidence, but
            # force later attempts to re-derive from the original problem.
            previous_block = (
                previous
                if attempt <= 2
                else "[上一版完整解答已省略；不得沿用其模型、递推或最终答案]"
            )
            repair_context = (
                "【定向修复上下文】\n"
                f"上一版解答：\n{previous_block}\n\n"
                "审查结果：\n"
                f"{json.dumps(audit.model_dump(), ensure_ascii=False, indent=2)}\n\n"
                f"{self._persistent_avoidance_context()}\n\n"
                "【强制修复要求】\n"
                "1. 必须从审查指出的第一个致命错误处重新推导，不能只改措辞或重排原文。\n"
                "2. 必须逐项回应 invalid_claim、counterexample_or_evidence、required_changes 和 unmet_obligations；若反例成立，必须修正受影响的结论。\n"
                "3. forbidden_reuse、additional_errors 及“本题跨轮防类比清单”中列出的模型、方向、递推、候选或证明步骤禁止再次使用；replacement_route 是最低要求，不是可选建议。\n"
                "4. 最终答案或支撑最终答案的关键推导必须发生实质变化；不得原样返回上一版解答。\n"
                "5. 重新检查答案类型、边界、构造/反例和所有题目问项；至少给出一个可执行的小规模或边界验证。\n"
                "6. 只有完成上述修复并通过后续独立审查，修复稿才会被采用。\n"
                "7. 若上一版已被审查否决，优先从原题重新建立模型；不要为了保持原答案而修改局部措辞。\n"
                "【修复闭环要求】先逐项写出：被否定的旧命题、其不成立的题面/反例证据、"
                "新模型（对象、状态、转移、边界、端点），以及新模型如何逐条避免旧错误。\n"
                "禁止把‘某固定端点唯一’直接替换成‘任意端点对唯一’，或把单个构造推广为所有构造；"
                "任何‘任意、唯一、只能、所有、每对’结论必须单独证明必要性、充分性和完备性。\n"
                "【计数模型硬约束】对计数、覆盖、Hamilton 路径、排列相邻或周期图问题，"
                "不得只凭局部度数、无死胡同直觉、蛇形图样或单个构造宣布唯一性。必须完整执行"
                "frontier/cut 状态递推、双射或完整分类之一；若用列连续、切口固定穿越或单调等结构，"
                "必须先从题面证明。\n"
                "【验证一致性硬门槛】验证中若出现重复、遗漏、不合法边、端点不符、计数不一致、"
                "无解、需修正或‘实际应为’，当前路线无效；不得输出由它支撑的最终数值。"
            )
        solver_system = STAGED_SOLVER_SYSTEM_PROMPT.replace(
            "{category}", profile.domain or "unknown"
        )
        domain_guidance = {
            "linear_regression": (
                "本题若是教材单选/填空，先按课程中对‘通常采用’的标准口径作答；"
                "区分最小二乘估计、极大似然估计和牛顿迭代的层级，不因方法在广义上可用就选‘以上都可以’。"
            ),
            "statistical_inference": (
                "时间序列季节调整要区分移动平均、季节分解和具体指数法；填空保留教材中的完整方法名称，"
                "按题目空格数量给出对应数量的方法。若题干只问季节调整的常用基础方法，优先核对教材对"
                "移动平均法与时间序列分解法的标准表述，不要用某一种派生的季节指数计算步骤替代方法名称。"
            ),
            "mathematical_analysis": (
                "实数集上的紧致性必须同时检查闭、有界条件与开覆盖定义；逐项判断选择项，不能只凭关键词。"
            ),
            "topology": (
                "在R^n中使用Heine-Borel定理时明确闭且有界与开覆盖有限子覆盖的等价关系，并逐项排除反例。"
            ),
            "combinatorics": (
                "计数时严格区分有序/无序、允许重复与否以及题面中密度参数的归一化；"
                "不要因为左右两侧或正反方向对称就自动乘2。用最小规模和极端构造复核常数因子。"
            ),
            "advanced_olympiad_mathematics": (
                "数论/函数题先固定定义域和量词，再做整除、模运算或边界代回；‘所有/可能值’必须证明完备性，"
                "不能只给一个看似自然的构造。"
            ),
        }.get(profile.domain, "")
        if domain_guidance:
            solver_system += "\n【领域口径补充】\n" + domain_guidance
        if attempt >= 3:
            solver_system += (
                "\n【独立重建模式】这是前面修复未通过后的独立候选。不要把审计中的替代路线或上一版"
                "结论当作事实；从原题逐字重新建模，优先使用策略中的 backup_method（若不适用则说明理由），"
                "并用一个与前次不同的边界、构造或小规模检查验证最终答案。"
            )
        if re.search(r"极线|polar", problem, re.I):
            solver_system += (
                "\n【极线题定理卡片】对圆心 C、半径 r 的圆，点 Y 的极线可写为 "
                "(Y-C)·(X-C)=r^2；先把三条极线写成直线方程，再用三线组成三角形的圆方程/行列式，"
                "最后代入 X=Y 并检查 Y 在题目规定区域，不能用‘看起来是某个圆’代替推导。"
            )
            if re.search(r"垂心|orthocenter", problem, re.I):
                solver_system += (
                    "若三个圆的半径分别是顶点到垂心的距离，先验证垂心同时在三圆上；"
                    "再测试该特殊点处的三条极线是否退化为切线，并用一般点的代数条件排除额外轨迹。"
                    "先把 Y=M 代入作为必检候选；若消元得到圆/直线族，必须继续检查 Y 在外接圆外、"
                    "三条极线不平行以及圆的非退化条件，不能仅凭一个半径公式宣布整条轨迹。"
                    "最终答案若是轨迹中的单点，要明确写成 Y=M（或等价的点集方程），不要只写 {M}，"
                    "以免丢失题目要求的变量关系。"
                )
        if re.search(r"直角三角形|right triangle", problem, re.I) and re.search(r"比值|ratio", problem, re.I):
            solver_system += (
                "\n【直角三角形比值卡片】分别在含 P、Q 的小三角形中应用正弦定理，"
                "把共享的边/角逐项消去后再形成比值；必须保留点在线段上的顺序和角度方向，"
                "不要把两个看似对称的分点直接当成等距。可采用坐标复算：令 X=(0,0)、XY 在 x 轴、"
                "XZ=1，则 Y=(cos A,0)、Z=(cos A,sin A)，每条从 X 出发的射线与 YZ 的交点满足 "
                "y=cos(A)tan(theta)；最后代回所求比值。"
            )
        if re.search(r"哈密尔顿|Hamiltonian", problem, re.I) and re.search(r"棋盘|grid|board|网格", problem, re.I):
            solver_system += (
                "\n【窄网格哈密尔顿计数卡片】不要假设蛇形路径唯一；按列/行建立有限状态转移，"
                "状态记录边界度数、连通分量和端点，逐列合并并在最后筛选单一路径。"
                "小宽度时必须列出状态递推或至少用小规模枚举校准总数。"
            )
        if re.search(r"多米诺|domino|铺砌|tiling|tile", problem, re.I):
            solver_system += (
                "\n【铺砌计数卡片】不要把每个局部方块强行分块，也不要由必要的染色/奇偶条件直接推出充分性。"
                "按行或列保存占用掩码，枚举所有合法横放/竖放转移；对题目额外的每个局部窗口条件逐个检查，"
                "最后用初始掩码、终止掩码和小尺寸枚举校准递推。局部条件若等价于禁止某个2×2窗口满覆盖，"
                "不要未经证明断言所有骨牌同向；先把横向覆盖的行状态与纵向覆盖的列状态分别编码，"
                "再用边界窗口和总骨牌数筛选，避免把一个必要结构误当成完整分类。"
            )
        if re.search(r"simple graph|简单图|common neighbor|共同邻居|邻域交", problem, re.I):
            solver_system += (
                "\n【图计数归一化卡片】先把题目所数的对象写成有序/无序元组的精确定义，"
                "再逐项计算同一对象在求和中的出现次数；不要因二部图的左右对称自动乘 2。"
                "对候选极值构造直接计算边数、邻域交和题目目标量，并用最小 n 的图枚举检查常数因子。"
                "若边数下界写成 λn²，先固定 λ 的归一化口径，再检查目标元组总共有 s+t 个顶点位置；"
                "Jensen/幂和递推每次引入的 n 次方必须与剩余自由位置对应，不能凭平均度把额外的 2 或 n 乘进去。"
                "对于无向简单图且密度按 |E|/n² 记为 λ，最终密度因子应从 λ 本身展开；"
                "有序元组的方向已由 x/y 位置计数，不能再补一个 2^{st}。"
            )
        if re.search(r"n-good|good function|函数.*整除|g\s*:\s*\\?mathbb", problem, re.I):
            solver_system += (
                "\n【整除函数分类卡片】先由定义推出 g 的候选形状，再分别检查定义域中的负数、0、1、"
                "合成数与符号/奇偶约束；计数时不能把形式上可写出的指数或符号选择直接当成不同合法函数，"
                "必须逐项代回 n-good 定义并证明没有遗漏。先从 b=0 与 a=1 推出 g(0) 的全部可能，"
                "再分别处理平移/反射分支和幂指数分支；用 n=1、素数、素数平方和两个不同素因子的小例子"
                "核对 N(n) 的计数公式，绝不能未经证明把 N(n) 直接等同于 2τ(n) 或把所有完全平方数列入。"
            )
        if re.search(r"Lucas|Fibonacci|斐波那契|卢卡斯", problem, re.I):
            solver_system += (
                "\n【递推数列构造卡片】使用 Lucas/Fibonacci 差值时先列出小下标的重复值并去重，"
                "明确下标范围和量词；下界后必须给出达到下界的可验证构造，逐个检查每个目标差值确实出现。"
            )
        if re.search(r"tuple|元组|维数|dimension", problem, re.I):
            solver_system += (
                "\n【题面维数一致性卡片】逐字检查每个运算是否保持元组长度。若起始维数与目标维数冲突，"
                "不得未经说明把数字改成笔误；分别给出按字面结论与任何附加假设下的结论，并判断题目是否因此无解或不唯一。"
            )
        if re.search(r"good number|good integers|删除.*数字|remove.*digit", problem, re.I):
            solver_system += (
                "\n【数字递归构造卡片】对每个候选数必须展示完整的逐次删位/整除链；"
                "不能把‘尝试若干删除均失败’与‘候选成立’同时写出。求最大值时用可复现的状态搜索或严格上界覆盖全部分支。"
            )
        if re.search(r"function|函数", problem, re.I) and re.search(r"C\s*\(|C\s*:\s*|不等式|inequality", problem, re.I):
            solver_system += (
                "\n【正整数函数不等式卡片】先代入最小的 a,b 与 b 的复合值，建立单调性/整除性或递推约束；"
                "再证明这些约束对所有正整数充分且必要。求某个 C(N) 的所有值时，必须同时给出每个候选的构造"
                "和排除其他值的全称证明，不能只列出几个试算结果。"
            )
        if re.search(r"tetramino|hexamino|四连块|六连块|S-?tetra|L-?hexa", problem, re.I):
            solver_system += (
                "\n【混合铺砌最优化卡片】先计算每种砖块面积、黑白染色/加权不变量和边界贡献，"
                "用不变量给出所用 domino 数的严格下界；随后提供满足所有边界与旋转限制的周期或分块构造，"
                "逐格检查而不是只按总面积配平。"
            )
        if re.search(r"difference|差值|差分|Fibonacci|Lucas|斐波那契|卢卡斯", problem, re.I) and re.search(r"set|集合", problem, re.I):
            solver_system += (
                "\n【差值基/递推数列卡片】把每个要求的差值标成必须覆盖的目标集合，"
                "用 C(m,2) 给出下界但要处理目标值重复；构造时逐一展示 x-y 等于每个目标，"
                "并单独解析题面中附加集合或量词的含义，不能把另一集合的条件悄悄并入 S。"
                "可检验 Fibonacci 恒等式 F_{2j}-F_{2j-2}=F_{2j-1} 以及 "
                "L_j=F_{j+2}-F_{j-2}，但必须按题面下标范围证明构造覆盖和最小性。"
            )
        compact_by_default = bool(
            getattr(self.config, "staged_solver_compact_by_default", True)
        )
        solver_prompt = self._render_solver_prompt(
            problem, profile, strategy, solver_material,
            repair_context=repair_context,
            recovery_context=(
                STAGED_COMPACT_SOLVER_INSTRUCTION if compact_by_default else ""
            ),
        )
        if attempt == 1 and bool(
            getattr(self.config, "staged_compact_reasoning_only", False)
        ):
            self._record(
                "primary_direct_compressed_started",
                reason="staged_compact_reasoning_only",
            )
            compressed = self._compressed_solve(
                problem, profile, strategy, solver_material, solver_system,
                repair_context=repair_context,
                attempt=attempt,
                failure_reason="compact_reasoning_only",
            )
            if compressed and self._has_complete_solution_sections(compressed):
                self._save_candidate(compressed, source=f"solver_attempt_{attempt}")
                self._record("compressed_solution_received", attempt=attempt,
                             content_length=len(compressed))
                self._record_solution_steps(compressed, attempt)
                return compressed
            if compressed and extract_staged_answer(compressed).answer is not None:
                extracted = extract_staged_answer(compressed)
                self._save_candidate(compressed, source=f"solver_attempt_{attempt}")
                self._record("partial_solution_accepted", attempt=attempt,
                             extraction=extracted.reason, content_length=len(compressed))
                return compressed
            self._record("compressed_solution_invalid", attempt=attempt,
                         reason=self._solver_failure_reason(compressed))
            return None
        if attempt > 1:
            # An audit has already rejected the original route.  Spending the
            # scarce recovery window on another long-form repair and then
            # reserving a second compact retry gave the actual repair only a
            # few seconds in practice.  Go straight to one independent,
            # bounded compact re-derivation; it receives the concrete audit
            # evidence and is still re-audited before it may replace the
            # original draft.
            self._record(
                "repair_direct_compressed_started",
                attempt=attempt,
                reason="audit_rejected_original_route",
            )
            compressed = self._compressed_solve(
                problem, profile, strategy, solver_material, solver_system,
                repair_context=repair_context,
                attempt=attempt,
                failure_reason="audit_rejected_original_route",
            )
            if compressed and self._has_complete_solution_sections(compressed):
                self._save_candidate(compressed, source=f"solver_attempt_{attempt}")
                self._record(
                    "compressed_solution_received", attempt=attempt,
                    content_length=len(compressed),
                )
                self._record_solution_steps(compressed, attempt)
                return compressed
            if compressed and extract_staged_answer(compressed).answer is not None:
                extracted = extract_staged_answer(compressed)
                self._save_candidate(compressed, source=f"solver_attempt_{attempt}")
                self._record(
                    "partial_solution_accepted",
                    attempt=attempt,
                    extraction=extracted.reason,
                    content_length=len(compressed),
                )
                return compressed
            self._record(
                "compressed_solution_invalid",
                attempt=attempt,
                reason=self._solver_failure_reason(compressed),
            )
            return None
        call_type = "solver" if attempt == 1 else "solver_repair"
        response = self._call(
            call_type,
            solver_system,
            {},
            max_tokens=int(getattr(self.config, "staged_solver_max_tokens", 8192)),
            max_timeout_seconds=self._normal_solver_timeout_seconds(attempt),
            temperature=(
                float(getattr(self.config, "staged_repair_solver_temperature", 0.35))
                if attempt > 1
                else float(getattr(self.config, "staged_primary_solver_temperature", 0.6))
            ),
            assistant_prefill=_COMPRESSED_PREFILL if compact_by_default else "",
            user_content=solver_prompt,
        )
        content = response.strip() if response else ""
        if content:
            self._last_solver_partial = content
        if compact_by_default and content and not content.startswith("## 问题分析"):
            content = f"{_COMPRESSED_PREFILL}{content.lstrip()}"
        if content and self._has_complete_solution_sections(content):
            self._save_candidate(content, source=f"solver_attempt_{attempt}")
            self._record("complete_solution_received", attempt=attempt, content_length=len(content))
            self._record_solution_steps(content, attempt)
            return content
        # Do not spend another several minutes repairing presentation when the
        # model already supplied a concrete answer.  The audit can still mark
        # the candidate as risky, and a later repair may replace it if it
        # finishes in time.
        if content and extract_staged_answer(content).answer is not None:
            extracted = extract_staged_answer(content)
            self._save_candidate(content, source=f"solver_attempt_{attempt}")
            self._record(
                "partial_solution_accepted",
                attempt=attempt,
                extraction=extracted.reason,
                content_length=len(content),
            )
            return content
        failure_reason = self._solver_failure_reason(content)
        self._record("complete_solution_invalid", attempt=attempt, reason=failure_reason)
        if not self._should_compressed_retry(failure_reason):
            return content or None

        compressed = self._compressed_solve(
            problem, profile, strategy, material, solver_system,
            repair_context=repair_context, attempt=attempt,
            failure_reason=failure_reason,
        )
        if compressed and len(compressed) > len(self._last_solver_partial):
            self._last_solver_partial = compressed
        if compressed and self._has_complete_solution_sections(compressed):
            self._save_candidate(compressed, source=f"solver_attempt_{attempt}")
            self._record(
                "compressed_solution_received", attempt=attempt,
                content_length=len(compressed),
            )
            self._record_solution_steps(compressed, attempt)
            return compressed
        if compressed and extract_staged_answer(compressed).answer is not None:
            self._save_candidate(compressed, source=f"solver_attempt_{attempt}")
        compressed_reason = self._solver_failure_reason(compressed)
        self._record(
            "compressed_solution_invalid", attempt=attempt,
            reason=compressed_reason,
        )
        return None

    def _compressed_solve(
        self,
        problem: str,
        profile: ProblemProfile,
        strategy: StagedStrategy,
        material: str,
        solver_system: str,
        *,
        repair_context: str,
        attempt: int,
        failure_reason: str,
    ) -> str:
        coverage = list(dict.fromkeys([
            *profile.obligations,
            *strategy.proof_obligations,
        ]))
        compact_only = failure_reason == "compact_reasoning_only"
        recovery_instruction = (
            STAGED_COMPACT_SOLVER_INSTRUCTION
            if compact_only else STAGED_COMPRESSED_SOLVER_INSTRUCTION
        )
        recovery_context = (
            f"{recovery_instruction}\n\n"
            f"失败原因：{failure_reason}\n"
            "答案覆盖要求："
            f"{json.dumps(coverage, ensure_ascii=False)}\n"
            "这是本次推理失败后唯一一次压缩救援，不得继续探索或请求再次重试。"
        )
        if attempt > 1:
            recovery_context += (
                "\n【修复强制要求】先逐条回应审查给出的首个致命错误；"
                "必须更换至少一个关键表示、计数编码、构造或验证路线。"
                "不得把‘标准结论’、图形直觉或未展示的枚举当作证明。"
                "即使最终答案与旧稿相同，也必须给出独立的可执行验证，"
                "并明确说明旧稿错误为何不再影响该结论。"
            )
        if compact_only:
            solver_prompt = STAGED_COMPACT_SOLVER_PROMPT.format(
                problem=problem,
                method=strategy.main_method or strategy.backup_method or "从定义建立模型并逐项验证",
                obligations=json.dumps(
                    list(dict.fromkeys([*profile.obligations, *strategy.proof_obligations])),
                    ensure_ascii=False,
                ),
                skill_material=material[:8000] or "（无）",
                strategy_cases=self._solver_strategy_cards or "（无）",
                constraint_ledger=self._constraint_ledger or "（结构化约束台账不可用；逐字以原题为准。）",
                retrieval_summary=self._solver_retrieval_summary(),
                special_requirements=self._build_special_requirements(problem, profile),
                repair_context=repair_context,
                recovery_context=recovery_context,
            )
        else:
            solver_prompt = self._render_solver_prompt(
                problem, profile, strategy, material[:12000],
                repair_context=repair_context,
                recovery_context=recovery_context,
            )
        self._record(
            "compressed_solver_retry_started",
            attempt=attempt,
            failure_reason=failure_reason,
        )
        compact_timeout = float(getattr(
            self.config,
            "staged_primary_compact_timeout_seconds",
            getattr(self.config, "staged_solver_compressed_call_estimate_seconds", 200.0),
        )) if compact_only else float(getattr(
            self.config, "staged_solver_compressed_call_estimate_seconds", 200.0,
        ))
        continuation = self._call(
            "solver_compressed",
            solver_system,
            {},
            max_tokens=int(
                getattr(self.config, "staged_solver_compressed_max_tokens", 8192)
            ),
            max_timeout_seconds=compact_timeout,
            thinking_mode=bool(
                getattr(self.config, "staged_solver_compressed_thinking_mode", False)
            ),
            temperature=float(getattr(
                self.config,
                "staged_repair_solver_temperature" if attempt > 1 else "staged_primary_solver_temperature",
                0.35 if attempt > 1 else 0.2,
            )),
            assistant_prefill=_COMPRESSED_PREFILL,
            user_content=solver_prompt,
        ).strip()
        if continuation and not continuation.startswith("## 问题分析"):
            return f"{_COMPRESSED_PREFILL}{continuation.lstrip()}"
        return continuation

    def _render_solver_prompt(
        self,
        problem: str,
        profile: ProblemProfile,
        strategy: StagedStrategy,
        material: str,
        *,
        repair_context: str = "",
        recovery_context: str = "",
    ) -> str:
        replacements = {
            "problem": problem,
            "profile": json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
            "strategy": json.dumps(strategy.model_dump(), ensure_ascii=False, indent=2),
            "skill_material": material or "（无）",
            "strategy_cases": self._solver_strategy_cards or "（无）",
            "constraint_ledger": self._constraint_ledger or "（结构化约束台账不可用；逐字以原题为准。）",
            "retrieval_summary": self._solver_retrieval_summary(),
            "special_requirements": self._build_special_requirements(problem, profile),
            "repair_context": repair_context,
            "recovery_context": recovery_context,
        }
        rendered = re.sub(
            r"\{(problem|profile|strategy|skill_material|strategy_cases|constraint_ledger|retrieval_summary|special_requirements|repair_context|recovery_context)\}",
            lambda match: replacements[match.group(1)],
            STAGED_SOLVER_PROMPT,
        )
        return rendered.strip()

    def _solver_retrieval_summary(self) -> str:
        """Bound the optional retrieval representation before Solver injection."""
        summary = self._strategy_retrieval_text.strip()
        if not summary:
            return "（无；以原题和题面约束台账为准。）"
        return summary[:4000]

    @staticmethod
    def _build_audit_skill_summary(skills: list[Any]) -> str:
        """Expose selected skill methods to auditors without forwarding examples.

        Auditors need enough context to distinguish a strategy-backed method from
        an unsupported assertion, but raw handbook passages can contain example
        answers.  Keep headings plus explicitly labelled method/pitfall bullets.
        """
        categories = [str(getattr(skill, "category", "")) for skill in skills]
        parts: list[str] = []
        cards = theorem_cards(categories)
        if cards:
            parts.append(cards)
        for skill in skills:
            category = str(getattr(skill, "category", "unknown"))
            lines = str(getattr(skill, "prompt", "")).splitlines()
            headings = [line.strip() for line in lines if re.match(r"^#{1,4}\s+\S", line)]
            labelled = [
                line.strip() for line in lines
                if re.match(r"^\s*[-*]\s*(?:核心内容|解题路线|易错点|考法提示|定理卡片)[：:]", line)
            ]
            summary_lines = (headings[:10] + labelled[:12])
            if summary_lines:
                parts.append(f"【{category} 相关小结】\n" + "\n".join(summary_lines))
        return "\n\n".join(parts)[:6000]

    def _normal_solver_timeout_seconds(self, attempt: int = 1) -> float:
        assert self.state is not None
        compressed_reserve = 0.0
        if getattr(self.config, "staged_solver_compressed_retry_enabled", True):
            compressed_reserve = max(
                0.0,
                float(
                    getattr(
                        self.config,
                        "staged_solver_compressed_call_estimate_seconds",
                        200.0,
                    )
                ),
            )
        available = (
            remaining_seconds(self.state)
            - self.state.finalize_reserve_seconds
            - compressed_reserve
        )
        configured_name = (
            "staged_solver_timeout_seconds"
            if attempt == 1 else "staged_solver_repair_timeout_seconds"
        )
        configured = float(getattr(
            self.config,
            configured_name,
            getattr(self.config, "staged_client_max_wait_seconds", 720.0),
        ))
        return max(0.001, min(configured, available))

    def _solver_failure_reason(self, content: str) -> str:
        if self._last_call_error is not None:
            error_type, message = self._last_call_error
            lowered = f"{error_type} {message}".lower()
            if "timeout" in lowered or "timed out" in lowered:
                return f"network_or_wall_clock_timeout:{error_type}"
            # The injected client wraps transport failures (SSL EOF, broken
            # pipe, connection reset and exhausted HTTP retries) in a generic
            # RuntimeError.  Keep a distinct reason for observability; all
            # failure reasons receive one bounded compressed retry below.
            if any(token in lowered for token in (
                "ssleoferror", "ssl", "connection", "httpsconnectionpool",
                "max retries exceeded", "connection reset", "broken pipe",
                "eof occurred",
            )):
                return f"network_transport_error:{error_type}"
            return f"model_call_failed:{error_type}"
        response = self._last_model_response
        if response is not None and response.reasoning_content and not content.strip():
            return "reasoning_content_exhausted"
        if response is not None and response.finish_reason == "length":
            return "output_length_exhausted"
        return "missing_fixed_sections"

    def _should_compressed_retry(self, failure_reason: str) -> bool:
        # Every failed primary attempt gets exactly one compact recovery.  A
        # failure can be a transport exception, a wrapped RuntimeError, a
        # truncated response, or a protocol/section error; distinguishing
        # these here used to send some failures straight to emergency output.
        # The call site invokes this at most once per solver attempt, and a
        # failed compressed call is never recursively compressed, so this does
        # not create an unbounded retry loop.
        return bool(
            getattr(self.config, "staged_solver_compressed_retry_enabled", True)
            and failure_reason
        )

    @staticmethod
    def _has_complete_solution_sections(content: str) -> bool:
        return all(marker in content for marker in _SOLUTION_SECTIONS)

    def _local_checks(self, problem: str, profile: ProblemProfile, strategy: StagedStrategy, draft: str) -> dict:
        findings: list[str] = []
        ok = True
        if draft.count("## ") != 4:
            ok = False; findings.append("fixed_section_count")
        if re.search(r"显然存在|容易看出|经枚举验证|显然成立", draft) and "关键验证点" not in draft:
            ok = False; findings.append("unsupported_assertion")
        checks = [
            (expression, "requested_check")
            for expression in requested_checks(draft)
        ]
        checks.extend(
            (expression, "numeric_equality")
            for expression in numeric_equalities(draft)
        )
        for expression, source in checks:
            result = check_expression(expression, source=source,
                                      max_steps=int(getattr(self.config, "custom2_text_check_max_steps", 20000)),
                                      timeout=float(getattr(self.config, "custom2_text_check_timeout_seconds", 1.0)))
            findings.append(f"{expression} => {result.result}")
            if result.contradiction:
                ok = False
        if any(item in profile.obligations for item in ("lower_bound", "attaining_construction")):
            if not re.search(r"下界|上界|构造|达到|可达|等号", draft):
                ok = False; findings.append("extremal_obligation_missing")
        if "all_cases" in profile.obligations and not re.search(r"完备|所有|必要性|充分性|无遗漏", draft):
            ok = False; findings.append("completeness_obligation_missing")
        # For quantitative/proof answers, keep the final-answer field
        # formulaic.  Concept/choice/fill-blank questions are exempt because
        # their accepted answers can legitimately be Chinese terminology.
        if profile.answer_mode not in {"choice", "judgment", "fill_blank", "proof"}:
            final_match = re.search(
                r"^\s*##\s*最终答案\s*$([\s\S]*?)(?=^\s*##\s+|\Z)",
                draft,
                re.MULTILINE,
            )
            final_text = final_match.group(1).strip() if final_match else ""
            if re.search(r"[\u3400-\u9fff]", final_text):
                ok = False
                findings.append("non_concept_final_answer_contains_chinese")
        final_match = re.search(
            r"^\s*##\s*最终答案\s*$([\s\S]*?)(?=^\s*##\s+|\Z)",
            draft,
            re.MULTILINE,
        )
        if final_match and len(re.findall(r"\\boxed\s*\{", final_match.group(1))) > 1:
            ok = False
            findings.append("multiple_final_candidates")
        return {"ok": ok, "summary": findings[:12]}

    def _model_fidelity(self, problem: str, draft: str,
                        strategy: StagedStrategy | None = None) -> StagedModelFidelity:
        """Reject only explicit rewrites that solve a different problem.

        This is intentionally permissive: it is not a proof-completeness or
        numerical-correctness gate.  Compatible alternate models proceed to the
        targeted audit rather than triggering a destructive repair loop.
        """
        if not bool(getattr(self.config, "staged_model_fidelity_enabled", True)):
            self._record("model_fidelity_skipped", reason="disabled")
            return StagedModelFidelity()
        if not self._constraint_ledger:
            self._record("model_fidelity_skipped", reason="constraint_ledger_unavailable")
            return StagedModelFidelity()
        if self._convergence_due():
            self._record("model_fidelity_skipped", reason="convergence_deadline_reached")
            return StagedModelFidelity()
        payload = {
            "problem": problem,
            "constraint_ledger": self._constraint_ledger,
            # Preserve the audit boundary: the fidelity pass receives the
            # planner's normalized commitments, never retrieved example text.
            "strategy": (strategy or StagedStrategy()).model_dump(),
            "retrieval_strategy_summary": self._planner_strategy_cards or "（无）",
            "related_skill_summary": self._audit_skill_summary or "（无）",
            "special_requirements": self._build_special_requirements(problem, ProblemProfile()),
            "solution": draft,
        }
        data = self._structured("model_fidelity", STAGED_MODEL_FIDELITY_PROMPT, payload)
        if data is None and bool(getattr(
                self.config, "staged_model_fidelity_thinking_mode", True)):
            # A timeout, transport failure, or malformed first response should
            # not consume the fidelity gate entirely. Retry once without
            # thinking, using the small control-output budget.
            self._record("model_fidelity_retry_without_thinking", reason="no_valid_json")
            data = self._structured(
                "model_fidelity", STAGED_MODEL_FIDELITY_PROMPT, payload,
                thinking_mode=False,
            )
        data = self._normalize_audit_payload(data, call_type="model_fidelity")
        if data is None:
            data = self._retry_audit_after_parse_failure(
                call_type="model_fidelity",
                system=STAGED_MODEL_FIDELITY_PROMPT,
                payload=payload,
                rejection_reason="No JSON object could be extracted from the prior response.",
            )
            data = self._normalize_audit_payload(data, call_type="model_fidelity")
        try:
            fidelity = StagedModelFidelity.model_validate(data or {})
        except Exception as exc:
            data = self._retry_audit_after_parse_failure(
                call_type="model_fidelity",
                system=STAGED_MODEL_FIDELITY_PROMPT,
                payload=payload,
                rejection_reason=str(exc),
            )
            data = self._normalize_audit_payload(data, call_type="model_fidelity")
            try:
                fidelity = StagedModelFidelity.model_validate(data or {})
            except Exception:
                return StagedModelFidelity(
                    verdict="uncertain",
                    first_fatal_error="建模保真审查输出无法解析。",
                )
        try:
            if fidelity.verdict == "fail" and not (
                fidelity.first_fatal_error.strip()
                and fidelity.source_constraint.strip()
                and fidelity.solver_claim.strip()
            ):
                return StagedModelFidelity(
                    verdict="uncertain",
                    first_fatal_error="建模保真审查未提供可核对的冲突证据。",
                )
            if fidelity.verdict == "fail" and not self._fidelity_claim_is_quoted(
                    draft, fidelity.solver_claim):
                return StagedModelFidelity(
                    verdict="uncertain",
                    first_fatal_error=(
                        "建模保真审查声称的 Solver 断言未在草稿中逐字出现，"
                        "不能据此否决当前解答。"
                    ),
                )
            return fidelity
        except Exception:
            return StagedModelFidelity(
                verdict="uncertain",
                first_fatal_error="建模保真审查输出无法解析。",
            )

    @staticmethod
    def _fidelity_claim_is_quoted(draft: str, claim: str) -> bool:
        """Require a fidelity failure to cite the Solver rather than paraphrase it.

        A model-direction audit that translates or invents a solver assertion can
        reverse a sign that the draft already handled correctly.  Whitespace is
        irrelevant, but all remaining characters must occur in the draft.
        """
        normalized_draft = re.sub(r"\s+", "", str(draft or ""))
        normalized_claim = re.sub(r"\s+", "", str(claim or ""))
        return bool(normalized_claim) and normalized_claim in normalized_draft

    @staticmethod
    def _fidelity_failure_as_audit(fidelity: StagedModelFidelity) -> StagedAudit:
        """Feed a concrete model mismatch into the existing repair protocol."""
        return StagedAudit(
            verdict="fail",
            error_type="model",
            first_fatal_error=fidelity.first_fatal_error,
            invalid_claim=fidelity.solver_claim,
            evidence=fidelity.source_constraint,
            counterexample_or_evidence=fidelity.affected_reasoning,
            required_changes=[
                *fidelity.required_changes,
                "逐条保留题面约束台账后重新建立数学模型",
            ],
            forbidden_reuse=[fidelity.solver_claim],
            replacement_route="从题面允许的状态和转移重新编码，再完成后续推导。",
            repair_instruction=(
                "不得沿用与题面约束冲突的模型；先修正边、转移、边界或端点定义，"
                "再重新计数或证明。"
            ),
            additional_errors=list(fidelity.additional_errors),
        )

    def _audit(self, problem: str, profile: ProblemProfile, strategy: StagedStrategy,
               draft: str, checks: dict) -> StagedAudit:
        payload = {
            "problem": problem, "profile": profile.model_dump(), "strategy": strategy.model_dump(),
            # Planner cards deliberately exclude reference problem/solution.
            # Skill context is a bounded method summary, not the raw handbook.
            "retrieval_strategy_summary": self._planner_strategy_cards or "（无）",
            "related_skill_summary": self._audit_skill_summary or "（无）",
            "solution": draft, "local_checks": checks,
            "special_requirements": self._build_special_requirements(problem, profile),
        }
        data = self._structured("targeted_audit", STAGED_AUDIT_PROMPT, payload)
        data = self._normalize_audit_payload(data, call_type="targeted_audit")
        if data is None:
            data = self._retry_audit_after_parse_failure(
                call_type="targeted_audit",
                system=STAGED_AUDIT_PROMPT,
                payload=payload,
                rejection_reason="No JSON object could be extracted from the prior response.",
            )
            data = self._normalize_audit_payload(data, call_type="targeted_audit")
        try:
            audit = StagedAudit.model_validate(data or {})
        except Exception as exc:
            data = self._retry_audit_after_parse_failure(
                call_type="targeted_audit",
                system=STAGED_AUDIT_PROMPT,
                payload=payload,
                rejection_reason=str(exc),
            )
            data = self._normalize_audit_payload(data, call_type="targeted_audit")
            try:
                audit = StagedAudit.model_validate(data or {})
            except Exception:
                return StagedAudit(verdict="uncertain", evidence="审查输出无法解析")
        try:
            # A targeted-audit failure starts a costly, destructive repair loop.
            # Do not accept an auditor's paraphrase as evidence: it must point at
            # an actual Solver statement and supply evidence plus an executable fix.
            if audit.verdict == "fail":
                if not (
                    audit.invalid_claim.strip()
                    and self._fidelity_claim_is_quoted(draft, audit.invalid_claim)
                    and (audit.evidence.strip() or audit.counterexample_or_evidence.strip())
                    and audit.required_changes
                ):
                    return StagedAudit(
                        verdict="uncertain",
                        evidence=(
                            "定向审查的 fail 未提供草稿原文、可核验证据和可执行修复的完整证据链；"
                            "不触发重解。"
                        ),
                        unmet_obligations=[
                            "审查器需引用草稿原命题，并给出题面证据、反例或逐步复算。"
                        ],
                    )
            if audit.verdict == "fail" and not audit.first_fatal_error.strip():
                fallback = (
                    audit.invalid_claim
                    or audit.counterexample_or_evidence
                    or audit.evidence
                    or audit.repair_instruction
                )
                if fallback:
                    audit = audit.model_copy(update={"first_fatal_error": fallback})
            return audit
        except Exception:
            return StagedAudit(verdict="uncertain", evidence="审查输出无法解析")

    def _normalize_audit_payload(
        self, data: dict[str, Any] | None, *, call_type: str,
    ) -> dict[str, Any] | None:
        """Recover harmless audit JSON shape drift without weakening evidence gates.

        The audit roles sometimes serialize a one-item list as a string.  A
        schema failure would otherwise discard an independently supported
        failure report before it reaches repair.  Only optional/list shape is
        normalized here: ``verdict``, root evidence, and the later quotation
        and evidence-chain checks remain strict.
        """
        if not isinstance(data, Mapping):
            return data

        payload = dict(data)
        adjustments: list[str] = []
        list_fields = (
            "unmet_obligations", "required_changes", "forbidden_reuse",
        )
        text_fields = (
            "first_fatal_error", "source_constraint", "solver_claim",
            "affected_reasoning", "evidence", "invalid_claim",
            "counterexample_or_evidence", "repair_instruction",
            "error_type", "replacement_route",
        )

        def normalize_list(container: dict[str, Any], field: str, label: str) -> None:
            value = container.get(field)
            if value is None:
                container[field] = []
                adjustments.append(f"{label}:null_to_empty_list")
            elif isinstance(value, str):
                container[field] = [value] if value.strip() else []
                adjustments.append(f"{label}:string_to_list")
            elif isinstance(value, tuple):
                container[field] = list(value)
                adjustments.append(f"{label}:tuple_to_list")
            elif isinstance(value, list) and len(value) > 12:
                container[field] = value[:12]
                adjustments.append(f"{label}:truncated_to_12")

        for field in list_fields:
            if field in payload:
                normalize_list(payload, field, field)
        for field in text_fields:
            if field in payload and payload[field] is None:
                payload[field] = ""
                adjustments.append(f"{field}:null_to_empty_string")

        if "additional_errors" in payload:
            raw_issues = payload["additional_errors"]
            if raw_issues is None:
                issues: list[Any] = []
                adjustments.append("additional_errors:null_to_empty_list")
            elif isinstance(raw_issues, Mapping):
                issues = [raw_issues]
                adjustments.append("additional_errors:object_to_list")
            elif isinstance(raw_issues, list):
                issues = raw_issues[:12]
                if len(raw_issues) > 12:
                    adjustments.append("additional_errors:truncated_to_12")
            else:
                issues = []
                adjustments.append("additional_errors:invalid_value_dropped")

            normalized_issues: list[dict[str, Any]] = []
            for index, issue in enumerate(issues):
                if not isinstance(issue, Mapping):
                    adjustments.append(f"additional_errors[{index}]:invalid_item_dropped")
                    continue
                normalized_issue = dict(issue)
                for field in ("required_changes", "forbidden_reuse"):
                    if field in normalized_issue:
                        normalize_list(
                            normalized_issue, field, f"additional_errors[{index}].{field}",
                        )
                for field in (
                    "error_type", "invalid_claim", "evidence",
                    "affected_reasoning", "prevention_rule",
                ):
                    if field in normalized_issue and normalized_issue[field] is None:
                        normalized_issue[field] = ""
                        adjustments.append(
                            f"additional_errors[{index}].{field}:null_to_empty_string"
                        )
                normalized_issues.append(normalized_issue)
            payload["additional_errors"] = normalized_issues

        if adjustments:
            self._record(
                "audit_payload_normalized", call_type=call_type,
                adjustments=adjustments[:24],
            )
        return payload

    def _retry_audit_after_parse_failure(
        self,
        *,
        call_type: str,
        system: str,
        payload: dict[str, Any],
        rejection_reason: str,
    ) -> dict[str, Any] | None:
        """Regenerate one structured audit with its prior rejection context.

        This is deliberately a full re-audit rather than an unsafe local
        coercion of unknown fields.  The retry sees the original task payload,
        prior response, and the schema rejection reason, but must still apply
        the same source/quotation/evidence rules from its system prompt.
        """
        previous = self._last_structured_response.strip()
        if not previous:
            self._record(
                "audit_parse_retry_skipped", call_type=call_type,
                reason="empty_previous_response",
            )
            return None
        if len(previous) > 24000:
            previous = f"{previous[:12000]}\n...[truncated]...\n{previous[-12000:]}"
        retry_payload = {
            **payload,
            "previous_audit_output": previous,
            "previous_output_rejection": rejection_reason[:2000],
        }
        self._record(
            "audit_parse_retry_started", call_type=call_type,
            rejection_reason=rejection_reason[:300],
        )
        response = self._call(
            "audit_parse_retry",
            system,
            retry_payload,
            max_tokens=int(getattr(self.config, "staged_audit_retry_max_tokens", 4096)),
            max_timeout_seconds=float(getattr(
                self.config, "staged_audit_retry_timeout_seconds", 60.0,
            )),
            thinking_mode=False,
            temperature=0.0,
        )
        data = extract_json_object(response or "")
        self._record(
            "audit_parse_retry_completed", call_type=call_type,
            parsed=isinstance(data, dict),
        )
        return data if isinstance(data, dict) else None

    def _structured(self, call_type: str, system: str, payload: dict, *,
                    thinking_mode: bool | None = None) -> dict | None:
        default_tokens = {
            "classifier": getattr(self.config, "staged_classifier_max_tokens", 4096),
            "strategy": getattr(self.config, "staged_strategy_max_tokens", 4096),
            "model_fidelity": getattr(self.config, "staged_model_fidelity_max_tokens", 4096),
            "targeted_audit": getattr(self.config, "staged_targeted_audit_max_tokens", 8192),
        }.get(call_type, 8192)
        timeout_name = {
            "classifier": "staged_classifier_timeout_seconds",
            "strategy": "staged_strategy_timeout_seconds",
            "model_fidelity": "staged_model_fidelity_timeout_seconds",
            "targeted_audit": "staged_targeted_audit_timeout_seconds",
        }.get(call_type)
        timeout = (
            float(getattr(self.config, timeout_name))
            if timeout_name is not None else None
        )
        response = self._call(
            call_type, system, payload,
            max_tokens=int(default_tokens), max_timeout_seconds=timeout,
            thinking_mode=thinking_mode,
            temperature=(
                float(getattr(self.config, "staged_strategy_temperature", 0.3))
                if call_type == "strategy" else None
            ),
        )
        self._last_structured_response = response or ""
        data = extract_json_object(response or "")
        return data if isinstance(data, dict) else None

    def _call(self, call_type: str, system: str, payload: dict, *, max_tokens: int,
              allow_finalize: bool = False, max_timeout_seconds: float | None = None,
              thinking_mode: bool | None = None, temperature: float | None = None,
              assistant_prefill: str = "",
              user_content: str | None = None,
              messages_override: list[dict[str, str]] | None = None) -> str:
        assert self.state is not None
        self.state.model_call_count += 1
        self._last_call_error = None
        self._last_model_response = None
        thinking_defaults = {
            "classifier": getattr(self.config, "staged_classifier_thinking_mode", False),
            "strategy_retrieval": getattr(self.config, "staged_strategy_retrieval_thinking_mode", False),
            "strategy": getattr(self.config, "staged_strategy_thinking_mode", False),
            "solver": getattr(self.config, "staged_solver_thinking_mode", False),
            "solver_repair": getattr(
                self.config, "staged_solver_repair_thinking_mode", True
            ),
            "solver_compressed": getattr(self.config, "staged_solver_compressed_thinking_mode", False),
            "model_fidelity": getattr(self.config, "staged_model_fidelity_thinking_mode", False),
            "targeted_audit": getattr(self.config, "staged_targeted_audit_thinking_mode", False),
            "emergency_integrator": getattr(self.config, "staged_emergency_thinking_mode", False),
            "emergency_direct_solver": getattr(self.config, "staged_emergency_thinking_mode", False),
            "final_arbitrator": getattr(self.config, "staged_emergency_thinking_mode", False),
        }
        effective_thinking_mode = (
            bool(thinking_defaults.get(call_type, False))
            if thinking_mode is None else bool(thinking_mode)
        )
        if effective_thinking_mode:
            # Reasoning-enabled Intern calls need enough completion budget for
            # both internal deliberation and the visible answer.  Normalize at
            # this single gateway so every staged role receives the same ceiling.
            max_tokens = self._thinking_max_tokens()
            if call_type == "model_fidelity":
                max_tokens = min(
                    max_tokens,
                    max(1, int(getattr(
                        self.config,
                        "staged_model_fidelity_thinking_max_tokens",
                        65536,
                    ))),
                )
        messages = messages_override or [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    json.dumps(payload, ensure_ascii=False)
                    if user_content is None else user_content
                ),
            },
        ]
        if assistant_prefill:
            messages.append({"role": "assistant", "content": assistant_prefill})
        if temperature is None:
            if call_type == "strategy":
                temperature = float(getattr(self.config, "staged_strategy_temperature", 0.3))
            elif call_type in {"solver", "solver_repair", "solver_compressed"}:
                temperature = 0.2
            else:
                temperature = 0.0
        try:
            response = call_model(self.client, self.state, self.debug_trace, call_type,
                                  allow_finalize_reserve=allow_finalize,
                                  max_timeout_seconds=(
                                      float(getattr(self.config, "staged_client_max_wait_seconds", 720.0))
                                      if max_timeout_seconds is None else max_timeout_seconds
                                  ),
                                  messages=messages,
                                  temperature=temperature,
                                  thinking_mode=effective_thinking_mode,
                                  max_tokens=max_tokens)
            self._last_model_response = response
            return response.content
        except Exception as exc:
            self._last_call_error = (type(exc).__name__, str(exc)[:1000])
            self._record("model_call_failed", call_type=call_type, error_type=type(exc).__name__)
            return ""

    def _thinking_max_tokens(self) -> int:
        """Return the shared maximum budget for every thinking-enabled stage."""
        configured = (
            getattr(self.config, "custom2_solver_max_tokens", 131072),
            getattr(self.config, "staged_solver_compressed_max_tokens", 131072),
            getattr(self.config, "staged_solver_max_tokens", 8192),
            getattr(self.config, "staged_classifier_max_tokens", 8192),
            getattr(self.config, "staged_strategy_max_tokens", 8192),
            getattr(self.config, "staged_strategy_retrieval_max_tokens", 512),
            getattr(self.config, "staged_targeted_audit_max_tokens", 8192),
            getattr(self.config, "staged_model_fidelity_max_tokens", 4096),
            getattr(self.config, "staged_emergency_max_tokens", 8192),
        )
        return max(1, *(int(value) for value in configured))

    def _record(self, event: str, **data: Any) -> None:
        self.trace.append({"type": event, "time": time.time(), "data": data})

    def _result(self, answer: str) -> dict:
        solve_status = "success"
        if answer.strip() == "无法确定唯一答案":
            timed_out = any(
                item.get("type") == "model_call_error"
                and "timeout" in (
                    str(item.get("error_type", "")) + " " + str(item.get("content", ""))
                ).lower()
                for item in self.debug_trace
            )
            solve_status = "timeout" if timed_out else "failed"
        return {
            "final_response": answer,
            "solve_status": solve_status,
            "trace": self.trace,
            "debug_trace": self.debug_trace,
        }
