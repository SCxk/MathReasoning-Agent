import json
import hashlib
import re
import time
from typing import Any

from pydantic import ValidationError

from reasoning_agent.custom.parsers.json_parser import extract_json_object, make_json_safe
from reasoning_agent.prompt_utils import build_invalid_json_retry_message
from reasoning_agent.custom2.context import (
    build_finalizer_messages,
    build_repair_messages,
    build_solver_messages,
)
from reasoning_agent.custom2.models import (
    AcceptedClaim,
    AgentState,
    ErrorRecord,
    ProblemFact,
    SolutionDraftState,
    StrategyGuidance,
    Task,
)
from reasoning_agent.custom2.model_call import (
    ModelCallBudgetExhausted,
    ModelCallTimedOut,
    call_model,
)
from reasoning_agent.custom2.prompts import (
    DOMAIN_CLASSIFIER_SYSTEM_PROMPT,
    FORMALIZER_SYSTEM_PROMPT,
    REPLANNER_SYSTEM_PROMPT,
    STRATEGY_PREPROCESS_SYSTEM_PROMPT,
)
from reasoning_agent.custom2.schemas import (
    CheckItem,
    CandidateVerification,
    DomainClassificationOutput,
    FinalAnswer,
    CritiqueOutput,
    FormalizationOutput,
    ReplanOutput,
    ReasoningStep,
    StepVerification,
    StrategyOutput,
)
from reasoning_agent.custom2.strategy_skills import (
    ALLOWED_SKILL_CATEGORIES,
    SelectedStrategySkill,
    normalize_skill_category,
    select_strategy_skills,
)
from reasoning_agent.custom2.storage import RuntimeLogger
from reasoning_agent.custom2.state_manager import (
    apply_candidate_set_verification,
    apply_candidate_verification,
    activate_task,
    can_finalize,
    can_finalize_best_effort,
    accepted_claim_closure,
    candidate_conflict_groups,
    commit_formalization,
    commit_step,
    choose_active_task,
    choose_open_task,
    ensure_tasks_from_tasks,
    initialize_state,
    has_candidate_conflict,
    maybe_replan_from_requirements,
    next_task_id,
    next_error_id,
    pending_required_tasks,
    reasoning_step_to_solution_draft,
    remaining_seconds,
    record_replan,
    record_protocol_failure,
    register_candidate,
    reject_step,
    restore_active_task,
    route,
    time_phase,
    validate_reasoning_step_protocol,
    validate_state_invariants,
)
from reasoning_agent.custom2.verifier import (
    CandidateSetVerifier,
    CandidateVerifier,
    DraftCritic,
    FormalizationVerifier,
    StepVerifier,
)


class RuntimeResult:
    def __init__(
        self,
        final_response: str,
        trace: list[dict],
        debug_trace: list[dict],
        state: AgentState,
    ) -> None:
        self.final_response = final_response
        self.trace = _prepend_structured_trace(trace, state, final_response)
        self.debug_trace = debug_trace
        self.state = state


def _prepend_structured_trace(trace: list[dict], state: AgentState, final_response: str) -> list[dict]:
    events = trace
    classification = next((item for item in events if item.get("type") == "domain_classification_committed"), {})
    strategy = next((item for item in events if item.get("type") == "strategy_preprocess_committed"), {})
    drafts = [item for item in events if item.get("type") == "draft_proposed"]
    reviews = [item for item in events if item.get("type") in {"critique_completed", "candidate_verified"}]
    final = next((item for item in reversed(events) if item.get("type") == "final"), {})
    reasoning = {
        "type": "stage_summary",
        "step": "reasoning",
        "attempts": len(drafts),
        "answer": str(final_response or ""),
        "steps_count": len(drafts),
        "tasks": [
            {"task_id": item.get("task_id"), "version": item.get("version"),
             "claim_count": item.get("claim_count"), "candidate_count": item.get("candidate_count")}
            for item in drafts
        ],
        "validation_points": [
            {"type": item.get("type"), "task_id": item.get("task_id"),
             "verdict": item.get("verdict"), "reason": item.get("reason", "")[:1000]}
            for item in reviews
        ],
    }
    stages = [
        {"type": "stage_summary", "step": "classification", "category": classification.get("primary_category", state.problem_type),
         "secondary_categories": classification.get("secondary_categories", state.secondary_problem_types),
         "confidence": classification.get("confidence", state.classification_confidence),
         "selected_skill_ids": classification.get("selected_skill_ids", state.selected_skill_ids)},
        {"type": "stage_summary", "step": "strategy", "execution_mode": strategy.get("execution_mode", state.execution_mode),
         "problem_type": strategy.get("problem_type", state.problem_type),
         "selected_skill_ids": strategy.get("selected_skill_ids", state.selected_skill_ids),
         "task_update": strategy.get("task_update", {})},
        reasoning,
        {"type": "stage_summary", "step": "validation", "status": "accepted" if any(item.get("type") == "candidate_verified" and item.get("verdict") == "accept" for item in events) else "uncertain",
         "validated_answer": final_response, "reviews": reasoning["validation_points"]},
        {"type": "stage_summary", "step": "coordination", "final_response": final_response,
         "finalize_mode": final.get("mode", state.finalize_mode), "finalize_reason": final.get("reason", state.finalize_reason)},
        {"type": "stage_summary", "step": "timing", "model_call_count": state.model_call_count,
         "solver_call_count": state.solver_call_count,
         "elapsed_seconds": max(0.0, time.monotonic() - state.started_at) if state.started_at else 0.0,
         "remaining_seconds": remaining_seconds(state) if state.efficient_runtime else None},
    ]
    return events + stages


class ReasoningRuntime:
    def __init__(self, client: Any, config: Any | None = None) -> None:
        self.client = client
        self.config = config
        self.formalization_verifier = FormalizationVerifier()
        self.step_verifier = StepVerifier(client=client)
        self.candidate_verifier = CandidateVerifier(client=client)
        self.candidate_set_verifier = CandidateSetVerifier(client=client)
        self.draft_critic = DraftCritic(client=client)
        self.last_solver_invalid: dict[str, str] = {}
        self.solver_raw_responses: list[str] = []
        self.solver_history_messages: list[dict] = []
        self.selected_strategy_skills: list[SelectedStrategySkill] = []

    def run(self, problem: str, metadata: dict | None = None) -> RuntimeResult:
        state = initialize_state(problem)
        state.efficient_runtime = bool(
            getattr(self.config, "custom2_efficient_runtime", False)
        )
        if state.efficient_runtime:
            state.started_at = time.monotonic()
            state.deadline_at = state.started_at + float(
                getattr(self.config, "custom2_total_budget_seconds", 1200.0)
            )
            state.finalize_reserve_seconds = float(
                getattr(self.config, "custom2_finalize_reserve_seconds", 120.0)
            )
            state.convergence_reserve_seconds = max(
                state.finalize_reserve_seconds,
                float(
                    getattr(
                        self.config, "custom2_convergence_reserve_seconds", 360.0
                    )
                ),
            )
            state.max_repairs = int(
                getattr(self.config, "custom2_max_repairs", 1)
            )
            state.max_model_replans = int(
                getattr(self.config, "custom2_max_model_replans", 2)
            )
            state.max_solver_calls = int(
                getattr(self.config, "custom2_max_solver_calls", 8)
            )
            state.solver_context_max_chars = int(
                getattr(self.config, "custom2_solver_context_max_chars", 24000)
            )
        self.solver_history_messages = [] if state.efficient_runtime else [
            {"role": "user", "content": f"请解决下面的数学题：\n{problem}"}
        ]
        trace: list[dict] = []
        debug_trace: list[dict] = []
        logger = RuntimeLogger.from_env(metadata)
        logger.write_config(problem=problem, metadata=metadata, config=self.config)
        if logger.enabled:
            self._record(
                trace,
                logger,
                state,
                "runtime_started",
                {"logging_enabled": True},
            )

        self._formalize(state, trace, debug_trace, logger)
        self._strategy_preprocess(
            state,
            trace,
            debug_trace,
            logger,
            metadata,
            self.selected_strategy_skills,
        )

        if state.efficient_runtime:
            return self._run_efficient(state, trace, debug_trace, logger)

        while True:
            invariants = validate_state_invariants(state)
            if invariants:
                state.phase = "incomplete"
                self._record(
                    trace,
                    logger,
                    state,
                    "invariant_violation",
                    {"errors": invariants},
                )
                return self._incomplete(
                    state, trace, debug_trace, "state invariant violation", logger
                )

            action = route(state)
            self._record(trace, logger, state, "route", {"action": action})

            if action == "incomplete":
                state.phase = "incomplete"
                return self._emergency_finalize(
                    state,
                    trace,
                    debug_trace,
                    "reasoning budget exhausted",
                    logger,
                )

            if action == "candidate_verify":
                state.phase = "candidate_verify"
                candidate = next(c for c in state.candidates if c.status == "candidate")
                verification = self.candidate_verifier.verify(
                    state, candidate, debug_trace
                )
                apply_candidate_verification(state, candidate, verification)
                self._record(
                    trace,
                    logger,
                    state,
                    "candidate_verified",
                    {
                        "candidate_id": candidate.id,
                        "verdict": verification.verdict,
                        "reason": verification.reason,
                    },
                )
                continue

            if action == "finalize":
                state.phase = "finalize"
                self._record(trace, logger, state, "finalize_started", {})
                answer = self._finalize(state, debug_trace)
                if can_finalize(state) and answer.answer.strip():
                    state.phase = "done"
                    self._record(trace, logger, state, "final", {"data": answer.model_dump()})
                    result = RuntimeResult(
                        final_response=answer.answer,
                        trace=make_json_safe(trace),
                        debug_trace=make_json_safe(debug_trace),
                        state=state,
                    )
                    logger.write_final(result.final_response, result.trace, state)
                    return result
                record_replan(
                    state,
                    trigger="finalizer_failed",
                    reason="CompletionRequirement 已满足但 finalizer 未返回可用答案。",
                    new_tasks=[
                        Task(
                            id=next_task_id(state),
                            kind="finalize",
                            objective="重新整理 verified evidence 和 satisfied requirements 生成最终答案",
                            priority=120,
                            created_by="runtime",
                        )
                    ],
                )
                self._record(
                    trace,
                    logger,
                    state,
                    "replan_triggered",
                    {"trigger": "finalizer_failed"},
                )
                state.phase = "incomplete"
                return self._emergency_finalize(
                    state,
                    trace,
                    debug_trace,
                    "finalizer failed",
                    logger,
                )

            state.phase = "solve"
            ensure_tasks_from_tasks(state)
            current_task = choose_active_task(state) or choose_open_task(state)
            if current_task is None:
                candidate_task = _maybe_add_candidate_extraction_task(state)
                if candidate_task is not None:
                    ensure_tasks_from_tasks(state)
                    self._record(
                        trace,
                        logger,
                        state,
                        "candidate_extraction_task_added",
                        {
                            "task_id": candidate_task.id,
                            "statement": candidate_task.objective,
                        },
                    )
                    continue
                if maybe_replan_from_requirements(state, "no_executable_task"):
                    self._record(
                        trace,
                        logger,
                        state,
                        "replan_triggered",
                        {"trigger": "no_executable_task"},
                    )
                    continue
                state.phase = "incomplete"
                return self._incomplete(
                    state, trace, debug_trace, "no executable task", logger
                )
            activate_task(current_task)
            self._record(
                trace,
                logger,
                state,
                "solve_started",
                {"task_id": current_task.id, "objective": current_task.objective},
            )

            step = self._solve_step(state, debug_trace, current_task)
            if step is None:
                protocol_failure_count = current_task.protocol_failures + 1
                protocol_reason = (
                    f"当前 Task 连续协议失败 {protocol_failure_count} 次，准备换路。"
                )
                protocol_blocked = record_protocol_failure(
                    state,
                    current_task,
                    reason=protocol_reason,
                    error_id=f"PROTO{protocol_failure_count}",
                    trigger="task_protocol_failure",
                )
                restore_active_task(current_task)
                invalid = dict(self.last_solver_invalid)
                if invalid.get("kind") != "chat_error":
                    retry_message = _build_json_retry_message(
                        invalid.get(
                            "error",
                            "Solver response was not valid ReasoningStep JSON.",
                        ),
                        invalid.get("response_excerpt", ""),
                        current_task.id,
                    )
                    self.solver_history_messages.append(
                        {"role": "user", "content": retry_message}
                    )
                self._record(
                    trace,
                    logger,
                    state,
                    "solver_chat_error"
                    if invalid.get("kind") == "chat_error"
                    else "solver_invalid_response",
                    {
                        "task_id": current_task.id,
                        "error": invalid.get("error", ""),
                        "response_excerpt": invalid.get("response_excerpt", ""),
                    },
                )
                if protocol_blocked:
                    self._record(
                        trace,
                        logger,
                        state,
                        "task_blocked",
                        {
                            "task_id": current_task.id,
                            "reason": current_task.blocked_reason,
                            "protocol_failures": current_task.protocol_failures,
                        },
                    )
                    state.phase = "incomplete"
                    return self._emergency_finalize(
                        state,
                        trace,
                        debug_trace,
                        "solver protocol retries exhausted",
                        logger,
                    )
                if state.solver_call_count >= state.max_solver_calls:
                    state.phase = "incomplete"
                    return self._emergency_finalize(
                        state,
                        trace,
                        debug_trace,
                        "solver returned invalid JSON",
                        logger,
                    )
                continue

            state.phase = "verify"
            self._record(
                trace,
                logger,
                state,
                    "step_proposed",
                    {
                        "current_task": step.current_task,
                        "step_summary": step.step_summary,
                    "new_definitions": len(step.new_definitions),
                    "new_results": len(step.new_results),
                    "candidate_answers": len(step.candidate_answers),
                    "closed_tasks": step.closed_tasks,
                    "request_finalization": step.request_finalization,
                    },
                )
            if step.current_task != current_task.id:
                verification = StepVerification(
                    verdict="reject",
                    dependency_validity=CheckItem(
                        passed=False,
                        reason=(
                            f"Solver returned current_task={step.current_task}, "
                            f"but Runtime selected {current_task.id}"
                        ),
                    ),
                    reason="Solver current_task 与 Runtime 选中的 Task 不一致。",
                    retry_instruction="只推进 prompt 中 Current Task 指定的 task ID。",
                    error_category="dependency_error",
                )
            else:
                verification = self.step_verifier.verify(state, step, debug_trace)
            if verification.verdict == "accept":
                commit_step(state, step, verification)
                self.solver_history_messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(step.model_dump(), ensure_ascii=False),
                    }
                )
                self._record(
                    trace,
                    logger,
                    state,
                    "step_committed",
                    {
                        "step_summary": step.step_summary,
                        "verification": verification.model_dump(),
                    },
                )
            else:
                restore_active_task(current_task)
                reject_step(state, step, verification)
                self._record(
                    trace,
                    logger,
                    state,
                    "step_rejected",
                    {
                        "step_summary": step.step_summary,
                        "verification": verification.model_dump(),
                    },
                )
                if current_task.status == "blocked":
                    replan_record = self._replan_blocked_task(
                        state,
                        current_task,
                        verification,
                        debug_trace,
                    )
                    self._record(
                        trace,
                        logger,
                        state,
                        "replan_triggered",
                        {
                            "trigger": replan_record.trigger,
                            "task_id": current_task.id,
                            "new_tasks": replan_record.new_tasks,
                            "reason": replan_record.reason,
                        },
                    )

    def _run_efficient(
        self,
        state: AgentState,
        trace: list[dict],
        debug_trace: list[dict],
        logger: RuntimeLogger,
    ) -> RuntimeResult:
        self._record(
            trace,
            logger,
            state,
            "execution_mode_selected",
            {"execution_mode": state.execution_mode},
        )
        while True:
            invariants = validate_state_invariants(state)
            if invariants:
                self._record(
                    trace, logger, state, "invariant_violation", {"errors": invariants}
                )
                return self._finish_efficient(
                    state, trace, debug_trace, logger, "state invariant violation"
                )

            budget_phase = time_phase(state)
            if (
                budget_phase == "final_reserve"
                or state.solver_call_count >= state.max_solver_calls
            ):
                reason = (
                    "final reserve reached"
                    if budget_phase == "final_reserve"
                    else "solver call budget reached"
                )
                return self._finish_efficient(
                    state, trace, debug_trace, logger, reason
                )

            current_task = choose_active_task(state) or choose_open_task(state)
            if current_task is None:
                if self._queue_candidate_extraction_task(
                    state, trace, logger
                ):
                    continue
                return self._finish_efficient(
                    state, trace, debug_trace, logger, "no executable macro task"
                )
            if current_task.status != "active":
                activate_task(current_task)
            self._record(
                trace,
                logger,
                state,
                "macro_task_started",
                {"task_id": current_task.id, "objective": current_task.objective},
            )

            state.phase = "solve"
            step = self._solve_step(state, debug_trace, current_task)
            if step is None:
                current_task.protocol_failures += 1
                current_task.status = "open"
                self._record(
                    trace,
                    logger,
                    state,
                    "solver_invalid_response",
                    {
                        "task_id": current_task.id,
                        "error": self.last_solver_invalid.get("error", ""),
                        "protocol_failures": current_task.protocol_failures,
                    },
                )
                if current_task.protocol_failures >= 2:
                    current_task.status = "blocked"
                    self._record(
                        trace,
                        logger,
                        state,
                        "protocol_repair_exhausted",
                        {
                            "task_id": current_task.id,
                            "reason": "Solver 原始输出及专用 JSON repair 均无法解析。",
                        },
                    )
                    return self._finish_efficient(
                        state, trace, debug_trace, logger, "protocol retries exhausted"
                    )
                continue

            protocol_errors = validate_reasoning_step_protocol(
                state, step, current_task
            )
            if protocol_errors:
                state.solver_call_count += 1
                current_task.protocol_failures += 1
                current_task.status = "open"
                self.last_solver_invalid = {
                    "kind": "protocol_error",
                    "task_id": current_task.id,
                    "error": "; ".join(protocol_errors)[:2000],
                    "response_excerpt": json.dumps(
                        step.model_dump(), ensure_ascii=False
                    )[:1200],
                }
                self._record(
                    trace,
                    logger,
                    state,
                    "solver_protocol_fast_fail",
                    {
                        "task_id": current_task.id,
                        "errors": protocol_errors,
                        "critique_called": False,
                    },
                )
                if current_task.protocol_failures >= 2:
                    current_task.status = "blocked"
                    self._record(
                        trace,
                        logger,
                        state,
                        "protocol_repair_exhausted",
                        {
                            "task_id": current_task.id,
                            "reason": "; ".join(protocol_errors),
                        },
                    )
                    return self._finish_efficient(
                        state, trace, debug_trace, logger, "protocol retries exhausted"
                    )
                continue

            prior_draft_text = (
                state.solution_draft.text
                if state.execution_mode == "macro"
                and state.solution_draft.status == "accepted"
                else ""
            )
            draft = reasoning_step_to_solution_draft(
                step, version=state.solution_draft.version + 1
            )
            state.solution_draft = SolutionDraftState(
                version=draft.version,
                task_id=draft.task_id,
                text=_merge_draft_text(prior_draft_text, draft.text),
                status="proposed",
            )
            self._record(
                trace,
                logger,
                state,
                "draft_proposed",
                {
                    "version": draft.version,
                    "task_id": draft.task_id,
                    "claim_count": len(draft.claims),
                    "candidate_count": len(draft.candidate_answers),
                },
            )

            if time_phase(state) == "final_reserve":
                state.solver_call_count += 1
                return self._finish_efficient(
                    state, trace, debug_trace, logger, "reserve reached after draft"
                )

            critique = self._critique_draft(state, step, draft, debug_trace)
            self._record(
                trace,
                logger,
                state,
                "critique_completed",
                {
                    "version": draft.version,
                    "verdict": critique.verdict,
                    "accepted_claims": critique.accepted_claims,
                    "invalid_claims": critique.invalid_claims,
                    "candidate_assessment": critique.candidate_assessment,
                    "reason": critique.reason,
                },
            )

            if critique.verdict == "accept":
                self._commit_accepted_draft(state, step, draft, critique)
                next_task = _next_task_after_accepted_draft(
                    state, current_task, step.request_finalization
                )
                if next_task is not None:
                    self._record(
                        trace,
                        logger,
                        state,
                        "accepted_task_continuation",
                        {
                            "completed_task_id": current_task.id,
                            "next_task_id": next_task.id,
                            "execution_mode": state.execution_mode,
                        },
                    )
                    continue
                if self._queue_candidate_extraction_task(
                    state, trace, logger
                ):
                    continue
                if self._queue_candidate_falsification_task(
                    state, trace, logger
                ):
                    continue
                candidates_ready, candidate_reason, retry_instruction = (
                    self._verify_candidates_and_completeness(
                        state, trace, debug_trace, logger
                    )
                )
                if not candidates_ready:
                    current_task.status = "blocked"
                    self._remember_candidate_failure(
                        state,
                        current_task,
                        candidate_reason,
                        retry_instruction,
                    )
                    if self._try_efficient_replan(
                        state,
                        current_task,
                        candidate_reason,
                        "candidate_failure",
                        trace,
                        debug_trace,
                        logger,
                    ):
                        continue
                    return self._finish_efficient(
                        state,
                        trace,
                        debug_trace,
                        logger,
                        "candidate verification incomplete",
                    )
                return self._finish_efficient(
                    state, trace, debug_trace, logger, "draft accepted"
                )

            if (
                critique.verdict == "repair"
                and state.repair_count < state.max_repairs
                and time_phase(state) != "final_reserve"
            ):
                self._record(
                    trace,
                    logger,
                    state,
                    "repair_started",
                    {
                        "version": draft.version,
                        "instruction": critique.repair_instruction,
                    },
                )
                self._commit_partial_claims(state, step, draft, critique, current_task)
                repaired = self._repair_draft(
                    state, step, draft, critique, current_task, debug_trace
                )
                if repaired is not None:
                    repair_errors = validate_reasoning_step_protocol(
                        state, repaired, current_task
                    )
                    if not repair_errors and time_phase(state) != "final_reserve":
                        repaired_draft = reasoning_step_to_solution_draft(
                            repaired, version=state.solution_draft.version + 1
                        )
                        state.solution_draft = SolutionDraftState(
                            version=repaired_draft.version,
                            task_id=repaired_draft.task_id,
                            text=_merge_draft_text(
                                prior_draft_text, repaired_draft.text
                            ),
                            status="proposed",
                        )
                        repaired_critique = self._critique_draft(
                            state, repaired, repaired_draft, debug_trace
                        )
                        self._record(
                            trace,
                            logger,
                            state,
                            "critique_completed",
                            {
                                "version": repaired_draft.version,
                                "verdict": repaired_critique.verdict,
                                "accepted_claims": repaired_critique.accepted_claims,
                                "invalid_claims": repaired_critique.invalid_claims,
                                "candidate_assessment": repaired_critique.candidate_assessment,
                                "reason": repaired_critique.reason,
                            },
                        )
                        if repaired_critique.verdict == "accept":
                            self._commit_accepted_draft(
                                state, repaired, repaired_draft, repaired_critique
                            )
                            next_task = _next_task_after_accepted_draft(
                                state,
                                current_task,
                                repaired.request_finalization,
                            )
                            if next_task is not None:
                                self._record(
                                    trace,
                                    logger,
                                    state,
                                    "accepted_task_continuation",
                                    {
                                        "completed_task_id": current_task.id,
                                        "next_task_id": next_task.id,
                                        "execution_mode": state.execution_mode,
                                        "after_repair": True,
                                    },
                                )
                                continue
                            if self._queue_candidate_extraction_task(
                                state, trace, logger
                            ):
                                continue
                            if self._queue_candidate_falsification_task(
                                state, trace, logger
                            ):
                                continue
                            candidates_ready, candidate_reason, retry_instruction = (
                                self._verify_candidates_and_completeness(
                                    state, trace, debug_trace, logger
                                )
                            )
                            if not candidates_ready:
                                current_task.status = "blocked"
                                self._remember_candidate_failure(
                                    state,
                                    current_task,
                                    candidate_reason,
                                    retry_instruction,
                                )
                                if self._try_efficient_replan(
                                    state,
                                    current_task,
                                    candidate_reason,
                                    "candidate_failure",
                                    trace,
                                    debug_trace,
                                    logger,
                                ):
                                    continue
                                return self._finish_efficient(
                                    state,
                                    trace,
                                    debug_trace,
                                    logger,
                                    "candidate verification incomplete",
                                )
                            return self._finish_efficient(
                                state, trace, debug_trace, logger, "repair accepted"
                            )
                    else:
                        state.solver_call_count += 1

            state.solution_draft.status = "rejected"
            current_task.status = "blocked"
            failed_reason = critique.failed_route_summary or critique.reason
            if self._try_efficient_replan(
                state,
                current_task,
                failed_reason,
                "unsupported_claim",
                trace,
                debug_trace,
                logger,
            ):
                continue
            return self._finish_efficient(
                state, trace, debug_trace, logger, "route rejected"
            )

    def _queue_candidate_extraction_task(
        self,
        state: AgentState,
        trace: list[dict],
        logger: RuntimeLogger,
    ) -> bool:
        if time_phase(state) != "normal":
            return False
        candidate_task = _maybe_add_candidate_extraction_task(state)
        if candidate_task is None:
            return False
        self._record(
            trace,
            logger,
            state,
            "candidate_extraction_task_added",
            {
                "task_id": candidate_task.id,
                "statement": candidate_task.objective,
            },
        )
        return True

    def _queue_candidate_falsification_task(
        self,
        state: AgentState,
        trace: list[dict],
        logger: RuntimeLogger,
    ) -> bool:
        if time_phase(state) != "normal":
            return False
        task = _maybe_add_candidate_falsification_task(state)
        if task is None:
            return False
        self._record(
            trace,
            logger,
            state,
            "candidate_falsification_task_added",
            {"task_id": task.id, "statement": task.objective},
        )
        return True

    def _critique_draft(self, state, step, draft, debug_trace) -> CritiqueOutput:
        state.phase = "critique"
        state.model_call_count += 1
        return self.draft_critic.critique(state, step, draft, debug_trace)

    def _commit_accepted_draft(
        self, state, step, draft, critique: CritiqueOutput
    ) -> None:
        accepted = accepted_claim_closure(
            draft,
            critique.accepted_claims or [claim.id for claim in draft.claims],
            critique.invalid_claims,
        )
        filtered = _filter_step_claims(step, accepted)
        if not (filtered.new_definitions or filtered.new_results or filtered.candidate_answers):
            filtered.closed_tasks = []
        before_definitions = len(state.definitions)
        before_results = len(state.derived_results)
        commit_step(
            state,
            filtered,
            StepVerification(verdict="accept", reason="批量 Critique 接受草稿。"),
        )
        _record_accepted_claims(
            state, draft, accepted, before_definitions, before_results
        )
        state.solution_draft.status = "accepted"

    def _commit_partial_claims(
        self, state, step, draft, critique, current_task
    ) -> None:
        accepted = accepted_claim_closure(
            draft, critique.accepted_claims, critique.invalid_claims
        )
        state.solution_draft.status = "repairing"
        if not accepted:
            state.solver_call_count += 1
            return
        filtered = _filter_step_claims(step, accepted)
        filtered.candidate_answers = []
        filtered.closed_tasks = []
        filtered.new_tasks = []
        filtered.solution_draft = ""
        current_task.status = "open"
        before_definitions = len(state.definitions)
        before_results = len(state.derived_results)
        commit_step(
            state,
            filtered,
            StepVerification(verdict="accept", reason="Critique 部分接受安全 claims。"),
        )
        current_task.status = "active"
        _record_accepted_claims(
            state, draft, accepted, before_definitions, before_results
        )

    def _repair_draft(
        self, state, step, draft, critique, current_task, debug_trace
    ) -> ReasoningStep | None:
        state.phase = "repair"
        state.repair_count += 1
        state.model_call_count += 1
        messages = build_repair_messages(state, step, draft, critique)
        try:
            response = call_model(
                self.client,
                state,
                debug_trace,
                "repair",
                messages=messages,
                temperature=0.1,
                thinking_mode=False,
                max_tokens=8192,
            )
            content = response.content
            data = extract_json_object(content or "")
            if not data:
                return None
            normalized = _normalize_reasoning_step_payload(
                data, state, current_task_id=current_task.id
            )
            repaired = ReasoningStep.model_validate(normalized)
            return _remove_committed_proposals(state, repaired)
        except (Exception, ValidationError, ValueError) as exc:
            debug_trace.append({"type": "repair_error", "content": str(exc)})
            return None

    def _try_efficient_replan(
        self,
        state,
        task,
        reason,
        category,
        trace,
        debug_trace,
        logger,
    ) -> bool:
        previous_error = next(
            (
                error
                for error in reversed(state.error_memory)
                if error.id == task.last_error_id
            ),
            None,
        )
        if previous_error is None or previous_error.reason != reason:
            error_category = category if category in {
                "dependency_error",
                "unsupported_claim",
                "repeated_route",
                "candidate_failure",
                "incomplete_case_analysis",
                "other",
            } else "other"
            error = ErrorRecord(
                id=next_error_id(state),
                branch_id=state.active_branch_id,
                step_summary=f"路线失败：{task.objective}",
                category=error_category,
                reason=reason,
                retry_instruction="改用不同核心方法并修复该失败原因。",
                related_ids=[candidate.id for candidate in state.candidates],
            )
            state.error_memory.append(error)
            task.last_error_id = error.id
        fingerprint = _route_fingerprint(state, task, reason, category)
        if fingerprint not in state.failed_route_fingerprints:
            state.failed_route_fingerprints.append(fingerprint)
        self._record(
            trace,
            logger,
            state,
            "route_rejected",
            {"task_id": task.id, "reason": reason, "fingerprint": fingerprint},
        )
        if (
            state.model_replan_count >= state.max_model_replans
            or time_phase(state) != "normal"
        ):
            return False
        verification = StepVerification(
            verdict="reject",
            reason=reason,
            retry_instruction="改用不同核心方法并生成新的宏任务。",
            error_category=category if category in {
                "dependency_error", "unsupported_claim", "repeated_route",
                "candidate_failure", "incomplete_case_analysis", "other"
            } else "other",
        )
        record = self._replan_blocked_task(state, task, verification, debug_trace)
        self._record(
            trace,
            logger,
            state,
            "replan_triggered",
            {
                "task_id": task.id,
                "new_tasks": record.new_tasks,
                "reason": record.reason,
                "model_replan_count": state.model_replan_count,
            },
        )
        return bool(record.new_tasks)

    def _verify_candidates_and_completeness(
        self, state, trace, debug_trace, logger
    ) -> tuple[bool, str, str]:
        requires_candidate_set = any(
            requirement.kind == "candidate_set_complete"
            for requirement in state.requirements
        )
        unfinished = pending_required_tasks(state)
        if unfinished:
            task_ids = ", ".join(task.id for task in unfinished)
            return (
                False,
                f"仍有必需任务未完成：{task_ids}。",
                "先完成全部 required Task，尤其是反例、边界与独立核验任务，再验证候选。",
            )
        if not state.candidates:
            return (
                False,
                "Solver 尚未注册任何候选答案，禁止进入严格验证。",
                "重新调用 Solver，把可独立判分的最终结论写入 candidate_answers；"
                "不能用 solution_draft、new_results 或 Critic accept 代替候选注册。",
            )
        if time_phase(state) == "final_reserve":
            return (
                False,
                "剩余时间不足，未能逐一验证候选及检查集合完备性。",
                "保留已有推导，但不得把候选集合视为已经验证完整。",
            )

        for candidate in state.candidates:
            if candidate.status not in {"candidate", "conflict"}:
                continue
            if time_phase(state) == "final_reserve":
                break
            state.phase = "candidate_verify"
            state.model_call_count += 1
            verification = self.candidate_verifier.verify(
                state, candidate, debug_trace
            )
            apply_candidate_verification(state, candidate, verification)
            self._record(
                trace,
                logger,
                state,
                "candidate_verified",
                {
                    "candidate_id": candidate.id,
                    "candidate_value": candidate.value,
                    "verdict": verification.verdict,
                    "reason": verification.reason,
                },
            )

        unresolved = [
            candidate.id
            for candidate in state.candidates
            if candidate.status in {"candidate", "conflict"}
        ]
        if unresolved or time_phase(state) == "final_reserve":
            reason = "仍有候选未完成独立验证：" + ", ".join(unresolved)
            return (
                False,
                reason,
                "逐一复核未决候选；验证失败的候选应修正或替换。",
            )

        verified = [
            candidate.id
            for candidate in state.candidates
            if candidate.status == "verified"
        ]
        if not verified:
            rejected_reasons = [
                candidate.verification_reason.strip()
                for candidate in state.candidates
                if candidate.status == "rejected"
                and candidate.verification_reason.strip()
            ]
            detail = "；".join(rejected_reasons)
            return (
                False,
                "已注册候选均未通过独立 CandidateVerifier，禁止进入严格收尾。"
                + (f" 失败原因：{detail}" if detail else ""),
                "Solver 必须根据验证失败原因重新推导并注册新的 candidate_answers。",
            )
        if not requires_candidate_set:
            return True, "候选已注册并通过独立 CandidateVerifier。", ""

        state.phase = "candidate_set_verify"
        state.model_call_count += 1
        set_verification = self.candidate_set_verifier.verify(state, debug_trace)
        record = apply_candidate_set_verification(state, set_verification)
        self._record(
            trace,
            logger,
            state,
            "candidate_set_verified",
            {
                "record_id": record.id,
                "verdict": record.verdict,
                "verified_candidate_ids": record.verified_candidate_ids,
                "rejected_candidate_ids": record.rejected_candidate_ids,
                "complete_answer": record.complete_answer,
                "missing_cases": record.missing_cases,
                "reason": record.reason,
            },
        )
        if record.verdict == "accept":
            return True, record.reason, ""
        reason = record.reason or "候选集合未通过完备性验证。"
        instruction = (
            record.repair_instruction
            or "重新搜索漏解、边界和分类分支，并再次验证全部候选。"
        )
        return False, reason, instruction

    @staticmethod
    def _remember_candidate_failure(
        state, task, reason: str, retry_instruction: str
    ) -> None:
        error = ErrorRecord(
            id=next_error_id(state),
            branch_id=state.active_branch_id,
            step_summary=f"候选验证与完备性审查失败：{task.objective}",
            category="candidate_failure",
            reason=reason,
            retry_instruction=retry_instruction,
            related_ids=[candidate.id for candidate in state.candidates],
        )
        state.error_memory.append(error)
        task.last_error_id = error.id
        task.blocked_reason = reason

    def _resolve_candidate_conflict(
        self, state, trace, logger, debug_trace=None
    ) -> None:
        if time_phase(state) == "final_reserve":
            return
        for candidate in state.candidates:
            if candidate.status not in {"candidate", "conflict"}:
                continue
            state.phase = "candidate_verify"
            state.model_call_count += 1
            verification = self.candidate_verifier.verify(
                state, candidate, debug_trace
            )
            apply_candidate_verification(state, candidate, verification)
            self._record(
                trace,
                logger,
                state,
                "candidate_conflict_checked",
                {"candidate_id": candidate.id, "verdict": verification.verdict},
            )

    def _finish_efficient(
        self, state, trace, debug_trace, logger, reason
    ) -> RuntimeResult:
        state.phase = "finalize"
        strict_ready = can_finalize(state)
        best_effort_ready = can_finalize_best_effort(state)
        state.finalize_mode = "strict" if strict_ready else "best_effort"
        state.finalize_reason = reason
        self._record(
            trace,
            logger,
            state,
            "finalize_started",
            {
                "mode": state.finalize_mode,
                "reason": reason,
                "remaining_seconds": remaining_seconds(state),
                "model_call_count": state.model_call_count,
                "candidate_ids": [
                    candidate.id
                    for candidate in state.candidates
                    if candidate.status in {"candidate", "verified", "conflict"}
                ],
                "best_effort_gate": best_effort_ready,
            },
        )
        answer = (
            self._best_effort_finalize_with_verification(
                state, trace, debug_trace, logger
            )
            if state.finalize_mode == "best_effort"
            else self._finalize(state, debug_trace, emergency=False)
        )
        if answer.answer.strip().lower() in {"", "unknown", "incomplete"}:
            answer = self._fallback_final_answer(state)
        state.phase = "done"
        self._record(
            trace,
            logger,
            state,
            "final",
            {
                "data": answer.model_dump(),
                "mode": state.finalize_mode,
                "reason": reason,
            },
        )
        result = RuntimeResult(
            final_response=answer.answer.strip(),
            trace=make_json_safe(trace),
            debug_trace=make_json_safe(debug_trace),
            state=state,
        )
        logger.write_final(result.final_response, result.trace, state)
        return result

    def _best_effort_finalize_with_verification(
        self,
        state: AgentState,
        trace: list[dict],
        debug_trace: list[dict],
        logger: RuntimeLogger,
    ) -> FinalAnswer:
        provisional = self._finalize(state, debug_trace, emergency=True)
        if not provisional.answer.strip():
            provisional = self._fallback_final_answer(state)
        self._record(
            trace,
            logger,
            state,
            "best_effort_candidate_generated",
            {"answer": provisional.answer},
        )

        candidate = register_candidate(
            state,
            value=provisional.answer.strip(),
            # Emergency Finalizer synthesizes this answer from mixed state. Do not
            # falsely claim that every historical verified result supports it.
            support_results=[],
        )
        state.phase = "candidate_verify"
        state.model_call_count += 1
        verification = self.candidate_verifier.verify(
            state,
            candidate,
            debug_trace,
            allow_finalize_reserve=True,
        )
        apply_candidate_verification(state, candidate, verification)
        self._record(
            trace,
            logger,
            state,
            "best_effort_candidate_verified",
            {
                "candidate_id": candidate.id,
                "candidate_value": candidate.value,
                "verdict": verification.verdict,
                "reason": verification.reason,
            },
        )

        audit = {
            "provisional_answer": provisional.answer,
            "verdict": verification.verdict,
            "reason": verification.reason,
            "instruction": (
                "保持已验证结论并重新整理最终答案。"
                if verification.verdict == "accept"
                else "不得重复临时候选；根据审核原因重新计算并生成修正答案。"
            ),
        }
        state.phase = "finalize"
        self._record(
            trace,
            logger,
            state,
            "best_effort_regeneration_started",
            audit,
        )
        regenerated = self._finalize(
            state,
            debug_trace,
            emergency=True,
            best_effort_verification=audit,
            call_type="best_effort_regenerator",
        )
        selected = regenerated if regenerated.answer.strip() else provisional
        if not selected.answer.strip():
            selected = self._fallback_final_answer(state)

        regenerated_candidate = register_candidate(
            state,
            value=selected.answer.strip(),
            support_results=[],
        )
        state.phase = "candidate_verify"
        state.model_call_count += 1
        regenerated_verification = self.candidate_verifier.verify(
            state,
            regenerated_candidate,
            debug_trace,
            allow_finalize_reserve=True,
        )
        apply_candidate_verification(
            state, regenerated_candidate, regenerated_verification
        )
        self._record(
            trace,
            logger,
            state,
            "best_effort_regenerated_candidate_verified",
            {
                "candidate_id": regenerated_candidate.id,
                "candidate_value": regenerated_candidate.value,
                "verdict": regenerated_verification.verdict,
                "reason": regenerated_verification.reason,
            },
        )
        if regenerated_verification.verdict != "accept":
            self._record(
                trace,
                logger,
                state,
                "best_effort_unverified_answer_selected",
                {
                    "candidate_id": regenerated_candidate.id,
                    "candidate_value": regenerated_candidate.value,
                    "verdict": regenerated_verification.verdict,
                    "reason": regenerated_verification.reason,
                },
            )
            selected.reasoning_summary = (
                selected.reasoning_summary.strip()
                or "已执行独立验证与重新生成；严格验证仍未通过，按 best-effort 返回当前最有依据的具体答案。"
            )
        return selected
    def _formalize(
        self,
        state: AgentState,
        trace: list[dict],
        debug_trace: list[dict],
        logger: RuntimeLogger,
    ) -> None:
        state.phase = "formalize"
        self._record(trace, logger, state, "formalization_started", {})
        classification = self._classify_domain(state, debug_trace)
        selected_skills = select_strategy_skills(
            classification.primary_category,
            classification.secondary_categories,
        )
        self.selected_strategy_skills = selected_skills
        state.selected_skill_ids = [skill.id for skill in selected_skills]
        self._record(
            trace,
            logger,
            state,
            "domain_classification_committed",
            {
                "primary_category": classification.primary_category,
                "secondary_categories": classification.secondary_categories,
                "confidence": classification.confidence,
                "selected_skill_ids": state.selected_skill_ids,
            },
        )
        output = self._call_formalizer(state, debug_trace)
        facts: list[ProblemFact] = []
        for index, raw_fact in enumerate(output.problem_facts, start=1):
            normalized_fact = _normalize_problem_fact_payload(raw_fact)
            try:
                fact = ProblemFact.model_validate(
                    {
                        **normalized_fact,
                        "id": f"P{index}",
                        "status": "verified",
                    }
                )
            except ValidationError:
                continue
            if self.formalization_verifier.verify_problem_fact(state.problem, fact):
                facts.append(fact)

        if not facts:
            facts.append(
                ProblemFact(
                    id="P1",
                    fact_type="target",
                    statement="原题要求求解给定数学问题",
                    source_text=state.problem,
                    status="verified",
                )
            )
        tasks = [
            Task(
                id="T1",
                kind="derive",
                objective="基于原题和已验证事实推进求解",
                priority=10,
                status="open",
            )
        ]
        commit_formalization(
            state,
            facts,
            tasks,
            classification.primary_category,
            classification.secondary_categories,
            classification.confidence,
            classification.reason,
        )
        self._record(
            trace,
            logger,
            state,
            "formalization_committed",
            {
                "problem_fact_count": len(facts),
                "task_count": len(tasks),
                "problem_type": state.problem_type,
            },
        )

    def _strategy_preprocess(
        self,
        state: AgentState,
        trace: list[dict],
        debug_trace: list[dict],
        logger: RuntimeLogger,
        metadata: dict | None = None,
        selected_skills: list[SelectedStrategySkill] | None = None,
    ) -> None:
        state.phase = "plan"
        self._record(trace, logger, state, "strategy_preprocess_started", {})
        output = self._call_strategy_preprocessor(
            state, debug_trace, metadata, selected_skills
        )
        guidance = _strategy_output_to_guidance(state, output)
        state.strategy_guidance.append(guidance)
        state.execution_mode = output.execution_mode
        task_update = _apply_strategy_task_revisions(state, output)
        self._record(
            trace,
            logger,
            state,
            "strategy_preprocess_committed",
            {
                "guidance_id": guidance.id,
                "problem_type": guidance.problem_type,
                "selected_skill_ids": guidance.selected_skill_ids,
                "warnings": guidance.sanitization_warnings,
                "task_update": task_update,
                "execution_mode": state.execution_mode,
            },
        )

    def _call_formalizer(
        self, state: AgentState, debug_trace: list[dict]
    ) -> FormalizationOutput:
        if not callable(getattr(self.client, "chat", None)):
            return FormalizationOutput()
        messages = [
            {"role": "system", "content": FORMALIZER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "输出 JSON：problem_facts。\n"
                    "problem_facts 项只能包含 fact_type, statement, source_text；"
                    "只抽取题面直接给出的事实、定义域约束和目标。"
                    "不要输出 problem_type、initial_tasks、解题计划、候选值或答案暗示。\n\n"
                    f"Problem:\n{state.problem}"
                ),
            },
        ]
        for attempt in range(2):
            try:
                if state.efficient_runtime and time_phase(state) == "final_reserve":
                    break
                if state.efficient_runtime:
                    state.model_call_count += 1
                response = call_model(
                    self.client,
                    state,
                    debug_trace,
                    "formalizer",
                    messages=messages,
                    temperature=0.0,
                    thinking_mode=False,
                    max_tokens=4096,
                )
                content = response.content
                data = extract_json_object(content or "")
                if data:
                    return FormalizationOutput.model_validate(data)
                raise ValueError("formalizer did not contain a valid JSON object")
            except (Exception, ValidationError) as exc:
                error_text = str(exc)
                debug_trace.append(
                    {
                        "type": "formalizer_error",
                        "attempt": attempt + 1,
                        "content": error_text,
                    }
                )
                if attempt == 0:
                    retry_message = _build_json_regeneration_message(
                        protocol_name="FormalizationOutput",
                        required_fields="problem_facts",
                        error=error_text,
                        response_excerpt=str(locals().get("content", "")),
                    )
                    messages.append({"role": "user", "content": retry_message})
                    debug_trace.append(
                        {"type": "formalizer_retry", "content": retry_message}
                    )
                    continue
                break
        return FormalizationOutput()

    def _classify_domain(
        self,
        state: AgentState,
        debug_trace: list[dict],
    ) -> DomainClassificationOutput:
        if not callable(getattr(self.client, "chat", None)):
            return DomainClassificationOutput()
        allowed_categories = "、".join(ALLOWED_SKILL_CATEGORIES)
        messages = [
            {
                "role": "system",
                "content": DOMAIN_CLASSIFIER_SYSTEM_PROMPT.replace(
                    "{allowed_categories}", allowed_categories
                ),
            },
            {"role": "user", "content": f"题目：\n{state.problem}"},
        ]
        for attempt in range(2):
            try:
                if state.efficient_runtime and time_phase(state) == "final_reserve":
                    break
                if state.efficient_runtime:
                    state.model_call_count += 1
                response = call_model(
                    self.client,
                    state,
                    debug_trace,
                    "domain_classifier",
                    messages=messages,
                    temperature=0.0,
                    thinking_mode=False,
                    max_tokens=1024,
                )
                content = response.content
                data = extract_json_object(content or "")
                if not data:
                    raise ValueError("domain classifier did not contain a valid JSON object")
                output = DomainClassificationOutput.model_validate(data)
                return _sanitize_domain_classification(output)
            except (Exception, ValidationError) as exc:
                error_text = str(exc)
                debug_trace.append(
                    {
                        "type": "domain_classifier_error",
                        "attempt": attempt + 1,
                        "content": error_text,
                    }
                )
                if attempt == 0:
                    retry_message = _build_json_regeneration_message(
                        protocol_name="DomainClassificationOutput",
                        required_fields=(
                            "primary_category, secondary_categories, confidence, reason"
                        ),
                        error=error_text,
                        response_excerpt=str(locals().get("content", "")),
                    )
                    messages.append({"role": "user", "content": retry_message})
                    debug_trace.append(
                        {"type": "domain_classifier_retry", "content": retry_message}
                    )
                    continue
                break
        return DomainClassificationOutput()

    def _call_strategy_preprocessor(
        self,
        state: AgentState,
        debug_trace: list[dict],
        metadata: dict | None = None,
        selected_skills: list[SelectedStrategySkill] | None = None,
    ) -> StrategyOutput:
        selected_skills = selected_skills or []
        if not callable(getattr(self.client, "chat", None)):
            return StrategyOutput(
                problem_type=state.problem_type,
                selected_skill_ids=[skill.id for skill in selected_skills],
                risk_controls=["策略预处理不可用，正式解题时必须保守推进。"],
                do_not=["不要猜最终答案。"],
                first_step_instruction="先整理题目条件、定义必要变量，并建立目标表达式。",
            )
        messages = [{"role": "system", "content": STRATEGY_PREPROCESS_SYSTEM_PROMPT}]
        if selected_skills:
            messages.append(
                {
                    "role": "user",
                    "content": _build_strategy_skill_reference_message(selected_skills),
                }
            )
        messages.append(
            {
                "role": "user",
                "content": _build_strategy_preprocess_context_message(
                    state=state,
                    metadata=metadata,
                ),
            }
        )
        for attempt in range(2):
            try:
                if state.efficient_runtime and time_phase(state) == "final_reserve":
                    break
                if state.efficient_runtime:
                    state.model_call_count += 1
                response = call_model(
                    self.client,
                    state,
                    debug_trace,
                    "strategy_preprocess",
                    messages=messages,
                    temperature=0.0,
                    thinking_mode=False,
                    max_tokens=int(
                        getattr(self.config, "strategy_preprocess_max_tokens", 4096)
                    ),
                )
                content = response.content
                parsed = _parse_strategy_output(content or "")
                if parsed is not None:
                    parsed.selected_skill_ids = [skill.id for skill in selected_skills]
                    return parsed
                raise ValueError("strategy preprocess did not contain a valid JSON object")
            except (Exception, ValidationError) as exc:
                error_text = str(exc)
                debug_trace.append(
                    {
                        "type": "strategy_preprocess_error",
                        "attempt": attempt + 1,
                        "content": error_text,
                    }
                )
                if attempt == 0:
                    retry_message = _build_strategy_json_retry_message(
                        error_text,
                        str(locals().get("content", "")),
                    )
                    messages.append({"role": "user", "content": retry_message})
                    debug_trace.append(
                        {
                            "type": "strategy_preprocess_retry",
                            "content": retry_message,
                        }
                    )
                    continue
                break
        return StrategyOutput(
            problem_type=state.problem_type,
            selected_skill_ids=[skill.id for skill in selected_skills],
            risk_controls=["策略预处理输出无法解析，正式解题时必须保守推进。"],
            do_not=["不要猜最终答案。"],
            first_step_instruction="先整理题目条件、定义必要变量，并建立目标表达式。",
        )

    def _solve_step(
        self, state: AgentState, debug_trace: list[dict], current_task: Task
    ) -> ReasoningStep | None:
        prior_invalid = (
            dict(self.last_solver_invalid)
            if self.last_solver_invalid.get("task_id") == current_task.id
            else {}
        )
        messages = build_solver_messages(
            state,
            history_messages=self.solver_history_messages,
            current_task=current_task,
        )
        is_json_repair = bool(
            prior_invalid
            and prior_invalid.get("kind") in {"json_error", "protocol_error"}
        )
        if is_json_repair:
            messages.append(
                {
                    "role": "user",
                    "content": _build_json_retry_message(
                        prior_invalid.get("error", "ReasoningStep JSON 无法解析。"),
                        prior_invalid.get("response_excerpt", ""),
                        current_task.id,
                    ),
                }
            )
            debug_trace.append(
                {
                    "type": "solver_json_repair_started",
                    "task_id": current_task.id,
                    "error": prior_invalid.get("error", "")[:1000],
                }
            )
        self.last_solver_invalid = {}
        try:
            if state.efficient_runtime:
                state.model_call_count += 1
            response = call_model(
                self.client,
                state,
                debug_trace,
                "solver_json_repair" if is_json_repair else "solver",
                messages=messages,
                temperature=0.2,
                thinking_mode=False,
                max_tokens=int(
                    getattr(self.config, "custom2_solver_max_tokens", 131072)
                ),
            )
            content = response.content
            self._remember_solver_response(content)
            data = extract_json_object(content or "")
            if not data:
                raise ValueError("solver response did not contain a valid JSON object")
            normalized = _normalize_reasoning_step_payload(
                data, state, current_task_id=current_task.id
            )
            self.last_solver_invalid = {}
            return ReasoningStep.model_validate(normalized)
        except ValidationError as exc:
            error_text = str(exc)
            self.last_solver_invalid = {
                "kind": "json_error",
                "task_id": current_task.id,
                "error": error_text[:2000],
                "response_excerpt": str(locals().get("content", ""))[:1200],
            }
            debug_trace.append({"type": "solver_error", "content": error_text})
        except ValueError as exc:
            error_text = str(exc)
            self.last_solver_invalid = {
                "kind": "json_error",
                "task_id": current_task.id,
                "error": error_text[:2000],
                "response_excerpt": str(locals().get("content", ""))[:1200],
            }
            debug_trace.append({"type": "solver_error", "content": error_text})
        except Exception as exc:
            error_text = str(exc)
            self.last_solver_invalid = {
                "kind": "chat_error",
                "task_id": current_task.id,
                "error": error_text[:2000],
                "response_excerpt": "",
            }
            debug_trace.append({"type": "solver_chat_error", "content": error_text})
        return None

    def _remember_solver_response(self, content: str) -> None:
        text = str(content or "").strip()
        if not text:
            return
        self.solver_raw_responses.append(text[-16000:])
        self.solver_raw_responses = self.solver_raw_responses[-4:]

    def _replan_blocked_task(
        self,
        state: AgentState,
        blocked_task: Task,
        verification: StepVerification,
        debug_trace: list[dict],
    ):
        replan_output = self._call_replanner(
            state=state,
            blocked_task=blocked_task,
            verification=verification,
            debug_trace=debug_trace,
        )
        new_tasks = _replan_output_to_tasks(state, blocked_task, replan_output)
        trigger = "model_replan" if new_tasks else "task_rejected_twice"
        reason = (
            replan_output.diagnosis
            if new_tasks and replan_output.diagnosis
            else blocked_task.blocked_reason
        )
        if not new_tasks and not state.efficient_runtime:
            new_tasks = [
                _build_fallback_route_reset_task(
                    state,
                    blocked_task,
                    reason=blocked_task.blocked_reason,
                )
            ]
        invalidate_tasks: list[str] = []
        if state.efficient_runtime:
            state.model_replan_count += 1
            invalidate_tasks = [
                task.id
                for task in state.tasks
                if task.status in {"open", "active", "blocked"}
            ]
        record = record_replan(
            state,
            trigger=trigger,
            reason=reason,
            invalidate_tasks=invalidate_tasks,
            new_tasks=new_tasks,
        )
        if state.efficient_runtime and record.new_tasks:
            first = next(
                (task for task in state.tasks if task.id == record.new_tasks[0]), None
            )
            if first is not None:
                activate_task(first)
        return record

    def _call_replanner(
        self,
        state: AgentState,
        blocked_task: Task,
        verification: StepVerification,
        debug_trace: list[dict],
    ) -> ReplanOutput:
        if not callable(getattr(self.client, "chat", None)):
            return ReplanOutput()
        messages = [{"role": "system", "content": REPLANNER_SYSTEM_PROMPT}]
        if self.selected_strategy_skills:
            messages.append(
                {
                    "role": "user",
                    "content": _build_replanner_skill_reference_message(
                        self.selected_strategy_skills
                    ),
                }
            )
        messages.append(
            {
                "role": "user",
                "content": _build_replanner_context_message(
                    state=state,
                    blocked_task=blocked_task,
                    verification=verification,
                ),
            }
        )
        for attempt in range(2):
            try:
                if state.efficient_runtime and time_phase(state) != "normal":
                    break
                if state.efficient_runtime:
                    state.model_call_count += 1
                response = call_model(
                    self.client,
                    state,
                    debug_trace,
                    "replanner",
                    messages=messages,
                    temperature=0.0,
                    thinking_mode=False,
                    max_tokens=4096,
                )
                content = response.content
                debug_trace.append(
                    {
                        "type": "replanner_response",
                        "attempt": attempt + 1,
                        "content_length": len(content),
                    }
                )
                data = extract_json_object(content or "")
                if data:
                    return ReplanOutput.model_validate(data)
                raise ValueError("replanner did not contain a valid JSON object")
            except (Exception, ValidationError) as exc:
                error_text = str(exc)
                debug_trace.append(
                    {
                        "type": "replanner_error",
                        "attempt": attempt + 1,
                        "content": error_text,
                    }
                )
                if attempt == 0:
                    retry_message = _build_json_regeneration_message(
                        protocol_name="ReplanOutput",
                        required_fields=(
                            "diagnosis, avoid_routes, reuse_results, new_tasks, "
                            "first_step_instruction"
                        ),
                        error=error_text,
                        response_excerpt=str(locals().get("content", "")),
                    )
                    messages.append({"role": "user", "content": retry_message})
                    debug_trace.append({"type": "replanner_retry", "content": retry_message})
                    continue
                break
        return ReplanOutput()

    def _finalize(
        self,
        state: AgentState,
        debug_trace: list[dict],
        emergency: bool = False,
        best_effort_verification: dict | None = None,
        call_type: str = "finalizer",
    ) -> FinalAnswer:
        if (
            state.efficient_runtime
            and state.deadline_at > 0
            and remaining_seconds(state) <= 0
        ):
            debug_trace.append(
                {
                    "type": "finalizer_skipped",
                    "reason": "runtime deadline exhausted",
                }
            )
            return FinalAnswer(answer="", reasoning_summary="")
        if callable(getattr(self.client, "chat", None)):
            messages = build_finalizer_messages(
                state,
                solver_history_messages=self.solver_history_messages,
                unparsed_solver_responses=self.solver_raw_responses,
                emergency=emergency,
                best_effort_verification=best_effort_verification,
            )
            for attempt in range(2):
                try:
                    if state.efficient_runtime:
                        state.model_call_count += 1
                    response = call_model(
                        self.client,
                        state,
                        debug_trace,
                        call_type,
                        allow_finalize_reserve=True,
                        messages=messages,
                        temperature=0.0,
                        thinking_mode=False,
                        max_tokens=int(
                            getattr(self.config, "custom2_finalizer_max_tokens", 8192)
                        ),
                    )
                    content = response.content
                    data = extract_json_object(content or "")
                    if data:
                        return FinalAnswer.model_validate(data)
                    raise ValueError("finalizer did not contain a valid JSON object")
                except (Exception, ValidationError) as exc:
                    error_text = str(exc)
                    debug_trace.append(
                        {
                            "type": "finalizer_error",
                            "attempt": attempt + 1,
                            "content": error_text,
                        }
                    )
                    if isinstance(
                        exc, (ModelCallBudgetExhausted, ModelCallTimedOut)
                    ):
                        break
                    if attempt == 0:
                        retry_message = _build_json_regeneration_message(
                            protocol_name="FinalAnswer",
                            required_fields="answer, reasoning_summary",
                            error=error_text,
                            response_excerpt=str(locals().get("content", "")),
                        )
                        messages.append({"role": "user", "content": retry_message})
                        debug_trace.append(
                            {"type": "finalizer_retry", "content": retry_message}
                        )
                        continue
                    break

        verified = [candidate for candidate in state.candidates if candidate.status == "verified"]
        if verified:
            return FinalAnswer(answer=verified[0].value, reasoning_summary="")
        if emergency and state.candidates:
            return FinalAnswer(answer=state.candidates[0].value, reasoning_summary="")
        return FinalAnswer(answer="", reasoning_summary="")

    def _emergency_finalize(
        self,
        state: AgentState,
        trace: list[dict],
        debug_trace: list[dict],
        reason: str,
        logger: RuntimeLogger,
    ) -> RuntimeResult:
        self._record(
            trace,
            logger,
            state,
            "finalize_started",
            {"emergency": True, "reason": reason},
        )
        answer = self._finalize(state, debug_trace, emergency=True)
        if not answer.answer.strip():
            answer = self._fallback_final_answer(state)
        state.phase = "done"
        self._record(
            trace,
            logger,
            state,
            "final",
            {"data": answer.model_dump(), "emergency": True, "reason": reason},
        )
        result = RuntimeResult(
            final_response=answer.answer,
            trace=make_json_safe(trace),
            debug_trace=make_json_safe(debug_trace),
            state=state,
        )
        logger.write_final(result.final_response, result.trace, state)
        return result

    def _fallback_final_answer(self, state: AgentState) -> FinalAnswer:
        accepted_sets = [
            record
            for record in state.candidate_set_verifications
            if record.verdict == "accept" and record.complete_answer.strip()
        ]
        if accepted_sets:
            return FinalAnswer(
                answer=accepted_sets[-1].complete_answer,
                reasoning_summary=accepted_sets[-1].reason,
            )
        if state.candidates:
            verified = [
                candidate for candidate in state.candidates if candidate.status == "verified"
            ]
            if verified:
                return FinalAnswer(
                    answer="；".join(candidate.value for candidate in verified),
                    reasoning_summary="",
                )
            return FinalAnswer(answer=state.candidates[0].value, reasoning_summary="")
        if state.derived_results:
            return FinalAnswer(answer=state.derived_results[-1].statement, reasoning_summary="")
        if state.solution_draft.text.strip():
            return FinalAnswer(answer=state.solution_draft.text.strip(), reasoning_summary="")
        rescued = _rescue_answer_from_solver_texts(self.solver_raw_responses)
        if rescued:
            return FinalAnswer(answer=rescued, reasoning_summary="")
        return FinalAnswer(answer="未能形成可靠的最终结论。", reasoning_summary="")

    def _incomplete(
        self,
        state: AgentState,
        trace: list[dict],
        debug_trace: list[dict],
        reason: str,
        logger: RuntimeLogger,
    ) -> RuntimeResult:
        self._record(
            trace,
            logger,
            state,
            "incomplete",
            {
                "reason": reason,
                "verified_problem_facts": [
                    pf.id for pf in state.problem_facts if pf.status == "verified"
                ],
                "verified_definitions": [
                    d.id for d in state.definitions if d.status == "verified"
                ],
                "verified_results": [
                    r.id for r in state.derived_results if r.status == "verified"
                ],
                "verified_candidates": [
                    c.id for c in state.candidates if c.status == "verified"
                ],
                "unsatisfied_requirements": [
                    req.id for req in state.requirements if req.status != "satisfied"
                ],
                "open_tasks": [
                    task.id
                    for task in state.tasks
                    if task.status in {"open", "active", "blocked"}
                ],
            },
        )
        result = RuntimeResult(
            final_response="incomplete",
            trace=make_json_safe(trace),
            debug_trace=make_json_safe(debug_trace),
            state=state,
        )
        logger.write_final(result.final_response, result.trace, state)
        return result

    @staticmethod
    def _record(
        trace: list[dict],
        logger: RuntimeLogger,
        state: AgentState,
        event_type: str,
        data: dict,
    ) -> None:
        event = {"type": event_type, **data}
        if state.efficient_runtime:
            event.setdefault("model_call_count", state.model_call_count)
            event.setdefault("solver_call_count", state.solver_call_count)
            event.setdefault("remaining_seconds", remaining_seconds(state))
        trace.append(make_json_safe(event))
        logger.emit(event_type, data, state)


def _filter_step_claims(step: ReasoningStep, accepted: set[str]) -> ReasoningStep:
    filtered = step.model_copy(deep=True)
    filtered.new_definitions = [
        proposal
        for index, proposal in enumerate(step.new_definitions, start=1)
        if f"DRAFT-D{index}" in accepted
    ]
    filtered.new_results = [
        proposal
        for index, proposal in enumerate(step.new_results, start=1)
        if f"DRAFT-R{index}" in accepted
    ]
    return filtered


def _merge_draft_text(previous: str, current: str) -> str:
    previous = previous.strip()
    current = current.strip()
    if not previous:
        return current
    if not current or current == previous:
        return previous
    return f"{previous}\n\n{current}"


def _rescue_answer_from_solver_texts(responses: list[str]) -> str:
    for content in reversed(responses):
        data = extract_json_object(content or "")
        if isinstance(data, dict):
            answer = str(data.get("answer", "")).strip()
            if answer:
                return answer
            candidates = data.get("candidate_answers")
            if isinstance(candidates, list):
                for candidate in reversed(candidates):
                    value = str(candidate).strip()
                    if value:
                        return value
        boxed = re.findall(r"\\boxed\{([^{}]+)\}", content or "")
        if boxed:
            return f"\\boxed{{{boxed[-1].strip()}}}"
    return ""


def _record_accepted_claims(
    state: AgentState,
    draft,
    accepted: set[str],
    before_definitions: int,
    before_results: int,
) -> None:
    new_definitions = state.definitions[before_definitions:]
    new_results = state.derived_results[before_results:]
    definition_ids = {item.statement: item.id for item in new_definitions}
    result_ids = {item.statement: item.id for item in new_results}
    for claim in draft.claims:
        if claim.id not in accepted:
            continue
        authoritative_id = (
            definition_ids.get(claim.statement)
            if claim.claim_type == "definition"
            else result_ids.get(claim.statement)
        )
        suffix = claim.id.removeprefix("DRAFT-")
        claim_id = f"DRAFT-v{draft.version}-{suffix}"
        dependencies = [
            (
                f"DRAFT-v{draft.version}-{dependency.removeprefix('DRAFT-')}"
                if dependency.startswith("DRAFT-")
                else dependency
            )
            for dependency in claim.depends_on
        ]
        if any(existing.id == claim_id for existing in state.accepted_claims):
            continue
        state.accepted_claims.append(
            AcceptedClaim(
                id=claim_id,
                claim_type=claim.claim_type,
                statement=claim.statement,
                source_draft_version=draft.version,
                authoritative_id=authoritative_id,
                depends_on=dependencies,
            )
        )


def _remove_committed_proposals(
    state: AgentState, step: ReasoningStep
) -> ReasoningStep:
    cleaned = step.model_copy(deep=True)
    known_definitions = {
        re.sub(r"\s+", "", item.statement)
        for item in state.definitions
        if item.status == "verified"
    }
    known_results = {
        re.sub(r"\s+", "", item.statement)
        for item in state.derived_results
        if item.status == "verified"
    }
    cleaned.new_definitions = [
        item
        for item in cleaned.new_definitions
        if re.sub(r"\s+", "", item.statement) not in known_definitions
    ]
    cleaned.new_results = [
        item
        for item in cleaned.new_results
        if re.sub(r"\s+", "", item.statement) not in known_results
    ]
    return cleaned


def _route_fingerprint(
    state: AgentState, task: Task, reason: str, category: str
) -> str:
    guidance = next(
        (item for item in reversed(state.strategy_guidance) if item.status == "active"),
        None,
    )
    methods = guidance.core_methods[:3] if guidance else []
    source = "|".join(
        [
            task.kind,
            re.sub(r"\s+", " ", task.objective).strip().lower(),
            ",".join(methods).lower(),
            category,
            re.sub(r"\s+", " ", reason).strip().lower()[:240],
        ]
    )
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]
    return f"route:{task.kind}:{category}:{digest}"


def _normalize_problem_fact_payload(raw_fact: dict) -> dict:
    fact = dict(raw_fact)
    allowed = {"given_value", "relation", "domain_constraint", "condition", "target"}
    fact_type = str(fact.get("fact_type", "")).strip()
    if fact_type not in allowed:
        if "target" in fact_type or "求" in str(fact.get("statement", "")):
            fact["fact_type"] = "target"
        elif "relation" in fact_type or "definition" in fact_type or "field" in fact_type:
            fact["fact_type"] = "condition"
        else:
            fact["fact_type"] = "condition"
    return fact


def _normalize_task_payload(raw_task: dict) -> dict:
    task = dict(raw_task)
    if "task_type" not in task and "kind" in task:
        task["task_type"] = task.get("kind")
    if "kind" not in task and "task_type" in task:
        task["kind"] = task.get("task_type")
    if "statement" not in task:
        task["statement"] = (
            task.get("objective")
            or task.get("description")
            or task.get("task")
            or ""
        )
    if "objective" not in task:
        task["objective"] = task.get("statement", "")
    if "depends_on_tasks" not in task and "depends_on" in task:
        task["depends_on_tasks"] = task.get("depends_on")
    if "depends_on" not in task and "depends_on_tasks" in task:
        task["depends_on"] = task.get("depends_on_tasks")
    allowed = {
        "formalize",
        "derive",
        "compute",
        "verify",
        "repair",
        "replan",
        "finalize",
        "case_analysis",
        "verify_candidate",
        "completeness",
        "lower_bound",
        "upper_bound",
        "construction",
        "proof",
        "sanity_check",
    }
    task_type = str(task.get("task_type", "")).strip()
    if task_type not in allowed:
        text = f"{task_type} {task.get('statement', '')}".lower()
        if "count" in text or "compute" in text or "calculate" in text:
            task["task_type"] = "compute"
        elif "complete" in text or "all" in text:
            task["task_type"] = "completeness"
        elif "proof" in text or "prove" in text:
            task["task_type"] = "proof"
        else:
            task["task_type"] = "derive"
    task["kind"] = task["task_type"]
    task.setdefault("priority", 0)
    task.setdefault("required", True)
    task.setdefault("depends_on_tasks", [])
    task.setdefault("depends_on", task.get("depends_on_tasks") or [])
    task["objective"] = str(task.get("objective") or task.get("statement") or "")
    task["statement"] = str(task.get("statement") or task.get("objective") or "")
    return task


def _strategy_output_to_guidance(
    state: AgentState,
    output: StrategyOutput,
) -> StrategyGuidance:
    return StrategyGuidance(
        id=f"S{len(state.strategy_guidance) + 1}",
        status="active",
        problem_type=output.problem_type or state.problem_type,
        selected_skill_ids=[str(item) for item in output.selected_skill_ids],
        core_methods=[str(item) for item in output.core_methods],
        phase_plan=[str(item) for item in output.phase_plan],
        risk_controls=[str(item) for item in output.risk_controls],
        do_not=[str(item) for item in output.do_not],
        first_step_instruction=output.first_step_instruction,
        sanitization_warnings=list(output.sanitization_warnings),
    )


def _parse_strategy_output(content: str) -> StrategyOutput | None:
    data = extract_json_object(content or "")
    if not data:
        return None
    return StrategyOutput.model_validate(_sanitize_strategy_payload(data))


def _build_strategy_preprocess_context_message(
    state: AgentState,
    metadata: dict | None,
) -> str:
    verified_problem_facts = [
        pf.model_dump() for pf in state.problem_facts if pf.status == "verified"
    ]
    completion_requirements = [req.model_dump() for req in state.requirements]
    tasks = [task.model_dump() for task in state.tasks]

    sections = [
        "请根据以下题目、已验证事实和任务状态，生成本题 StrategyOutput JSON。",
        "",
        "题目：",
        state.problem,
        "",
        "领域分类：",
        f"主领域：{state.problem_type}",
        "辅助领域：" + (
            "、".join(state.secondary_problem_types)
            if state.secondary_problem_types
            else "无"
        ),
        f"分类置信度：{state.classification_confidence}",
        f"分类理由：{state.classification_reason or '无'}",
        "",
        "已验证 ProblemFact：",
        json.dumps(verified_problem_facts, ensure_ascii=False),
        "",
        "CompletionRequirement：",
        json.dumps(completion_requirements, ensure_ascii=False),
        "",
        "当前 Task：",
        json.dumps(tasks, ensure_ascii=False),
        "",
        "Task 修正契约：",
        "可用 initial_task_revisions 修正调度层 Task；不得泄漏答案或倾向具体选项，不得创建 P/D/R/C。",
        "",
        "输出要求：",
        "只输出一个合法 StrategyOutput JSON。",
    ]
    return "\n".join(sections)


def _build_strategy_skill_reference_message(
    selected_skills: list[SelectedStrategySkill],
) -> str:
    if not selected_skills:
        return "主技能参考文档：\n无\n\n辅助技能参考文档：\n无"

    primary = selected_skills[0]
    sections = [
        "以下是本题可参考的技能手册。它们只是方法提示，不是题面事实、已证明结论或答案来源。",
        "",
        "主技能参考文档：",
        f"【{primary.category}】",
        primary.prompt,
        "",
        "辅助技能参考文档：",
    ]
    if len(selected_skills) == 1:
        sections.append("无")
        return "\n".join(sections)

    for skill in selected_skills[1:]:
        sections.extend([f"【{skill.category}】", skill.prompt, ""])
    return "\n".join(sections)


def _build_replanner_skill_reference_message(
    selected_skills: list[SelectedStrategySkill],
) -> str:
    if not selected_skills:
        return "完整技能参考文档：\n无"

    sections = [
        "以下是本题可参考的完整技能手册。它们只用于帮助重选路线，不是题面事实、已证明结论或答案来源。",
        "",
        "完整技能参考文档：",
    ]
    for index, skill in enumerate(selected_skills):
        role = "主技能" if index == 0 else "辅助技能"
        sections.extend([f"{role}【{skill.category}】", skill.prompt, ""])
    return "\n".join(sections).rstrip()


def _build_replanner_context_message(
    state: AgentState,
    blocked_task: Task,
    verification: StepVerification,
) -> str:
    recent_errors = [error.model_dump() for error in state.error_memory[-8:]]
    active_guidance = [
        guidance.model_dump()
        for guidance in state.strategy_guidance
        if guidance.status == "active"
    ]
    verified_problem_facts = [
        pf.model_dump() for pf in state.problem_facts if pf.status == "verified"
    ]
    verified_definitions = [
        definition.model_dump()
        for definition in state.definitions
        if definition.status == "verified"
    ]
    verified_results = [
        result.model_dump()
        for result in state.derived_results
        if result.status == "verified"
    ]
    candidates = [candidate.model_dump() for candidate in state.candidates]
    unsatisfied_requirements = [
        req.model_dump() for req in state.requirements if req.status == "unsatisfied"
    ]
    open_tasks = [
        task.model_dump()
        for task in state.tasks
        if task.status in {"open", "active", "blocked"}
    ]
    return "\n".join(
        [
            "请根据以下结构化上下文生成 ReplanOutput JSON。",
            "",
            "## Problem",
            state.problem,
            "",
            "## Problem Type",
            state.problem_type,
            "",
            "## Blocked Task",
            json.dumps(blocked_task.model_dump(), ensure_ascii=False),
            "",
            "## Last Verification",
            json.dumps(verification.model_dump(), ensure_ascii=False),
            "",
            "## Recent Error Memory",
            _render_json_lines(recent_errors),
            "",
            "## Active Strategy Guidance",
            _render_json_lines(active_guidance[-1:] if active_guidance else []),
            "",
            "## VERIFIED Problem Facts",
            _render_json_lines(verified_problem_facts),
            "",
            "## VERIFIED Definitions",
            _render_json_lines(verified_definitions),
            "",
            "## VERIFIED Derived Results",
            _render_json_lines(verified_results),
            "",
            "## Candidates",
            _render_json_lines(candidates),
            "",
            "## Unsatisfied Completion Requirements",
            _render_json_lines(unsatisfied_requirements),
            "",
            "## Open Or Blocked Tasks",
            _render_json_lines(open_tasks),
            "",
            "## Replan Instruction",
            "生成 1 到 3 个新的调度任务，必须避开 Recent Error Memory 中反复失败的路线；不要输出答案或已证明结论。",
        ]
    )


def _render_json_lines(items: list[dict]) -> str:
    if not items:
        return "(none)"
    return "\n".join(json.dumps(item, ensure_ascii=False) for item in items)


def _replan_output_to_tasks(
    state: AgentState,
    blocked_task: Task,
    output: ReplanOutput,
) -> list[Task]:
    tasks: list[Task] = []
    used_objectives: set[str] = set()
    for raw_task in output.new_tasks[:3]:
        if not isinstance(raw_task, dict):
            continue
        task_payload = _sanitize_replan_task_payload(raw_task)
        objective = task_payload.get("objective", "")
        if not objective or _contains_strategy_answer_leak(objective):
            continue
        if _objectives_repeat_route(objective, blocked_task.objective):
            continue
        if objective in used_objectives:
            continue
        used_objectives.add(objective)
        tasks.append(
            Task(
                id=next_task_id(state, offset=len(tasks)),
                kind=task_payload["kind"],
                objective=objective,
                priority=int(task_payload.get("priority", 0) or 0),
                required=bool(task_payload.get("required", True)),
                status="open",
                depends_on=list(task_payload.get("depends_on") or []),
                requirement_ids=list(blocked_task.requirement_ids),
                created_by="replanner",
            )
        )
    return tasks


def _objectives_repeat_route(left: str, right: str) -> bool:
    def normalize(value: str) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff]+", "", value).lower()

    left_key = normalize(left)
    right_key = normalize(right)
    if not left_key or not right_key:
        return False
    if left_key == right_key:
        return True
    shorter, longer = sorted((left_key, right_key), key=len)
    return len(shorter) >= 12 and shorter in longer and len(shorter) / len(longer) >= 0.8


def _sanitize_replan_task_payload(raw_task: dict) -> dict:
    task = dict(raw_task)
    if "kind" not in task:
        task["kind"] = task.get("task_type", "replan")
    if "objective" not in task:
        task["objective"] = task.get("statement", "")
    if "depends_on" not in task:
        task["depends_on"] = task.get("depends_on_tasks", [])
    return _normalize_task_payload(task)


def _build_fallback_route_reset_task(
    state: AgentState,
    task: Task,
    reason: str,
) -> Task:
    objective = task.objective.strip()
    prefix = "切换路线："
    while objective.startswith(prefix):
        objective = objective[len(prefix) :].strip()
    return Task(
        id=next_task_id(state),
        kind="replan",
        objective=f"{prefix}{objective}",
        priority=task.priority + 5,
        requirement_ids=list(task.requirement_ids),
        created_by="replanner",
        blocked_reason=reason,
    )


def _sanitize_domain_classification(
    output: DomainClassificationOutput,
) -> DomainClassificationOutput:
    primary = normalize_skill_category(output.primary_category)
    secondary: list[str] = []
    for raw_category in output.secondary_categories:
        category = normalize_skill_category(raw_category)
        if (
            category in ALLOWED_SKILL_CATEGORIES
            and category != primary
            and category not in secondary
        ):
            secondary.append(category)
        if len(secondary) >= 2:
            break
    confidence = float(output.confidence or 0.0)
    confidence = min(1.0, max(0.0, confidence))
    return DomainClassificationOutput(
        primary_category=primary,
        secondary_categories=secondary,
        confidence=confidence,
        reason=str(output.reason or "")[:60],
    )


def _build_strategy_json_retry_message(error: str, response_excerpt: str) -> str:
    excerpt = " ".join(str(response_excerpt or "").split())[:1200]
    return (
        "上一条 strategy_preprocess 输出不是合法 StrategyOutput JSON，必须重新输出。\n"
        f"解析错误：{error[:1000]}\n"
        f"原始输出片段：{excerpt}\n\n"
        "请只重发一个 JSON 对象，不要解释，不要 Markdown。\n"
        "必须包含字段：problem_type, core_methods, phase_plan, risk_controls, "
        "do_not, first_step_instruction, initial_task_revisions。\n"
        "JSON 字符串内部不得出现未转义的英文双引号；中文引用请用 '单引号'、"
        "“中文引号” 或《书名号》。\n"
        "不得写答案、最终选项、候选答案或任何倾向具体选项的语句。\n"
        "initial_task_revisions.objective 是解题计划/阶段目标，可写比较对象、"
        "检查性质、计划方法或验证目标；不得写已完成结论、具体候选值、"
        "选项优劣、候选倾向或答案暗示。"
    )


def _build_json_regeneration_message(
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


def _apply_strategy_task_revisions(state: AgentState, output: StrategyOutput) -> dict:
    invalidated: list[str] = []
    created: list[str] = []
    dependency_warnings: list[str] = []
    revisions = []
    raw_revisions = (
        _normalize_macro_tasks(output.macro_tasks, output.execution_mode)
        if state.efficient_runtime
        else output.initial_task_revisions
    )
    if state.efficient_runtime and not raw_revisions:
        raw_revisions = _normalize_macro_tasks(
            output.initial_task_revisions, output.execution_mode
        )
    for raw_task in raw_revisions:
        if not isinstance(raw_task, dict):
            continue
        task_payload = _normalize_task_payload(raw_task)
        objective = str(task_payload.get("objective", "")).strip()
        if not objective or _contains_strategy_answer_leak(objective):
            continue
        revisions.append(task_payload)

    if not revisions and state.efficient_runtime:
        revisions = [
            {
                "kind": "proof" if output.execution_mode != "direct" else "derive",
                "objective": "完成主要推导并形成可独立审查的完整解答草稿",
                "priority": 100,
                "depends_on": [],
            }
        ]
    if (
        state.efficient_runtime
        and output.execution_mode != "direct"
        and len(revisions) == 1
    ):
        revisions.append(
            {
                "kind": "sanity_check",
                "objective": "复核关键推导、边界与完备性，并整理最终可判分结论",
                "priority": max(0, int(revisions[0].get("priority", 100)) - 10),
                "depends_on": [],
            }
        )
    if not revisions:
        return {
            "invalidated_tasks": [],
            "created_tasks": [],
            "dependency_warnings": [],
        }

    for task in state.tasks:
        should_replace = state.efficient_runtime or _is_generic_task_objective(task.objective)
        if task.status in {"open", "active"} and should_replace:
            task.status = "invalid"
            task.invalidated_by = "strategy_guidance"
            invalidated.append(task.id)

    for payload in revisions:
        kind = payload["kind"]
        objective = payload["objective"]
        duplicate = next(
            (
                task
                for task in state.tasks
                if task.kind == kind
                and task.objective.strip() == objective.strip()
                and task.status in {"open", "active", "done"}
            ),
            None,
        )
        if duplicate is not None:
            continue
        task_id = f"T{len(state.tasks) + 1}"
        dependencies, warnings = _resolve_strategy_task_dependencies(
            state,
            payload.get("depends_on") or [],
            task_id=task_id,
            earlier_created_task_ids=created,
        )
        dependency_warnings.extend(warnings)
        task = Task(
            id=task_id,
            kind=kind,
            objective=objective,
            priority=int(payload.get("priority", 0) or 0),
            required=bool(payload.get("required", True)),
            status="open",
            depends_on=dependencies,
            created_by="strategy",
        )
        state.tasks.append(task)
        created.append(task.id)

    if state.efficient_runtime and created:
        first = next((task for task in state.tasks if task.id == created[0]), None)
        if first is not None:
            activate_task(first)

    return {
        "invalidated_tasks": invalidated,
        "created_tasks": created,
        "dependency_warnings": dependency_warnings,
    }


def _resolve_strategy_task_dependencies(
    state: AgentState,
    raw_dependencies: object,
    *,
    task_id: str,
    earlier_created_task_ids: list[str],
) -> tuple[list[str], list[str]]:
    """Resolve strategy dependency aliases without admitting unknown IDs or cycles."""

    if not isinstance(raw_dependencies, list):
        return [], [f"{task_id}: depends_on is not a list and was discarded"]
    verified_evidence = {
        item.id
        for item in [*state.problem_facts, *state.definitions, *state.derived_results]
        if item.status == "verified"
    }
    verified_candidates = {
        candidate.id for candidate in state.candidates if candidate.status == "verified"
    }
    satisfied_requirements = {
        requirement.id
        for requirement in state.requirements
        if requirement.status == "satisfied"
    }
    completed_tasks = {task.id for task in state.tasks if task.status == "done"}
    allowed_static = (
        verified_evidence
        | verified_candidates
        | satisfied_requirements
        | completed_tasks
    )
    allowed_prior_tasks = set(earlier_created_task_ids)
    resolved: list[str] = []
    warnings: list[str] = []
    for raw_dependency in raw_dependencies:
        dependency = str(raw_dependency).strip()
        if not dependency:
            continue
        normalized = dependency
        alias = re.match(r"^(T\d+)(?:[_:\-].*)?$", dependency, re.IGNORECASE)
        if alias:
            normalized = alias.group(1).upper()
        if normalized in allowed_static or normalized in allowed_prior_tasks:
            if normalized != task_id and normalized not in resolved:
                resolved.append(normalized)
            continue
        warnings.append(
            f"{task_id}: discarded unknown, future, invalid, or cyclic dependency {dependency}"
        )
    return resolved, warnings


def _sanitize_strategy_payload(data: dict) -> dict:
    sanitized = dict(data)
    removed_items: list[str] = []
    list_fields = ("core_methods", "phase_plan", "risk_controls", "do_not")
    for field in list_fields:
        value = sanitized.get(field)
        if not isinstance(value, list):
            sanitized[field] = []
            continue
        kept = []
        for item in value:
            text = str(item)
            if _contains_unproved_strategy_candidate(text):
                removed_items.append(text)
                continue
            kept.append(text)
        sanitized[field] = kept

    first_step = sanitized.get("first_step_instruction", "")
    if not isinstance(first_step, str):
        sanitized["first_step_instruction"] = ""
    elif _contains_unproved_strategy_candidate(first_step):
        removed_items.append(first_step)
        sanitized["first_step_instruction"] = (
            "先整理题目条件、定义必要变量，并建立目标表达式；不要猜最终答案。"
        )

    if removed_items:
        risk_controls = sanitized.get("risk_controls")
        if not isinstance(risk_controls, list):
            risk_controls = []
        risk_controls.append(
            "策略预处理曾包含具体最终常数、候选答案或 known result，相关内容已清除；正式解题不得采用这些候选，除非在 solve_step 中完成推导证明。"
        )
        sanitized["risk_controls"] = risk_controls

        do_not = sanitized.get("do_not")
        if not isinstance(do_not, list):
            do_not = []
        do_not.append("不要把策略预处理中的候选常数或 known result 当作已证明结论。")
        sanitized["do_not"] = do_not
        sanitized["sanitization_warnings"] = [
            "removed_unproved_candidate_or_known_result"
        ]

    sanitized.setdefault("problem_type", "unknown")
    if sanitized.get("execution_mode") not in {"direct", "draft", "macro"}:
        sanitized["execution_mode"] = "draft"
    selected_skill_ids = sanitized.get("selected_skill_ids")
    if not isinstance(selected_skill_ids, list):
        sanitized["selected_skill_ids"] = []
    else:
        sanitized["selected_skill_ids"] = [str(item) for item in selected_skill_ids]
    sanitized.setdefault("core_methods", [])
    sanitized.setdefault("phase_plan", [])
    sanitized.setdefault("risk_controls", [])
    sanitized.setdefault("do_not", [])
    sanitized.setdefault("first_step_instruction", "")
    sanitized["initial_task_revisions"] = _sanitize_strategy_task_revisions(
        sanitized.get("initial_task_revisions")
    )
    sanitized["macro_tasks"] = _sanitize_strategy_task_revisions(
        sanitized.get("macro_tasks")
    )
    sanitized.setdefault("sanitization_warnings", [])
    return sanitized


def _normalize_macro_tasks(raw_tasks: object, execution_mode: str) -> list[dict]:
    tasks = _sanitize_strategy_task_revisions(raw_tasks)
    kept: list[dict] = []
    seen: set[str] = set()
    micro_patterns = (
        "定义变量",
        "重命名",
        "改写符号",
        "抄写",
        "机械转写",
        "尝试猜测",
    )
    for task in tasks:
        objective = str(task.get("objective", "")).strip()
        normalized = re.sub(r"\s+", "", objective).lower()
        if not normalized or normalized in seen:
            continue
        if any(pattern in normalized for pattern in micro_patterns) and len(objective) < 24:
            continue
        seen.add(normalized)
        kept.append(task)
    limit = 1 if execution_mode == "direct" else 4
    return kept[:limit]


def _sanitize_strategy_task_revisions(raw_revisions: object) -> list[dict]:
    if not isinstance(raw_revisions, list):
        return []
    revisions: list[dict] = []
    for raw_task in raw_revisions:
        if not isinstance(raw_task, dict):
            continue
        task = _normalize_task_payload(raw_task)
        objective = str(task.get("objective", "")).strip()
        if not objective or _contains_strategy_answer_leak(objective):
            continue
        revisions.append(
            {
                "kind": task["kind"],
                "objective": objective,
                "priority": int(task.get("priority", 0) or 0),
                "depends_on": list(task.get("depends_on") or []),
            }
        )
    return revisions


_UNPROVED_STRATEGY_CANDIDATE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\\boxed",
        r"(?:候选答案|候选常数|最终答案|最终常数)",
        r"(?:answer|constant)\s*(?:is|=|:)",
        r"(?:minimum|minimal|maximum|maximal|optimum|optimal).{0,24}(?:is|=|:)",
        r"\b(?:T|C|K|k|x|n|m)\s*(?:=|≈|~=|<=|>=|<|>|≤|≥|\\le|\\ge)\s*[-+]?\d",
        r"(?:known result|well-known|standard result|folklore|known theorem)",
        r"(?:众所周知|已知结论|经典结论|标准结论|著名结论)",
        r"(?:golden ratio|黄金分割|phi|φ)",
        r"(?:sqrt|√)\s*[\({]?\s*\d",
    )
)


def _contains_unproved_strategy_candidate(text: str) -> bool:
    if _is_negative_instruction(text):
        return False
    return any(pattern.search(text) for pattern in _UNPROVED_STRATEGY_CANDIDATE_PATTERNS)


_STRATEGY_ANSWER_LEAK_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\\boxed",
        r"(?:答案|候选答案|正确选项|应选|选择)\s*(?:是|为|:|：)?\s*[A-H]",
        r"[A-H]\s*(?:是|为)\s*(?:正确|答案|最优|最佳|最合适)",
        r"(?:最合适|最优|最佳|正确).{0,12}(?:选项|答案|候选)",
        r"(?:answer|correct option|choose|select)\s*(?:is|=|:)\s*[A-H]",
    )
)


def _contains_strategy_answer_leak(text: str) -> bool:
    if _is_negative_instruction(text):
        return False
    return any(pattern.search(text) for pattern in _STRATEGY_ANSWER_LEAK_PATTERNS)


def _is_negative_instruction(text: str) -> bool:
    normalized = str(text or "").lower()
    negative_markers = ("不要", "不得", "禁止", "不能", "avoid", "do not", "don't")
    return any(marker in normalized for marker in negative_markers)


def _is_generic_task_objective(objective: str) -> bool:
    text = " ".join(str(objective or "").split())
    generic_phrases = (
        "基于原题和已验证事实推进求解",
        "推进完成条件",
        "继续推进求解",
        "解决给定数学问题",
    )
    return any(phrase in text for phrase in generic_phrases)


def _normalize_reasoning_step_payload(
    data: dict,
    state: AgentState,
    current_task_id: str | None = None,
) -> dict:
    normalized = dict(data)
    ensure_tasks_from_tasks(state)
    current_task = choose_active_task(state) or choose_open_task(state)
    normalized.setdefault("type", "reasoning_step")
    if not str(normalized.get("current_task", "")).strip():
        normalized["current_task"] = current_task_id or (
            current_task.id if current_task else ""
        )
    normalized.setdefault("used_facts", [])
    normalized.setdefault("used_definitions", [])
    normalized.setdefault("used_results", [])
    normalized.setdefault("candidate_answers", [])
    normalized.setdefault("new_tasks", [])
    normalized.setdefault("closed_tasks", [])
    normalized.setdefault("request_finalization", False)

    new_definitions = []
    for proposal in normalized.get("new_definitions") or []:
        if not isinstance(proposal, dict):
            continue
        item = dict(proposal)
        statement = item.get("statement") or item.get("definition") or item.get("term") or ""
        purpose = item.get("purpose") or item.get("justification") or item.get("term") or ""
        new_definitions.append(
            {
                "definition_type": item.get("definition_type") or "notation",
                "statement": statement,
                "purpose": purpose,
                "depends_on": item.get("depends_on") or [],
            }
        )
    normalized["new_definitions"] = new_definitions

    new_results = []
    for proposal in normalized.get("new_results") or []:
        if not isinstance(proposal, dict):
            continue
        item = dict(proposal)
        new_results.append(
            {
                "result_type": item.get("result_type") or "derived_fact",
                "statement": item.get("statement") or item.get("conclusion") or "",
                "justification": item.get("justification") or item.get("reason") or "",
                "depends_on": item.get("depends_on") or [],
            }
        )
    normalized["new_results"] = new_results

    new_tasks = []
    for proposal in normalized.get("new_tasks") or []:
        if isinstance(proposal, str):
            # A bare SG/T id is a reference to an existing task, not a new task proposal.
            continue
        if not isinstance(proposal, dict):
            continue
        item = _normalize_task_payload(proposal)
        if not str(item.get("statement", "")).strip():
            continue
        new_tasks.append(
            {
                "task_type": item["task_type"],
                "statement": item["statement"],
                "priority": item.get("priority", 0),
                "required": item.get("required", True),
                "depends_on_tasks": item.get("depends_on_tasks") or [],
            }
        )
    normalized["new_tasks"] = new_tasks

    if "step_summary" not in normalized or not str(normalized.get("step_summary", "")).strip():
        if new_results:
            normalized["step_summary"] = str(new_results[0].get("statement", ""))[:160]
        elif new_definitions:
            normalized["step_summary"] = str(new_definitions[0].get("statement", ""))[:160]
        else:
            normalized["step_summary"] = "本轮提出一个 ReasoningStep proposal"

    closed_tasks = []
    for item in normalized.get("closed_tasks") or []:
        if isinstance(item, str):
            closed_tasks.append(item)
        elif isinstance(item, dict) and item.get("id"):
            closed_tasks.append(str(item["id"]))
    normalized["closed_tasks"] = closed_tasks
    return normalized


def _maybe_add_candidate_extraction_task(state: AgentState) -> Task | None:
    unfinished_required = [
        task
        for task in state.tasks
        if task.status in {"open", "active", "blocked"} and task.kind != "verify"
    ]
    if unfinished_required:
        return None
    if any(candidate.status in {"candidate", "verified", "conflict"} for candidate in state.candidates):
        return None
    if any(
        task.kind == "verify"
        and task.status in {"open", "active"}
        and "最终候选答案" in task.objective
        for task in state.tasks
    ):
        return None
    task = Task(
        id=f"T{len(state.tasks) + 1}",
        kind="verify",
        objective=(
            "基于已 verified 的 ProblemFacts、Definitions、DerivedResults 提出最终候选答案；"
            "本步必须把候选写入 candidate_answers，并说明支持它的已验证结果。"
        ),
        status="open",
        priority=100,
        requirement_ids=["REQ_candidate_verified"],
    )
    state.tasks.append(task)
    ensure_tasks_from_tasks(state)
    return task


def _maybe_add_candidate_falsification_task(state: AgentState) -> Task | None:
    candidate = next(
        (
            item
            for item in state.candidates
            if item.status in {"candidate", "verified", "conflict"}
            and not any(
                task.created_by == "candidate_falsification"
                and task.candidate_id == item.id
                and task.candidate_source_draft_version == item.source_draft_version
                and task.status in {"open", "active", "done"}
                for task in state.tasks
            )
        ),
        None,
    )
    if candidate is None:
        return None
    task = Task(
        id=next_task_id(state),
        kind="sanity_check",
        objective=(
            "独立尝试推翻当前候选及其关键引理：优先构造反例、检查边界，"
            "并在可行时用小规模枚举或不同表示法核验；只有排除反例后才能收尾。"
        ),
        priority=120,
        required=True,
        candidate_id=candidate.id,
        candidate_source_draft_version=candidate.source_draft_version,
        created_by="candidate_falsification",
    )
    state.tasks.append(task)
    return task


def _next_task_after_accepted_draft(
    state: AgentState,
    current_task: Task,
    request_finalization: bool,
) -> Task | None:
    """Return the next dependency-ready task before opening candidate gates."""
    if state.execution_mode not in {"draft", "macro"}:
        return None
    if time_phase(state) != "normal":
        return None
    next_task = choose_open_task(state)
    if next_task is None or next_task.id == current_task.id:
        return None
    if request_finalization and not next_task.required:
        return None
    return next_task


def _build_json_retry_message(error: str, response_excerpt: str, task_id: str) -> str:
    message = build_invalid_json_retry_message(
        protocol_name="ReasoningStep JSON",
        error_message=error,
        response_excerpt=response_excerpt,
        context_label=f"当前任务：{task_id}",
        allowed_formats=[
            f"""{{
  "type": "reasoning_step",
  "current_task": "{task_id}",
  "used_facts": [],
  "used_definitions": [],
  "used_results": [],
  "step_summary": "...",
  "new_definitions": [],
  "new_results": [],
  "candidate_answers": [],
  "closed_tasks": [],
  "new_tasks": [],
  "request_finalization": false
}}"""
        ],
        extra_instructions=[
            "current_task 必须填写当前任务 id。",
            "不要把格式/schema 错误当作数学失败；只修正 JSON 结构并继续当前任务。",
            "new_tasks.statement 是解题计划/阶段目标，可写比较对象、检查性质、计划方法或验证目标。",
            "new_tasks.statement 不得写已完成结论、具体候选值、选项优劣、候选倾向或答案暗示。",
        ],
    )
    return message["content"]
