from __future__ import annotations

import json
import time
from typing import Any

from reasoning_agent.custom.parsers.answer_normalizer import detect_question_mode
from reasoning_agent.custom.parsers.final_answer_parser import ensure_boxed_final_response
from reasoning_agent.custom2.strategy_skills import (
    normalize_skill_category, retrieve_skill_material, skill_catalog,
)
from reasoning_agent.strategy_retrieval import (
    build_structure_messages, get_shared_strategy_retriever, normalize_retrieval_text,
)

from .action_registry import ANSWER_PRODUCING_ACTIONS, ACTION_REGISTRY, filter_available_actions
from .config import ActionGraphConfig
from .context import bounded_text, build_memory, source_packet
from .models import (
    AcceptedClaim, ActionDecision, ActionNode, ActionRuntimeState, AnswerCandidate,
    RouteFingerprint, RuntimeBudget,
)
from .strategy_cards import bound_card_text, build_strategy_cards, trace_results
from .interfaces import summarize_node
from .preprocessing import preprocess_problem
from .prompts import (
    executor_messages, finalizer_messages, model_preprocess_messages,
    emergency_guess_messages, planner_messages, profile_messages, reflector_messages,
    strategy_skill_messages,
)
from .tools import invoke_client, parse_action_result, parse_branches, parse_decision, parse_json, parse_reflection


class ActionGraphRuntime:
    """受严格预算约束的非递归 PRER 动作图运行时。"""

    def __init__(self, client: Any, config: ActionGraphConfig | object | None = None) -> None:
        self.client = client
        self.config = ActionGraphConfig.from_object(config)
        self.trace: list[dict[str, Any]] = []
        self.debug_trace: list[dict[str, Any]] = []
        self._pending: list[tuple[ActionDecision, int, str | None]] = []
        self._stage_elapsed: dict[str, float] = {}

    def run(self, problem: str, metadata: dict | None = None) -> dict[str, Any]:
        del metadata  # 平台 metadata，尤其是答案字段，绝不参与状态或模型上下文。
        started = time.monotonic()
        total = min(1200.0, max(0.0, self.config.action_total_budget_seconds))
        packet = preprocess_problem(problem)
        state = ActionRuntimeState(
            problem_packet=packet,
            budget=RuntimeBudget(started, started + total),
            subquestion_status={item.id: "pending" for item in packet.subquestions},
            answer_mode=detect_question_mode(problem),
        )
        self._record("action_runtime_started", workflow="action_graph_prer")
        self._record("offline_preprocess_completed", **packet.json_summary())
        stop_reason = ""
        try:
            decision = self._bootstrap(state)
            if decision is None:
                stop_reason = "bootstrap_failed"
            else:
                self._run_decision(state, decision)
            while not self._covered(state) and not stop_reason:
                if not self._may_start_node(state):
                    stop_reason = self._node_start_block_reason(state)
                    break
                if self._pending:
                    decision, depth, parent_id = self._pending.pop(0)
                    self._run_decision(state, decision, depth=depth, parent_id=parent_id)
                    continue
                decision = self._plan(state)
                if decision is None or decision.action == "finish":
                    stop_reason = "planner_finish_or_failed"
                    break
                self._run_decision(state, decision)
        except TimeoutError as exc:
            stop_reason = f"timeout:{type(exc).__name__}"
            self._record("budget_converged", reason=stop_reason)
        except Exception as exc:  # keep platform non-empty return contract
            stop_reason = f"timeout:{type(exc).__name__}" if self._recoverable(exc) else f"runtime_error:{type(exc).__name__}"
            self._record("runtime_error", error_type=type(exc).__name__, message=str(exc)[:300])
        final = self._finalize(state)
        status = self._status(state, final, stop_reason)
        self._record(
            "action_runtime_finished", solve_status=status, elapsed_seconds=round(time.monotonic() - started, 3),
            model_calls=state.budget.model_calls, node_attempts=state.budget.node_attempts,
            stop_reason=stop_reason or "completed",
        )
        output: dict[str, Any] = {
            "final_response": final
            or "基于当前可用材料生成的最佳努力结论：尚未形成可验证的数学对象。",
            "trace": self.trace,
            "solve_status": status,
        }
        if self.config.action_emit_debug_trace:
            output["debug_trace"] = self.debug_trace
        return output

    def _bootstrap(self, state: ActionRuntimeState) -> ActionDecision | None:
        target = next(iter(state.subquestion_status), "q1")
        problem, warnings = source_packet(state, self.config, target)
        for warning in warnings:
            self._record(warning, stage="bootstrap")
        actions = filter_available_actions(depth=0, remaining_seconds=state.budget.remaining(), rejected=set(), target_id=target, max_depth=self.config.action_max_branch_depth)
        try:
            preprocess = self._json_call(
                "model_preprocess", model_preprocess_messages(problem),
                self.config.action_model_preprocess_max_tokens,
                self.config.action_model_preprocess_timeout_seconds, state,
                self.config.action_model_preprocess_thinking_mode,
            )
            state.model_preprocess, _ = bounded_text(_json(preprocess), 12000)
            self._record("model_preprocess_completed", fields=list(preprocess.keys()))
        except Exception as exc:
            self._record("model_preprocess_failed", error_type=type(exc).__name__)
            state.model_preprocess = _json({"problem_restatement": problem, "subquestions": []})

        try:
            profile = self._json_call(
                "profile", profile_messages(problem, state.model_preprocess),
                self.config.action_profile_max_tokens,
                self.config.action_profile_timeout_seconds, state,
                self.config.action_profile_thinking_mode,
            )
            state.profile_context, _ = bounded_text(_json(profile), 6000)
            state.domain = normalize_skill_category(profile.get("domain"))
            state.answer_mode = str(profile.get("answer_mode") or state.answer_mode)
            state.risk_level = str(profile.get("risk_level") or "medium")
            self._record("profile_classified", domain=state.domain, answer_mode=state.answer_mode, risk_level=state.risk_level)
        except Exception as exc:
            self._record("profile_failed", error_type=type(exc).__name__)
            state.profile_context = _json({"domain": "unknown", "answer_mode": state.answer_mode, "risk_level": "medium"})

        self._retrieve_strategy_examples(state)

        try:
            catalog = skill_catalog()[:12000]
            strategy = self._json_call(
                "strategy", strategy_skill_messages(problem, state.model_preprocess, state.profile_context, catalog, actions, state.planner_strategy_cards),
                self.config.action_strategy_max_tokens,
                self.config.action_strategy_timeout_seconds, state,
                self.config.action_strategy_thinking_mode,
            )
            state.strategy_context, _ = bounded_text(_json(strategy), 12000)
            state.skill_domains = [normalize_skill_category(item) for item in strategy.get("skill_domains", []) if normalize_skill_category(item) != "unknown"][:2]
            state.skill_sections = [str(item) for item in strategy.get("skill_sections", []) if str(item).strip()][:8]
            decision = parse_decision(_json(strategy.get("initial_decision", {})), target)
            self._record("strategy_selected", action=decision.action, skill_domains=state.skill_domains, skill_sections=state.skill_sections[:8])
            return decision
        except Exception as exc:
            self._record("strategy_failed", error_type=type(exc).__name__)
            return self._safe_decision(target)

    def _plan(self, state: ActionRuntimeState) -> ActionDecision | None:
        target = next((key for key, value in state.subquestion_status.items() if value != "covered"), "q1")
        accepted, failures, warnings = build_memory(state, self.config)
        for warning in warnings:
            self._record(warning, stage="planner")
        rejected = {(item.action, item.target_id) for item in state.rejected_routes}
        actions = filter_available_actions(depth=0, remaining_seconds=state.budget.remaining(), rejected=rejected, target_id=target, max_depth=self.config.action_max_branch_depth)
        rethink_count = sum(1 for node in state.nodes.values() if node.decision.action == "rethink")
        if rethink_count >= self.config.action_max_rethinks:
            actions = [item for item in actions if item.name != "rethink"]
            self._record("action_disabled", action="rethink", reason="rethink_limit")
        if not actions:
            return None
        problem, warnings = source_packet(state, self.config, target)
        for warning in warnings:
            self._record(warning, stage="planner")
        del problem  # Planner receives target/state; Executor receives exact source packet.
        try:
            text = self._call("planner", planner_messages(state.problem_packet.compact_view, target, accepted, failures, actions, state.profile_context, state.strategy_context), self.config.action_planner_max_tokens, self.config.action_planner_timeout_seconds, self.config.action_planner_thinking_mode, state)
            decision = parse_decision(text, target)
        except Exception as exc:
            if self._recoverable(exc):
                self._record("planner_network_failed", error_type=type(exc).__name__)
                return self._safe_decision(target)
            self._record("planner_protocol_failed", error_type=type(exc).__name__)
            if self._planner_repair_allowed(state):
                try:
                    messages = planner_messages(state.problem_packet.compact_view, target, accepted, failures, actions, state.profile_context, state.strategy_context)
                    messages[1]["content"] += "\n上次输出不符合 JSON 协议；现在只输出一个合法动作决策 JSON。"
                    text = self._call("planner_repair", messages, self.config.action_planner_max_tokens, self.config.action_planner_timeout_seconds, self.config.action_planner_thinking_mode, state)
                    decision = parse_decision(text, target)
                except Exception as repair_exc:
                    if self._recoverable(repair_exc):
                        self._record("planner_network_failed", error_type=type(repair_exc).__name__)
                        return self._safe_decision(target)
                    self._record("planner_protocol_repair_failed", error_type=type(repair_exc).__name__)
                    return self._safe_decision(target)
            else:
                return self._safe_decision(target)
        available_names = {item.name for item in actions}
        if decision.action not in available_names:
            self._record("planner_action_unavailable", action=decision.action, target_id=decision.target_id)
            return self._safe_decision(target)
        if (decision.action, decision.target_id) in rejected:
            return self._safe_decision(target)
        self._record("planner_decision", action=decision.action, target_id=decision.target_id, goal=decision.goal[:240])
        return decision

    def _retrieve_strategy_examples(self, state: ActionRuntimeState) -> None:
        """Run the script-equivalent retrieval once, under Runtime accounting."""
        if not self.config.action_strategy_retrieval_enabled:
            self._record("strategy_retrieval_skipped", reason="disabled")
            return
        top_k = self.config.action_strategy_retrieval_top_k
        if not isinstance(top_k, int) or top_k < 1:
            self._record("strategy_retrieval_skipped", reason="invalid_top_k")
            return
        try:
            raw = self._call(
                "strategy_retrieval",
                build_structure_messages(state.problem_packet.raw_text),
                self.config.action_strategy_retrieval_max_tokens,
                self.config.action_strategy_retrieval_timeout_seconds,
                self.config.action_strategy_retrieval_thinking_mode,
                state,
            )
            retrieval_text = normalize_retrieval_text(raw)
            retriever = get_shared_strategy_retriever()
            retrieved = retriever.retrieve_for_structure(
                state.problem_packet.raw_text, retrieval_text, top_k=top_k,
            )
            state.strategy_retrieval_text = retrieved["retrieval_text"]
            state.strategy_results = list(retrieved["results"])
            cards = build_strategy_cards(
                state.strategy_results,
                max_chars=max(0, self.config.action_strategy_card_max_chars),
            )
            state.planner_strategy_cards = cards.planner
            state.executor_strategy_cards = cards.executor
            state.planner_strategy_cards_truncated = cards.planner_truncated
            state.executor_strategy_cards_truncated = cards.executor_truncated
            trace_planner_cards, trace_planner_truncated = bound_card_text(
                state.planner_strategy_cards, self.config.action_trace_max_chars,
            )
            trace_executor_cards, trace_executor_truncated = bound_card_text(
                state.executor_strategy_cards, self.config.action_trace_max_chars,
            )
            self._record(
                "strategy_retrieval_completed",
                retrieval_text=state.strategy_retrieval_text,
                results=trace_results(state.strategy_results),
                planner_cards=trace_planner_cards,
                executor_cards=trace_executor_cards,
                planner_cards_truncated=cards.planner_truncated or trace_planner_truncated,
                executor_cards_truncated=cards.executor_truncated or trace_executor_truncated,
            )
        except Exception as exc:
            self._record("strategy_retrieval_degraded", error_type=type(exc).__name__)

    def _run_decision(self, state: ActionRuntimeState, decision: ActionDecision, *, depth: int = 0, parent_id: str | None = None) -> None:
        if decision.action == "finish" or not self._may_start_node(state):
            return
        node_id = f"n{len(state.nodes) + 1}"
        node = ActionNode(node_id, decision, depth=depth, parent_id=parent_id)
        state.nodes[node_id] = node
        state.budget.node_attempts += 1
        self._record("node_started", node_id=node_id, action=decision.action, target_id=decision.target_id)
        output = self._execute(state, node)
        node.output = output
        if decision.action in {"negate", "induct", "classify"}:
            self._spawn_branches(state, node)
            return
        reflection = self._reflect(state, node)
        if reflection is None:
            state.rejected_routes.append(RouteFingerprint(decision.action, decision.target_id, "reflector_protocol_failure"))
            return
        verdict = reflection["verdict"]
        self._record(
            "node_reflected",
            node_id=node_id,
            action=decision.action,
            verdict=verdict,
            claims=_trace_claims(reflection.get("accepted_claims", [])),
            first_fatal_error=str(reflection.get("first_fatal_error", ""))[:800],
        )
        if (
            verdict == "repair"
            and node.attempts < self.config.action_max_repairs_per_node
            and state.budget.repairs < self.config.action_max_repairs_total
        ):
            state.budget.repairs += 1
            node.attempts += 1
            self._record("node_repair_started", node_id=node_id)
            node.output = self._execute(state, node, repair=str(reflection.get("repair_instruction", "")), compressed=True)
            reflection = self._reflect(state, node) or {"verdict": "reject_route", "first_fatal_error": "repair_reflection_failed"}
        if reflection["verdict"] == "accept":
            self._commit(state, node, reflection)
        else:
            reason = str(reflection.get("first_fatal_error", "route_rejected"))
            state.rejected_routes.append(RouteFingerprint(decision.action, decision.target_id, reason))
            state.invalidate_claims([str(item) for item in reflection.get("invalidated_claim_ids", [])], reason)
            self._record("route_rejected", node_id=node_id, reason=reason[:300])

    def _spawn_branches(self, state: ActionRuntimeState, node: ActionNode) -> None:
        try:
            branches = parse_branches(node.output)
        except Exception as exc:
            self._record("json_protocol_repair_started", call_type="branches", attempt=2, error=str(exc)[:500])
            if node.attempts >= self.config.action_max_repairs_per_node or state.budget.repairs >= self.config.action_max_repairs_total:
                state.rejected_routes.append(RouteFingerprint(node.decision.action, node.decision.target_id, "invalid_branch_protocol"))
                self._record("route_rejected", node_id=node.id, reason=f"invalid_branch_protocol:{type(exc).__name__}")
                return
            node.attempts += 1
            state.budget.repairs += 1
            try:
                node.output = self._execute(state, node, repair="上一次分支输出未通过 JSON 校验，请只输出合法 branches 数组。", compressed=True)
                branches = parse_branches(node.output)
            except Exception as repair_exc:
                state.rejected_routes.append(RouteFingerprint(node.decision.action, node.decision.target_id, "invalid_branch_protocol"))
                self._record("route_rejected", node_id=node.id, reason=f"invalid_branch_protocol:{type(repair_exc).__name__}")
                return
        if node.depth >= self.config.action_max_branch_depth:
            self._record("branch_limit_reached", node_id=node.id, reason="max_depth")
            return
        slots = max(0, self.config.action_max_open_branches - len(self._pending))
        accepted = branches[: min(self.config.action_max_children_per_branch, slots)]
        if not accepted:
            self._record("branch_limit_reached", node_id=node.id, reason="open_branch_limit")
            return
        for branch in accepted:
            goal = f"在条件“{branch['conditions']}”下，{branch['goal']}"
            child = ActionDecision("derive", node.decision.target_id, goal, node.decision.required_fact_ids, "完成该分支并给出可审核结论")
            self._pending.append((child, node.depth + 1, node.id))
        node.status = "branched"
        self._record(
            "branch_created",
            node_id=node.id,
            action=node.decision.action,
            count=len(accepted),
            branches=[{"conditions": item["conditions"][:600], "goal": item["goal"][:600]} for item in accepted],
            truncated=len(branches) > len(accepted),
        )

    def _execute(self, state: ActionRuntimeState, node: ActionNode, repair: str = "", compressed: bool = False) -> str:
        problem, warnings = source_packet(state, self.config, node.decision.target_id)
        accepted, failures, memory_warnings = build_memory(state, self.config)
        for warning in warnings + memory_warnings:
            self._record(warning, stage="executor")
        skills, material = retrieve_skill_material(state.skill_domains, state.skill_sections, fallback_category=state.domain, problem=problem, max_chars=self.config.action_skill_material_max_chars)
        self._record("skill_material_selected", node_id=node.id, skills=[item.category for item in skills], chars=len(material))
        timeout = self.config.action_compressed_timeout_seconds if compressed else self.config.action_executor_timeout_seconds
        tokens = self.config.action_compressed_max_tokens if compressed else self.config.action_executor_max_tokens
        thinking = self.config.action_compressed_thinking_mode if compressed else self.config.action_executor_thinking_mode
        try:
            output = self._call(
                "executor_repair" if compressed else "executor",
                executor_messages(state.domain, node.decision.action, node.decision.goal, problem, accepted, failures, material, repair, state.model_preprocess, state.profile_context, state.strategy_context, state.executor_strategy_cards),
                tokens,
                timeout,
                thinking,
                state,
                temperature=self._executor_temperature(node.decision.action, compressed),
            )
            self._program_check(state, node.id, output)
            return output
        except Exception as exc:
            if not compressed and state.budget.network_recoveries < self.config.action_max_network_recovery_calls and self._recoverable(exc) and self._may_start_node(state):
                state.budget.network_recoveries += 1
                self._record("compressed_recovery_started", node_id=node.id, reason=type(exc).__name__)
                return self._execute(state, node, repair="上次请求传输或长度失败；简洁完成当前目标。", compressed=True)
            raise

    def _reflect(self, state: ActionRuntimeState, node: ActionNode) -> dict[str, Any] | None:
        accepted, _, _ = build_memory(state, self.config)
        problem, _ = source_packet(state, self.config, node.decision.target_id)
        messages = reflector_messages(node.decision.goal, problem, node.output, accepted)
        error = ""
        for attempt in range(2):
            current = [dict(item) for item in messages]
            if error:
                current[1]["content"] += f"\n\n<UNTRUSTED_PROTOCOL_ERROR>上一次审核输出无效：{error}。只输出合法 JSON。</UNTRUSTED_PROTOCOL_ERROR>"
                self._record("json_protocol_repair_started", call_type="reflector", attempt=attempt + 1, error=error[:500])
            try:
                text = self._call("reflector", current, self.config.action_reflector_max_tokens, self.config.action_reflector_timeout_seconds, self.config.action_reflector_thinking_mode, state)
                return parse_reflection(text)
            except Exception as exc:
                if self._recoverable(exc):
                    self._record("reflector_network_failed", node_id=node.id, error_type=type(exc).__name__)
                    return None
                error = str(exc)[:800] or type(exc).__name__
                self._record("json_protocol_failed", call_type="reflector", attempt=attempt + 1, error=error)
        self._record("reflector_failed", node_id=node.id, error_type="protocol_or_call_failure")
        return None

    def _program_check(self, state: ActionRuntimeState, node_id: str, output: str) -> None:
        """白名单检查只提供审核证据，绝不自动接受数学结论。"""
        if state.budget.program_checks >= self.config.action_max_program_checks:
            return
        try:
            from reasoning_agent.custom2.program_checks import check_expression, numeric_equalities, requested_checks
            expressions = (requested_checks(output) + numeric_equalities(output))[: self.config.action_max_program_checks - state.budget.program_checks]
            results = []
            for expression in expressions:
                result = check_expression(expression, source="action_node")
                state.budget.program_checks += 1
                results.append({"expression": result.expression, "status": result.status, "result": result.result})
            if results:
                self._record("program_checks_completed", node_id=node_id, checks=results)
        except Exception as exc:
            self._record("program_checks_failed", node_id=node_id, error_type=type(exc).__name__)

    def _commit(self, state: ActionRuntimeState, node: ActionNode, reflection: dict[str, Any]) -> None:
        claims = [str(item).strip() for item in reflection.get("accepted_claims", []) if str(item).strip()] or [node.output.strip()]
        claim_ids = []
        coverage = tuple(str(item) for item in reflection.get("covered_subquestion_ids", []) if str(item) in state.subquestion_status)
        for index, text in enumerate(claims, 1):
            claim_id = f"c{len(state.accepted_claims) + 1}"
            state.accepted_claims[claim_id] = AcceptedClaim(claim_id, text, node.id, tuple(node.decision.required_fact_ids), coverage, "reflector_accept")
            claim_ids.append(claim_id)
        answer, action_coverage = parse_action_result(node.output)
        covered = tuple(item for item in (action_coverage or list(coverage)) if item in state.subquestion_status)
        if decision_action_allows_answer(node.decision.action) and answer and covered:
            candidate_id = f"a{len(state.answer_candidates) + 1}"
            state.answer_candidates[candidate_id] = AnswerCandidate(candidate_id, answer, state.answer_mode, covered, tuple(claim_ids), node.id)
        summary = summarize_node(state)
        self._record(
            "claims_committed",
            node_id=node.id,
            action=node.decision.action,
            claim_ids=claim_ids,
            claims=_trace_claims(claims),
            candidate_count=len(state.supported_candidates()),
            covered=summary["covered"],
        )

    def _finalize(self, state: ActionRuntimeState) -> str:
        candidates = [{"id": item.id, "answer": item.text, "covers": item.covered_subquestion_ids} for item in state.supported_candidates()]
        accepted, _, _ = build_memory(state, self.config)
        if not candidates:
            return self._emergency_guess(state, accepted)
        self._record("finalization_started", candidates=len(candidates))
        try:
            problem, _ = source_packet(state, self.config, next(iter(state.subquestion_status), "q1"))
            text = self._call("finalizer", finalizer_messages(problem, candidates, accepted), self.config.action_finalizer_max_tokens, self.config.action_finalizer_timeout_seconds, self.config.action_finalizer_thinking_mode, state, finalizer=True)
            final = text.strip()
        except Exception as exc:
            self._record("finalizer_failed", error_type=type(exc).__name__)
            final = self._fallback(state)
        candidates = state.supported_candidates()
        if state.answer_mode in {"computation", "numeric", "multiple_choice", "fill_in_blank"} and len(candidates) == 1:
            return self._boxed(candidates[0].text)
        return self._boxed(final)

    def _emergency_guess(self, state: ActionRuntimeState, accepted: str) -> str:
        problem, _ = source_packet(state, self.config, next(iter(state.subquestion_status), "q1"))
        candidates = [{"id": item.id, "answer": item.text, "covers": item.covered_subquestion_ids} for item in state.supported_candidates()]
        node_material = "\n".join(
            f"[{node.id}/{node.decision.action}] {node.output[:1800]}"
            for node in state.nodes.values() if node.output.strip()
        )
        try:
            text = self._call(
                "finalizer_emergency",
                emergency_guess_messages(problem, candidates, accepted, state.strategy_context, node_material),
                self.config.action_finalizer_max_tokens,
                self.config.action_finalizer_timeout_seconds,
                self.config.action_finalizer_thinking_mode,
                state,
                finalizer=True,
            ).strip()
            if text and text != "无法确定唯一答案":
                self._record("best_effort_finalized", source="emergency_model", content_chars=len(text))
                return self._boxed(text)
        except Exception as exc:
            self._record("best_effort_finalizer_failed", error_type=type(exc).__name__)
        fallback = self._fallback(state)
        self._record("best_effort_fallback", source="accepted_or_node_material", content_chars=len(fallback))
        return fallback

    def _fallback(self, state: ActionRuntimeState) -> str:
        candidates = state.supported_candidates()
        if candidates:
            return "\n".join(item.text for item in candidates)
        claims = [item.text for item in state.accepted_claims.values() if item.valid]
        if claims:
            return "\n".join(claims)
        # 最后的通用兜底只复用节点模型已经给出的答案控制尾部或正文，
        # 不硬编码某道题的答案；solve_status 仍会标记为 failed/timeout。
        action_answers = []
        for node in reversed(list(state.nodes.values())):
            answer, _ = parse_action_result(node.output)
            if answer:
                action_answers.append(answer)
        if action_answers:
            return self._boxed(action_answers[0])
        node_outputs = [node.output.strip() for node in reversed(list(state.nodes.values())) if node.output.strip()]
        if node_outputs:
            return node_outputs[0]
        return "基于当前可用材料生成的最佳努力结论：尚未形成可验证的数学对象。"

    def _boxed(self, text: str) -> str:
        text = str(text or "").strip()
        if not text or "\\boxed" in text:
            return text or "基于当前可用材料生成的最佳努力结论：尚未形成可验证的数学对象。"
        return ensure_boxed_final_response(text)

    def _call(
        self,
        call_type: str,
        messages: list[dict[str, str]],
        tokens: int,
        timeout: float,
        thinking: bool,
        state: ActionRuntimeState,
        finalizer: bool = False,
        temperature: float | None = None,
    ) -> str:
        if state.budget.model_calls >= self.config.action_max_model_calls:
            raise TimeoutError("model_call_limit")
        remaining = state.budget.remaining()
        reserve = self.config.action_return_reserve_seconds if finalizer else self.config.action_finalizer_reserve_seconds
        stage = _stage_for(call_type)
        stage_limit = getattr(self.config, f"action_{stage}_pool_seconds", self.config.action_safety_pool_seconds)
        stage_remaining = max(0.0, stage_limit - self._stage_elapsed.get(stage, 0.0))
        allowed = min(timeout, stage_remaining, remaining - reserve)
        if allowed <= 0:
            raise TimeoutError("wall_clock_budget")
        state.budget.model_calls += 1
        setattr(state.budget, f"{call_type.split('_')[0]}_calls", getattr(state.budget, f"{call_type.split('_')[0]}_calls", 0) + 1)
        started = time.monotonic()
        try:
            content = invoke_client(
                self.client,
                messages,
                max_tokens=tokens,
                timeout=allowed,
                thinking=thinking,
                temperature=self._temperature_for(call_type) if temperature is None else temperature,
            )
        except Exception as exc:
            failure = {
                "call_type": call_type,
                "error_type": type(exc).__name__,
                "duration_seconds": time.monotonic() - started,
            }
            status_code = getattr(exc, "status_code", None)
            if isinstance(status_code, int):
                failure["status_code"] = status_code
            response_body = getattr(exc, "response_body", "")
            if isinstance(response_body, str) and response_body:
                failure["server_error"] = response_body[:1000]
            self.debug_trace.append({"type": "model_call_error", **failure})
            self._record("model_call_failed", **failure)
            raise
        finally:
            self._stage_elapsed[stage] = self._stage_elapsed.get(stage, 0.0) + max(0.0, time.monotonic() - started)
        self.debug_trace.append({"type": "model_response", "call_type": call_type, "duration_seconds": time.monotonic() - started, "content_length": len(content), "content_head": content[:300], "content_tail": content[-300:]})
        if not content.strip():
            raise RuntimeError("empty_model_response")
        return content

    def _temperature_for(self, call_type: str) -> float:
        """Choose sampling per runtime role without relying on client defaults."""
        if call_type == "finalizer_emergency":
            return self.config.action_emergency_temperature
        return self.config.action_control_temperature

    def _executor_temperature(self, action: str, compressed: bool) -> float:
        if compressed:
            return self.config.action_repair_temperature
        if action == "rethink":
            return self.config.action_rethink_temperature
        if action in {"negate", "induct", "classify"}:
            return self.config.action_branch_temperature
        return self.config.action_executor_temperature

    def _may_start_node(self, state: ActionRuntimeState) -> bool:
        return self._node_start_block_reason(state) == ""

    def _node_start_block_reason(self, state: ActionRuntimeState) -> str:
        if state.budget.node_attempts >= self.config.action_max_node_attempts:
            return "node_attempt_limit"
        if len(state.nodes) >= self.config.action_max_primary_nodes:
            return "primary_node_limit"
        # Reserve enough time to return an answer, but let each call use the
        # remaining dynamic budget instead of predicting a fixed node duration.
        if state.budget.model_calls > self.config.action_max_model_calls - 3:
            return "model_call_reserve"
        if state.budget.remaining() <= (
            self.config.action_finalizer_reserve_seconds
            + self.config.action_return_reserve_seconds
        ):
            return "convergence_window"
        return ""

    def _covered(self, state: ActionRuntimeState) -> bool:
        return bool(state.subquestion_status) and all(value == "covered" for value in state.subquestion_status.values())

    def _safe_decision(self, target: str) -> ActionDecision:
        # 安全降级也必须选择有资格产出候选答案的动作；否则分析结论
        # 只能进入 AcceptedClaim，无法推动题目完成。
        return ActionDecision("derive", target, "沿最直接路线完成当前问项并给出可审核结论", (), "得到一个明确可验证的局部结论")

    def _planner_repair_allowed(self, state: ActionRuntimeState) -> bool:
        repairs = sum(1 for item in self.trace if item["type"] == "planner_protocol_repair_started")
        if repairs >= self.config.action_max_planner_protocol_repairs:
            return False
        self._record("planner_protocol_repair_started")
        return True

    @staticmethod
    def _recoverable(exc: Exception) -> bool:
        return isinstance(exc, (TimeoutError, ConnectionError)) or "timeout" in str(exc).lower() or "length" in str(exc).lower()

    def _status(self, state: ActionRuntimeState, final: str, stop_reason: str) -> str:
        if self._covered(state) and final.strip():
            return "success"
        if "timeout" in stop_reason or "window" in stop_reason or state.budget.remaining() <= 0:
            return "timeout"
        return "failed"

    def _json_call(
        self,
        call_type: str,
        messages: list[dict[str, str]],
        tokens: int,
        timeout: float,
        state: ActionRuntimeState,
        thinking: bool,
    ) -> dict[str, Any]:
        """Call a JSON role and allow exactly one protocol repair attempt."""
        error = ""
        for attempt in range(2):
            current = messages
            if error:
                current = [dict(item) for item in messages]
                current[1]["content"] += (
                    "\n\n<UNTRUSTED_PROTOCOL_ERROR>\n"
                    f"上一次输出未通过 JSON 协议校验：{error}\n"
                    "现在只输出一个符合字段和类型要求的合法 JSON，不要输出解释、Markdown 或代码块。"
                    "</UNTRUSTED_PROTOCOL_ERROR>"
                )
                self._record("json_protocol_repair_started", call_type=call_type, attempt=attempt + 1, error=error[:500])
            try:
                text = self._call(call_type, current, tokens, timeout, thinking, state)
                data = parse_json(text)
                self._validate_json_role(call_type, data)
                return data
            except Exception as exc:
                # 只有实际收到但结构不合法的输出才需要协议修复。读取超时、
                # 网络错误与长度错误没有可修复的 JSON，直接交给调用方降级。
                if self._recoverable(exc):
                    self._record(
                        "json_network_failed",
                        call_type=call_type,
                        attempt=attempt + 1,
                        error_type=type(exc).__name__,
                    )
                    raise
                error = str(exc)[:800] or type(exc).__name__
                self._record("json_protocol_failed", call_type=call_type, attempt=attempt + 1, error=error)
        raise ValueError(f"{call_type}_json_protocol_failed:{error}")

    @staticmethod
    def _validate_json_role(call_type: str, data: dict[str, Any]) -> None:
        required: dict[str, tuple[str, ...]] = {
            "model_preprocess": ("problem_restatement", "subquestions"),
            "profile": ("domain", "answer_mode", "risk_level"),
            "strategy": (
                "main_method", "backup_method", "proof_obligations", "checks",
                "skill_domains", "skill_sections", "initial_decision",
            ),
        }
        for field in required.get(call_type, ()):
            if field not in data:
                raise ValueError(f"missing_{field}")
        if call_type == "model_preprocess" and not isinstance(data.get("subquestions"), list):
            raise ValueError("subquestions_not_list")
        if call_type == "profile" and data.get("risk_level") not in {"low", "medium", "high"}:
            raise ValueError("invalid_risk_level")
        if call_type == "strategy":
            for field in ("main_method", "backup_method"):
                if not isinstance(data.get(field), str) or not data[field].strip():
                    raise ValueError(f"invalid_{field}")
            for field in ("proof_obligations", "checks", "skill_domains", "skill_sections"):
                value = data.get(field)
                if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                    raise ValueError(f"invalid_{field}")
            if len(data["skill_domains"]) > 2 or len(data["skill_sections"]) > 8:
                raise ValueError("strategy_skill_limit_exceeded")
            decision = data.get("initial_decision")
            if not isinstance(decision, dict):
                raise ValueError("initial_decision_not_object")
            if not isinstance(decision.get("target_id"), str) or not decision["target_id"].strip():
                raise ValueError("initial_decision_invalid_target_id")
            if not isinstance(decision.get("required_fact_ids"), list) or not all(
                isinstance(item, str) for item in decision["required_fact_ids"]
            ):
                raise ValueError("initial_decision_invalid_required_fact_ids")
            if "branch_hint" in decision and not isinstance(decision["branch_hint"], str):
                raise ValueError("initial_decision_invalid_branch_hint")
            try:
                parse_decision(json.dumps(decision, ensure_ascii=False), "q1")
            except ValueError as exc:
                raise ValueError(f"invalid_initial_decision:{exc}") from exc

    def _record(self, event_type: str, **data: Any) -> None:
        safe = {key: _bound(value, self.config.action_trace_max_chars) for key, value in data.items()}
        self.trace.append({"type": event_type, "time": time.time(), "data": safe})


def _json(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


def _bound(value: Any, max_chars: int) -> Any:
    if isinstance(value, str):
        return value[:max_chars]
    if isinstance(value, list):
        return [_bound(item, max_chars) for item in value]
    if isinstance(value, dict):
        return {str(key): _bound(item, max_chars) for key, item in value.items()}
    return value


def _trace_claims(values: Any) -> list[str]:
    """保留动作核心结论，不把完整模型回答写入 trace。"""
    if not isinstance(values, list):
        return []
    return [str(value).strip()[:1200] for value in values if str(value).strip()][:6]


def _stage_for(call_type: str) -> str:
    if call_type == "model_preprocess":
        return "preprocess"
    if call_type == "bootstrap" or call_type.startswith("planner"):
        return "planner"
    if call_type == "profile":
        return "profile"
    if call_type == "strategy":
        return "strategy"
    if call_type == "strategy_retrieval":
        return "strategy_retrieval"
    if call_type.startswith("executor"):
        return "executor"
    if call_type == "reflector":
        return "reflector"
    if call_type.startswith("finalizer"):
        return "finalizer"
    return "safety"


def decision_action_allows_answer(action: str) -> bool:
    """Return whether an action has enough semantic responsibility for a candidate."""
    return action in ANSWER_PRODUCING_ACTIONS
