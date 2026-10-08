import json
import re
import time
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from reasoning_agent.custom.parsers.json_parser import extract_json_object
from reasoning_agent.custom2.model_call import ModelResponse, call_model
from reasoning_agent.custom2.models import AgentState
from reasoning_agent.custom2.program_checks import (
    ProgramCheck, check_expression, describe_checks, numeric_equalities, requested_checks,
)
from reasoning_agent.custom2.solution_parser import (
    create_draft, extract_candidate, infer_profile, render_solution, validate_extraction,
)
from reasoning_agent.custom2.strategy_skills import ALLOWED_SKILL_CATEGORIES, select_strategy_skills
from reasoning_agent.custom2.text_audit import parse_narrative_audit
from reasoning_agent.custom2.text_models import (
    AnswerExtraction, AuditRecord, NarrativeAudit, ProblemProfile, SolutionDraft, TextCandidate,
)
from reasoning_agent.custom2.text_prompts import (
    AUDIT_PROMPT, EXTRACTOR_PROMPT, FINALIZER_PROMPT, PLANNER_PROMPT, PROFILE_PROMPT,
    REPAIR_PROMPT, REPLANNER_PROMPT, SOLVER_PROMPT,
)
from reasoning_agent.custom2.text_tasks import TextTask, TextTaskLedger, TextTaskPlan, TextTaskReplan


ControlResult = TypeVar("ControlResult", bound=BaseModel)


class TextReasoningRuntime:
    def __init__(self, client: Any, config: Any) -> None:
        self.client = client
        self.config = config
        self.drafts: list[SolutionDraft] = []
        self.candidates: dict[str, TextCandidate] = {}
        self.audits: list[AuditRecord] = []
        self.trace: list[dict] = []
        self.debug_trace: list[dict] = []
        self.program_checks: dict[str, list[ProgramCheck]] = {}
        self.tool_call_count = 0
        self.ledger = TextTaskLedger(config.custom2_text_max_tasks)
        self.finalizing = False
        self.state = AgentState(problem="")
        self.stop_reason = "completed"
        self.thinking_mode = str(getattr(config, "custom2_text_thinking_mode", "false")).lower()
        if self.thinking_mode not in {"false", "true", "default"}:
            raise ValueError("custom2_text_thinking_mode must be false, true or default")

    def run(self, problem: str, metadata: dict | None = None) -> dict:
        self.drafts = []
        self.candidates = {}
        self.audits = []
        self.trace = []
        self.debug_trace = []
        self.program_checks = {}
        self.tool_call_count = 0
        self.ledger = TextTaskLedger(self.config.custom2_text_max_tasks)
        self.finalizing = False
        self.stop_reason = "completed"
        started = time.monotonic()
        self.state = AgentState(
            problem=problem, efficient_runtime=True, started_at=started,
            deadline_at=started + max(0.0, self.config.custom2_total_budget_seconds),
            finalize_reserve_seconds=max(0.0, self.config.custom2_finalize_reserve_seconds),
        )
        self._record("text_runtime_started", protocol="text", workflow="verified_subtasks")
        profile = self._profile(problem)
        self._record("problem_profile", domain=profile.domain, answer_mode=profile.answer_mode, obligations=profile.obligations)
        if not self._plan(profile):
            return self._finish(profile)
        while True:
            invalidated = self.ledger.invalidate_stale()
            if invalidated:
                self._record("tasks_invalidated", task_ids=invalidated, reason="stale_dependencies")
            if self.ledger.complete():
                final, review = self._finalize(profile)
                if final is not None and review is not None and review.verdict == "accept":
                    self.stop_reason = "verified_tasks_finalized"
                    return self._finish(profile, final)
                if final is None:
                    break
                target = self.ledger.tasks[self.ledger.ordered_task_ids()[-1]]
                if not self._replan(target, final, review, final_review=True):
                    break
                continue
            task = self.ledger.ready_task()
            if task is None:
                self.stop_reason = "no_ready_task"
                break
            if self.state.solver_call_count >= self.config.custom2_max_solver_calls:
                self.stop_reason = "solver_budget"
                break
            draft, review = self._solve_task(profile, task)
            if draft is None:
                break
            if review.verdict == "accept":
                continue
            if review.verdict in {"repair", "uncertain"} and task.repair_count < self.config.custom2_max_repairs:
                self._record("task_repair_scheduled", task_id=task.id, solution_id=draft.id)
                continue
            if not self._replan(task, draft, review):
                break
        return self._finish(profile)

    def _plan(self, profile: ProblemProfile) -> bool:
        skills = []
        if self.config.enable_strategy_preprocess:
            try:
                skills = select_strategy_skills(profile.domain, [], top_k=2)
            except OSError:
                self._record("strategy_skills_unavailable")
        self._record("strategy_preprocess_started", selected_skill_ids=[skill.id for skill in skills])
        messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": json.dumps({
                "problem": self.state.problem, "profile": profile.model_dump(),
                "strategy_materials": [{"category": skill.category, "content": skill.prompt} for skill in skills],
            }, ensure_ascii=False)},
        ]
        plan = self._structured(
            "planner", messages, TextTaskPlan,
            validate=lambda parsed: TextTaskLedger(self.config.custom2_text_max_tasks).initialize(parsed),
        )
        if plan is None:
            if self.stop_reason == "completed":
                self.stop_reason = "plan_unavailable"
            return False
        self.ledger.initialize(plan)
        self._record("task_plan_committed", task_ids=list(self.ledger.tasks), dependencies={
            task.id: list(task.dependencies) for task in self.ledger.tasks.values()
        })
        return True

    @staticmethod
    def _task_payload(task: TextTask) -> dict:
        return {
            "task_id": task.id, "objective": task.objective,
            "acceptance_criteria": list(task.acceptance_criteria), "depends_on": list(task.dependencies),
        }

    def _accepted_payload(self, task: TextTask | None = None) -> list[dict]:
        references = self.ledger.dependency_ids(task.id) if task else self.ledger.ordered_task_ids()
        drafts = {draft.id: draft for draft in self.drafts}
        results = []
        for reference in references:
            dependency = self.ledger.tasks[reference]
            if not self.ledger.is_current(reference):
                continue
            draft = drafts[dependency.accepted_solution_id]
            results.append({
                **self._task_payload(dependency), "solution_id": draft.id,
                "conclusion": re.sub(r"```check[ \t]*\n[\s\S]*?```", "", draft.text, flags=re.I).strip(),
                "program_checks": describe_checks(self.program_checks.get(draft.id, [])),
            })
        return results

    def _solve_task(self, profile: ProblemProfile, task: TextTask):
        versions = self.ledger.dependency_versions(task.id)
        parent = next((draft for draft in self.drafts if draft.id == task.latest_solution_id), None)
        previous_review = next((record.review for record in reversed(self.audits) if parent and record.solution_id == parent.id), None)
        action = "repair" if parent is not None else "solver"
        payload = {
            "problem": self.state.problem, "current_task": self._task_payload(task),
            "accepted_dependencies": self._accepted_payload(task),
            "strategy_advice_not_facts": self.ledger.strategy,
            "route_advice_not_facts": task.route,
        }
        if parent is not None:
            payload["draft_to_repair"] = parent.text
            payload["review_not_facts"] = previous_review.feedback if previous_review else "上次草稿没有通过审核，请核查当前目标。"
            payload["program_checks"] = describe_checks(self.program_checks.get(parent.id, []))
        messages = [
            {"role": "system", "content": REPAIR_PROMPT if parent else SOLVER_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        self._record("task_started", task_id=task.id, action=action, dependency_versions=dict(versions))
        response = self._call(action, messages, mathematical=True)
        if response is None:
            return None, None
        if parent is not None:
            task.repair_count += 1
        draft = create_draft(
            response.content, len(self.drafts) + 1, task_id=task.id, origin=action,
            parent_id=parent.id if parent else None, truncated=response.finish_reason == "length",
        )
        self.drafts.append(draft)
        task.latest_solution_id = draft.id
        self._record("draft_saved", task_id=task.id, solution_id=draft.id, parent_id=draft.parent_id, truncated=draft.truncated)
        review = None
        if draft.text.strip() and not draft.truncated:
            self._collect_checks(draft, draft.text)
            review = self._audit(self.state.problem, profile, draft, None, task=task)
        if review is None:
            review = NarrativeAudit(draft.id, "uncertain", "当前子任务草稿为空、截断或审核未完成，不能作为已验证结论。", "task_unreviewed")
        if review.verdict == "accept":
            try:
                self.ledger.accept(task.id, draft.id, versions)
            except ValueError:
                invalidated = self.ledger.invalidate([task.id])
                review = NarrativeAudit(draft.id, "uncertain", "任务所用依赖版本已失效，需要重新验收。", "stale_dependencies")
                self._record("tasks_invalidated", task_ids=invalidated, reason="stale_dependencies")
        self._save_review(draft, review)
        if review.verdict == "accept":
            self._record("task_accepted", task_id=task.id, solution_id=draft.id, dependency_versions=dict(versions))
        return draft, review

    def _save_review(self, draft: SolutionDraft, review: NarrativeAudit) -> None:
        record = AuditRecord(f"A{len(self.audits) + 1}", draft.id, review)
        self.audits.append(record)
        self._record("draft_audited", task_id=draft.task_id, solution_id=draft.id, audit_id=record.id,
                     verdict=review.verdict, routing_status=review.routing_status)

    def _replan(self, task: TextTask, draft: SolutionDraft, review: NarrativeAudit | None, *, final_review=False) -> bool:
        if self.state.solver_call_count >= self.config.custom2_max_solver_calls:
            self.stop_reason = "solver_budget"
            return False
        if self.state.model_call_count + 5 > self.config.max_model_calls:
            self.stop_reason = "model_budget"
            return False
        if self.state.model_replan_count >= self.config.custom2_max_model_replans:
            if not self._can_recover():
                self.stop_reason = "route_budget"
                return False
            self._record("route_budget_extended", task_id=task.id)
        self.state.model_replan_count += 1
        payload = {
            "problem": self.state.problem, "target_task": self._task_payload(task),
            "scope": "final" if final_review else "task",
            "active_tasks": [{**self._task_payload(item), "status": item.status} for item in self.ledger.tasks.values() if item.status != "superseded"],
            "accepted_results": self._accepted_payload(), "failed_draft_not_evidence": draft.text,
            "review_not_facts": review.feedback if review else "最终汇总尚未通过验证。",
            "program_checks": describe_checks(self.program_checks.get(draft.id, [])),
            "remaining_task_solves": self.config.custom2_max_solver_calls - self.state.solver_call_count,
        }
        messages = [
            {"role": "system", "content": REPLANNER_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        plan = self._structured("replanner", messages, TextTaskReplan, validate=lambda parsed: self.ledger.revised(task.id, parsed, final_review=final_review))
        if plan is None:
            if self.stop_reason == "completed":
                self.stop_reason = "replan_unavailable"
            return False
        previous_ids = set(self.ledger.tasks)
        self.ledger, invalidated, replacement = self.ledger.revised(task.id, plan, final_review=final_review)
        for reference in plan.invalidate_task_ids:
            if self.ledger.tasks[reference].status != "superseded":
                self.ledger.tasks[reference].route = "因后续审核需要回查此前结论。待核查建议：" + plan.route
        self._record("tasks_invalidated", task_ids=invalidated, reason="replan")
        self._record("task_replanned", old_task_id=task.id, replacement_task_id=replacement,
                     new_task_ids=[reference for reference in self.ledger.tasks if reference not in previous_ids],
                     model_replan_count=self.state.model_replan_count)
        return True

    def _finalize(self, profile: ProblemProfile):
        evidence = self._accepted_payload()
        snapshot = [(item["task_id"], item["solution_id"]) for item in evidence]
        self._record("finalization_started", accepted_task_ids=[item["task_id"] for item in evidence])
        self.finalizing = True
        try:
            messages = [
                {"role": "system", "content": FINALIZER_PROMPT},
                {"role": "user", "content": json.dumps({
                    "problem": self.state.problem, "profile": profile.model_dump(), "accepted_results": evidence,
                }, ensure_ascii=False)},
            ]
            response = self._call("finalizer", messages, mathematical=False)
            if response is None:
                return None, None
            draft = create_draft(response.content, len(self.drafts) + 1, origin="finalizer", truncated=response.finish_reason == "length")
            self.drafts.append(draft)
            candidate = extract_candidate(draft)
            if candidate is None and draft.text.strip() and not draft.truncated and profile.answer_mode != "proof":
                candidate = self._extract(draft)
            if candidate is not None:
                self.candidates[draft.id] = candidate
                self._record("candidate_registered", solution_id=draft.id, candidate_id=candidate.id, source=candidate.source)
            review = None
            if draft.text.strip() and not draft.truncated:
                self._collect_checks(draft, draft.text)
                review = self._audit(self.state.problem, profile, draft, candidate)
            if review is None:
                review = NarrativeAudit(draft.id, "uncertain", "最终汇总未完成验证。", "final_unreviewed")
            if not self.ledger.complete() or snapshot != [(item["task_id"], item["solution_id"]) for item in self._accepted_payload()]:
                review = NarrativeAudit(draft.id, "uncertain", "汇总所用依赖已失效，需要重新核查。", "stale_final_dependencies")
            self._save_review(draft, review)
            return draft, review
        finally:
            self.finalizing = False

    def _can_recover(self) -> bool:
        if not self.config.custom2_text_budget_recovery:
            return False
        if self.state.solver_call_count >= self.config.custom2_max_solver_calls:
            return False
        if self.state.model_call_count + 5 > self.config.max_model_calls:
            return False
        durations = [event["duration_seconds"] for event in self.debug_trace if event.get("type") == "model_call_metrics"]
        estimated_round = max(60.0, 2 * sum(durations) / max(1, len(durations)))
        remaining = self.state.deadline_at - time.monotonic()
        reserve = max(self.state.finalize_reserve_seconds, self.config.custom2_convergence_reserve_seconds)
        return remaining > reserve + estimated_round

    def _collect_checks(self, draft: SolutionDraft, text: str) -> None:
        if not self.config.custom2_text_program_checks:
            return
        checks = self.program_checks.setdefault(draft.id, [])
        seen = {(check.expression, check.source) for check in checks}
        requests = [(expression, "requested") for expression in requested_checks(text)]
        if text == draft.text:
            requests += [(expression, "numeric_equality") for expression in numeric_equalities(text)]
        for expression, source in requests:
            if (expression, source) in seen:
                continue
            reserve = 0.0 if self.finalizing else self.state.finalize_reserve_seconds
            remaining = self.state.deadline_at - time.monotonic() - reserve
            if self.tool_call_count >= self.config.max_tool_calls or remaining <= 0:
                self._record("program_check_budget", solution_id=draft.id)
                break
            self.tool_call_count += 1
            check = check_expression(
                expression, source, max_steps=self.config.custom2_text_check_max_steps,
                timeout=min(self.config.custom2_text_check_timeout_seconds, remaining),
            )
            checks.append(check)
            seen.add((expression, source))
            self._record(
                "program_check_completed", solution_id=draft.id, source=source,
                status=check.status, contradiction=check.contradiction, tool_call_count=self.tool_call_count,
            )

    def _profile(self, problem: str) -> ProblemProfile:
        messages = [
            {"role": "system", "content": PROFILE_PROMPT},
            {"role": "user", "content": json.dumps({
                "problem": problem, "domains": list(ALLOWED_SKILL_CATEGORIES),
            }, ensure_ascii=False)},
        ]
        proposed = self._structured("profile", messages, ProblemProfile)
        return infer_profile(problem, proposed)

    @staticmethod
    def _draft_payload(draft: SolutionDraft) -> dict:
        return {
            "solution_id": draft.id,
            "paragraphs": [{"id": paragraph.id, "text": paragraph.text} for paragraph in draft.paragraphs],
        }

    def _extract(self, draft: SolutionDraft) -> TextCandidate | None:
        if not getattr(self.config, "custom2_text_extract_answer", True):
            return None
        messages = [
            {"role": "system", "content": EXTRACTOR_PROMPT},
            {"role": "user", "content": json.dumps(self._draft_payload(draft), ensure_ascii=False)},
        ]
        result = self._structured(
            "extractor", messages, AnswerExtraction, attempts=1,
            validate=lambda parsed: validate_extraction(draft, parsed),
        )
        return validate_extraction(draft, result) if result else None

    def _audit(
        self, problem: str, profile: ProblemProfile, draft: SolutionDraft,
        candidate: TextCandidate | None, *, task: TextTask | None = None,
    ) -> NarrativeAudit | None:
        payload = self._draft_payload(draft)
        payload.update({
            "problem": problem,
            "profile": {"domain": profile.domain, "answer_mode": profile.answer_mode} if task else profile.model_dump(),
            "scope": "task" if task else "final",
            "current_task": self._task_payload(task) if task else None,
            "accepted_results": self._accepted_payload(task),
            "candidate": {"id": candidate.id, "value": candidate.value} if candidate else None,
            "program_checks": describe_checks(self.program_checks.get(draft.id, [])),
            "program_checks_enabled": self.config.custom2_text_program_checks,
        })
        messages = [
            {"role": "system", "content": AUDIT_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        response = self._call("audit", messages, mathematical=False)
        if response is None:
            return None
        if requested_checks(response.content):
            self._collect_checks(draft, response.content)
            messages += [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": "程序计算结果如下。请核对其与原题的对应关系并完成审核，不再请求工具。\n"
                 + describe_checks(self.program_checks.get(draft.id, []))},
            ]
            followup = self._call("audit", messages, mathematical=False)
            if followup is None:
                return NarrativeAudit(draft.id, "uncertain", response.content, "tool_review_incomplete")
            response = followup
        review = parse_narrative_audit(
            response.content, draft, truncated=response.finish_reason == "length",
        )
        if requested_checks(response.content):
            return NarrativeAudit(draft.id, "uncertain", review.feedback, "tool_request_unresolved")
        if review.verdict == "accept" and any(check.contradiction for check in self.program_checks.get(draft.id, [])):
            return NarrativeAudit(
                draft.id, "repair", review.feedback + "\n草稿中数值等式与程序计算不一致；请修正或明确说明该等式只是被否定的假设。\n"
                + describe_checks(self.program_checks[draft.id]), "program_disagreement",
            )
        if review.verdict == "accept" and task is None and profile.answer_mode != "proof" and candidate is None:
            return NarrativeAudit(
                draft.id, "repair", review.feedback + "\n请在最终答案段明确给出全部所求结果。",
                "missing_candidate",
            )
        return review

    def _structured(
        self, role: str, messages: list[dict], schema: type[ControlResult], *,
        attempts: int = 2, validate: Callable[[ControlResult], Any] | None = None,
    ) -> ControlResult | None:
        for attempt in range(attempts):
            response = self._call(role, messages, mathematical=False)
            if response is None:
                return None
            try:
                if response.finish_reason == "length":
                    raise ValueError("truncated_control_response")
                payload = extract_json_object(response.content)
                parsed = schema.model_validate(payload)
                if validate is not None:
                    validate(parsed)
                return parsed
            except (ValueError, TypeError) as error:
                allowed_reasons = {
                    "empty_task_requirement", "invalid_dependency_order", "unknown_or_unaccepted_dependency",
                    "invalid_invalidation_target", "unknown_replan_target", "dependency_cycle", "task_limit",
                    "invalid_dependency", "truncated_control_response",
                }
                reason = str(error) if str(error) in allowed_reasons else "schema_or_source_invalid"
                self._record("control_response_invalid", role=role, attempt=attempt + 1, reason=reason)
                if attempt + 1 < attempts:
                    messages = messages + [{
                        "role": "user",
                        "content": "上次控制数据无效。请按当前系统协议重新输出指定 JSON，不增删字段；"
                        "任务依赖必须合法，抽取必须有原文来源，不重新解题。错误类型：" + reason,
                    }]
        return None

    def _call(self, role: str, messages: list[dict], *, mathematical: bool) -> ModelResponse | None:
        reserved_calls = 0 if self.finalizing else 2
        if self.state.model_call_count >= self.config.max_model_calls - reserved_calls:
            self.stop_reason = "model_budget"
            return None
        remaining = self.state.deadline_at - time.monotonic()
        reserve = 0.0 if self.finalizing else self.state.finalize_reserve_seconds
        if remaining <= reserve:
            self.stop_reason = "time_reserve"
            return None
        context_chars = sum(len(message["content"]) for message in messages)
        if context_chars > self.config.custom2_text_context_max_chars:
            self._record("context_limit", role=role, chars=context_chars)
            self.stop_reason = "context_limit"
            return None
        request = {
            "messages": messages,
            "temperature": 0.2 if mathematical else 0.0,
            "max_tokens": (
                min(self.config.custom2_solver_max_tokens, self.config.custom2_text_task_max_tokens)
                if mathematical else (self.config.custom2_finalizer_max_tokens if role == "finalizer" else self.config.custom2_text_control_max_tokens)
            ),
        }
        if not mathematical:
            request["thinking_mode"] = False
        elif self.thinking_mode != "default":
            request["thinking_mode"] = self.thinking_mode == "true"
        self.state.model_call_count += 1
        if mathematical:
            self.state.solver_call_count += 1
            if role == "repair":
                self.state.repair_count += 1
        started = time.monotonic()
        try:
            response = call_model(
                self.client, self.state, None, f"text_{role}", allow_finalize_reserve=self.finalizing, **request,
            )
        except Exception:
            self.stop_reason = "model_call_failed"
            self._record("model_call_failed", role=role)
            return None
        self._record("model_call_completed", role=role)
        usage = response.token_usage if isinstance(response.token_usage, dict) else {}
        self.debug_trace.append({
            "type": "model_call_metrics", "role": role,
            "duration_seconds": round(max(0.0, time.monotonic() - started), 3),
            "finish_reason": (
                response.finish_reason
                if response.finish_reason in {"stop", "length", "tool_calls"} else None
            ),
            "token_usage": {
                key: value for key, value in usage.items()
                if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
                and isinstance(value, int) and not isinstance(value, bool) and value >= 0
            },
        })
        return response

    def _record(self, event_type: str, **data: Any) -> None:
        self.trace.append({
            "type": event_type, **data,
            "model_call_count": self.state.model_call_count,
            "solver_call_count": self.state.solver_call_count,
        })

    def _finish(self, profile: ProblemProfile, selected: SolutionDraft | None = None) -> dict:
        if not self.ledger.complete() or (selected is not None and selected.origin != "finalizer"):
            selected = None
        review = next((record.review for record in reversed(self.audits) if selected and record.solution_id == selected.id), None)
        if review is None or review.verdict != "accept":
            selected = None
        self._record(
            "solution_selected", solution_id=selected.id if selected else None,
            review_status=review.verdict if selected else "incomplete",
            stop_reason=self.stop_reason, draft_count=len(self.drafts),
            repair_count=self.state.repair_count, resolve_count=self.state.model_replan_count,
            tool_call_count=self.tool_call_count,
            task_statuses={task.id: task.status for task in self.ledger.tasks.values()},
            selection_status="verified_tasks" if selected else "incomplete_tasks_or_final",
        )
        final = render_solution(selected, self.candidates.get(selected.id), profile) if selected else ""
        output = {
            "final_response": final or "未能完成全部必要子任务及最终验证，无法给出可靠最终答案。",
            "trace": _bounded_events(self.trace, self.config.max_trace_chars),
        }
        if self.config.emit_debug_trace:
            output["debug_trace"] = _bounded_events(self.debug_trace, self.config.max_trace_chars)
        return output


def _bounded_events(events: list[dict], max_chars: int) -> list[dict]:
    selected = []
    remaining = max(0, max_chars - 2)
    for event in reversed(events):
        cost = len(json.dumps(event, ensure_ascii=False)) + (2 if selected else 0)
        if cost > remaining:
            continue
        selected.append(event)
        remaining -= cost
    return list(reversed(selected))
