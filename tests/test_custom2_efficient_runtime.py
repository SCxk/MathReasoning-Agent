import json
import time
import unittest

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom2.context import build_solver_messages
from reasoning_agent.custom2.models import (
    AgentState,
    CandidateAnswer,
    CompletionRequirement,
    ProblemFact,
    StrategyGuidance,
    SolutionDraftState,
    Task,
)
from reasoning_agent.custom2.model_call import ModelCallTimedOut, call_model
from reasoning_agent.custom2.agent import _bounded_debug_trace
from reasoning_agent.custom2.runner import (
    ReasoningRuntime,
    _normalize_macro_tasks,
    _objectives_repeat_route,
)
from reasoning_agent.custom2.schemas import (
    ReasoningStep,
    ResultProposal,
    StepVerification,
    CritiqueOutput,
)
from reasoning_agent.custom2.storage import RuntimeLogger
from reasoning_agent.custom2.state_manager import (
    accepted_claim_closure,
    candidate_conflict_groups,
    reasoning_step_to_solution_draft,
    time_phase,
    validate_reasoning_step_protocol,
    validate_state_invariants,
)


def independent_verification_fields(
    method: str = "直接代回原式核验",
    attempt: str = "检查定义域边界与其他可能值",
    method_type: str = "direct_substitution",
) -> dict:
    return {
        "independent_method": method,
        "falsification_attempt": attempt,
        "method_type": method_type,
        "checked_claims": ["候选满足原题全部条件"],
        "tested_cases": [attempt],
        "route_difference": "不沿用原推导，直接从原题条件核验候选",
    }


class EfficientRuntimeFakeClient:
    def __init__(self, repair: bool = False) -> None:
        self.repair = repair
        self.calls: list[list[dict]] = []
        self.call_kwargs: list[dict] = []
        self.solver_calls = 0
        self.critique_calls = 0

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        self.call_kwargs.append(kwargs)
        system = messages[0]["content"]
        if "判断下面数学题" in system:
            return json.dumps(
                {
                    "primary_category": "数学分析",
                    "secondary_categories": [],
                    "confidence": 0.95,
                    "reason": "基础计算",
                },
                ensure_ascii=False,
            )
        if "事实形式化器" in system:
            return json.dumps(
                {
                    "problem_facts": [
                        {
                            "fact_type": "target",
                            "statement": "计算 1+1",
                            "source_text": "求 1+1",
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if "解题策略设计器" in system:
            return json.dumps(
                {
                    "execution_mode": "direct",
                    "problem_type": "numeric",
                    "core_methods": ["直接计算"],
                    "phase_plan": ["计算并复核"],
                    "risk_controls": [],
                    "do_not": [],
                    "first_step_instruction": "完成计算并复核。",
                    "initial_task_revisions": [],
                    "macro_tasks": [
                        {
                            "kind": "compute",
                            "objective": "完成计算并给出可判分结论",
                            "priority": 100,
                            "depends_on": [],
                        }
                    ],
                },
                ensure_ascii=False,
            )
        if "Runtime 中的 Solver" in system:
            self.solver_calls += 1
            results = [
                {
                    "result_type": "equation",
                    "statement": "1+1=2",
                    "justification": "由整数加法",
                    "depends_on": [],
                }
            ]
            if self.repair:
                results.append(
                    {
                        "result_type": "derived_fact",
                        "statement": "错误的附加结论",
                        "justification": "缺少依据",
                        "depends_on": [],
                    }
                )
            return self._step(results, candidates=[] if self.repair else ["2"])
        if "定向修复器" in system:
            return self._step(
                [
                    {
                        "result_type": "derived_fact",
                        "statement": "计算结果为 2",
                        "justification": "由已验证等式 R1",
                        "depends_on": ["R1"],
                    }
                ],
                candidates=["2"],
            )
        if "批量审查器" in system:
            self.critique_calls += 1
            if self.repair and self.critique_calls == 1:
                return json.dumps(
                    {
                        "verdict": "repair",
                        "accepted_claims": ["DRAFT-R1"],
                        "invalid_claims": ["DRAFT-R2"],
                        "candidate_assessment": "absent",
                        "reason": "第二个结论缺少依据",
                        "repair_instruction": "删除错误结论并从已验证等式提炼答案",
                        "failed_route_summary": "",
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {
                    "verdict": "accept",
                    "accepted_claims": ["DRAFT-R1"],
                    "invalid_claims": [],
                    "candidate_assessment": "supported",
                    "reason": "计算与候选一致",
                    "repair_instruction": "",
                    "failed_route_summary": "",
                },
                ensure_ascii=False,
            )
        if "CandidateAnswer 独立验证器" in system:
            return json.dumps(
                {
                    "verdict": "accept",
                    "reason": "候选代回成立且定义域合法",
                    **independent_verification_fields(),
                },
                ensure_ascii=False,
            )
        if "CandidateAnswer 集合完备性验证器" in system:
            payload = json.loads(messages[-1]["content"])
            verified_ids = [
                item["id"]
                for item in payload["all_candidates"]
                if item["status"] == "verified"
            ]
            rejected_ids = [
                item["id"]
                for item in payload["all_candidates"]
                if item["status"] == "rejected"
            ]
            return json.dumps(
                {
                    "verdict": "accept",
                    "verified_candidate_ids": verified_ids,
                    "rejected_candidate_ids": rejected_ids,
                    "complete_answer": "\\boxed{2}",
                    "missing_cases": [],
                    "reason": "全部候选已逐一验证且集合完整",
                    "repair_instruction": "",
                },
                ensure_ascii=False,
            )
        if "最终答案整理器" in system:
            return json.dumps(
                {"answer": "\\boxed{2}", "reasoning_summary": "1+1=2"},
                ensure_ascii=False,
            )
        raise AssertionError(system[:120])

    @staticmethod
    def _step(results, candidates, request_finalization=True):
        return json.dumps(
            {
                "type": "reasoning_step",
                "current_task": "",
                "used_facts": [],
                "used_definitions": [],
                "used_results": [],
                "step_summary": "完成计算",
                "solution_draft": "由整数加法可得 1+1=2，因此答案为 2。",
                "new_definitions": [],
                "new_results": results,
                "candidate_answers": candidates,
                "closed_tasks": [],
                "new_tasks": [],
                "request_finalization": request_finalization,
            },
            ensure_ascii=False,
        )


class EfficientRuntimeTests(unittest.TestCase):
    def test_custom2_solver_default_max_tokens_is_131072(self) -> None:
        config = AgentConfig()
        self.assertEqual(config.custom2_solver_max_tokens, 131072)
        self.assertEqual(config.strategy_preprocess_max_tokens, 4096)
        self.assertEqual(config.custom2_finalizer_max_tokens, 8192)

    def test_new_state_fields_are_json_safe_and_old_state_is_valid(self) -> None:
        state = AgentState(problem="求值")
        payload = json.loads(state.model_dump_json())
        self.assertEqual(payload["execution_mode"], "draft")
        self.assertEqual(payload["solution_draft"]["version"], 0)
        self.assertEqual(validate_state_invariants(state), [])

    def test_reasoning_step_adapter_and_dependency_closure(self) -> None:
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="批量推导",
            solution_draft="完整草稿",
            new_results=[
                ResultProposal(
                    result_type="derived_fact",
                    statement="结论一",
                    justification="依据",
                ),
                ResultProposal(
                    result_type="derived_fact",
                    statement="结论二",
                    justification="依据",
                ),
            ],
        )
        draft = reasoning_step_to_solution_draft(step)
        draft.claims[1].depends_on = ["DRAFT-R1"]
        accepted = accepted_claim_closure(
            draft, ["DRAFT-R1", "DRAFT-R2"], ["DRAFT-R1"]
        )
        self.assertEqual(accepted, set())

    def test_protocol_validation_fast_fails_unknown_ids(self) -> None:
        state = AgentState(
            problem="求值",
            problem_facts=[
                ProblemFact(
                    id="P1", fact_type="target", statement="求值", source_text="求值"
                )
            ],
            tasks=[Task(id="T1", kind="derive", objective="完成推导", status="active")],
        )
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            used_results=["R99"],
            step_summary="错误引用",
            solution_draft="草稿",
        )
        errors = validate_reasoning_step_protocol(state, step, state.tasks[0])
        self.assertIn("unknown or unverified dependency R99", errors)

    def test_macro_normalization_filters_micro_and_duplicate_tasks(self) -> None:
        tasks = _normalize_macro_tasks(
            [
                {"kind": "formalize", "objective": "定义变量", "priority": 10},
                {"kind": "derive", "objective": "建立核心关系并完成推导", "priority": 9},
                {"kind": "derive", "objective": "建立核心关系并完成推导", "priority": 8},
                {"kind": "verify", "objective": "检查边界和完整性", "priority": 7},
            ],
            "macro",
        )
        self.assertEqual([task["kind"] for task in tasks], ["derive", "verify"])
        direct = _normalize_macro_tasks(tasks, "direct")
        draft = _normalize_macro_tasks(tasks, "draft")
        self.assertEqual(len(direct), 1)
        self.assertEqual(len(draft), 2)

    def test_critique_schema_supports_route_rejection(self) -> None:
        output = CritiqueOutput(
            verdict="reject_route",
            candidate_assessment="uncertain",
            reason="核心等价不成立",
            failed_route_summary="错误使用不可逆变换",
        )
        self.assertEqual(output.verdict, "reject_route")

    def test_efficient_solver_context_omits_history_and_skill_body(self) -> None:
        state = AgentState(
            problem="求值",
            efficient_runtime=True,
            solver_context_max_chars=1200,
            tasks=[Task(id="T1", kind="derive", objective="完成推导", status="active")],
            strategy_guidance=[
                StrategyGuidance(
                    id="S1",
                    selected_skill_ids=["数学分析"],
                    core_methods=["方法摘要"],
                )
            ],
        )
        messages = build_solver_messages(
            state,
            history_messages=[{"role": "assistant", "content": "SECRET_FULL_HISTORY"}],
            current_task=state.tasks[0],
        )
        rendered = "\n".join(message["content"] for message in messages)
        self.assertNotIn("SECRET_FULL_HISTORY", rendered)
        self.assertNotIn("selected_skill_ids", messages[-1]["content"])
        self.assertLessEqual(len(messages[-1]["content"]), 1200)

    def test_time_phases_and_candidate_conflicts(self) -> None:
        now = time.monotonic()
        state = AgentState(
            problem="求值",
            deadline_at=now + 100,
            finalize_reserve_seconds=120,
            convergence_reserve_seconds=360,
            candidates=[
                CandidateAnswer(id="C1", value="2"),
                CandidateAnswer(id="C2", value=" 2。"),
            ],
        )
        self.assertEqual(time_phase(state, now), "final_reserve")
        self.assertEqual(len(candidate_conflict_groups(state)), 1)
        state.deadline_at = now + 300
        self.assertEqual(time_phase(state, now), "converge")
        state.candidates.append(CandidateAnswer(id="C3", value="3"))
        self.assertEqual(len(candidate_conflict_groups(state)), 2)

    def test_direct_end_to_end_verifies_candidate_and_set_before_finalizing(self) -> None:
        client = EfficientRuntimeFakeClient()
        result = ReasoningRuntime(client, AgentConfig()).run("求 1+1。")
        self.assertEqual(result.final_response, "\\boxed{2}")
        self.assertEqual(len(client.calls), 10)
        self.assertEqual(result.state.finalize_mode, "strict")
        self.assertTrue(result.state.accepted_claims)
        self.assertNotIn("step_rejected", [event["type"] for event in result.trace])
        self.assertTrue(client.call_kwargs)
        self.assertTrue(
            all(call.get("thinking_mode") is False for call in client.call_kwargs)
        )
        strategy_limits = [
            kwargs["max_tokens"]
            for messages, kwargs in zip(client.calls, client.call_kwargs)
            if "解题策略设计器" in messages[0]["content"]
        ]
        finalizer_limits = [
            kwargs["max_tokens"]
            for messages, kwargs in zip(client.calls, client.call_kwargs)
            if "最终答案整理器" in messages[0]["content"]
        ]
        self.assertEqual(strategy_limits, [4096])
        self.assertEqual(finalizer_limits, [8192])

    def test_draft_accept_continues_remaining_task_before_candidate_gate(self) -> None:
        class DraftMultiTaskClient(EfficientRuntimeFakeClient):
            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "解题策略设计器" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    return json.dumps(
                        {
                            "execution_mode": "draft",
                            "problem_type": "numeric",
                            "core_methods": ["先推导，再复核"],
                            "phase_plan": ["建立等式", "形成候选"],
                            "risk_controls": [],
                            "do_not": [],
                            "first_step_instruction": "先完成推导任务。",
                            "initial_task_revisions": [],
                            "macro_tasks": [
                                {
                                    "kind": "derive",
                                    "objective": "建立并证明核心计算等式",
                                    "priority": 100,
                                    "depends_on": [],
                                },
                                {
                                    "kind": "verify",
                                    "objective": "独立复核等式并形成最终候选",
                                    "priority": 90,
                                    "depends_on": [],
                                },
                            ],
                        },
                        ensure_ascii=False,
                    )
                if "Runtime 中的 Solver" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    self.solver_calls += 1
                    if "独立尝试推翻当前候选" in json.dumps(messages, ensure_ascii=False):
                        return self._step(
                            [
                                {
                                    "result_type": "derived_fact",
                                    "statement": "用边界值独立复核后结果仍为 2",
                                    "justification": "直接检查最小规模",
                                    "depends_on": [],
                                }
                            ],
                            candidates=["2"],
                            request_finalization=True,
                        )
                    if self.solver_calls == 1:
                        return self._step(
                            [
                                {
                                    "result_type": "equation",
                                    "statement": "1+1=2",
                                    "justification": "由整数加法",
                                    "depends_on": [],
                                }
                            ],
                            candidates=[],
                            request_finalization=False,
                        )
                    return self._step(
                        [
                            {
                                "result_type": "derived_fact",
                                "statement": "复核后最终结果为 2",
                                "justification": "由已验证等式 R1",
                                "depends_on": ["R1"],
                            }
                        ],
                        candidates=["2"],
                        request_finalization=True,
                    )
                return super().chat(messages, **kwargs)

        client = DraftMultiTaskClient()
        result = ReasoningRuntime(client, AgentConfig()).run("求 1+1。")

        self.assertEqual(result.final_response, "\\boxed{2}")
        self.assertEqual(client.solver_calls, 3)
        started = [
            event["task_id"]
            for event in result.trace
            if event["type"] == "macro_task_started"
        ]
        self.assertEqual(len(started), 3)
        continuation = next(
            event
            for event in result.trace
            if event["type"] == "accepted_task_continuation"
        )
        self.assertEqual(continuation["completed_task_id"], started[0])
        self.assertEqual(continuation["next_task_id"], started[1])
        self.assertNotIn("route_rejected", [event["type"] for event in result.trace])

    def test_draft_repair_accept_also_continues_remaining_task(self) -> None:
        class DraftRepairMultiTaskClient(EfficientRuntimeFakeClient):
            def __init__(self) -> None:
                super().__init__(repair=True)

            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "解题策略设计器" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    return json.dumps(
                        {
                            "execution_mode": "draft",
                            "problem_type": "numeric",
                            "core_methods": ["分阶段推导"],
                            "phase_plan": ["修复推导", "形成候选"],
                            "risk_controls": [],
                            "do_not": [],
                            "first_step_instruction": "先完成第一阶段。",
                            "initial_task_revisions": [],
                            "macro_tasks": [
                                {
                                    "kind": "derive",
                                    "objective": "建立可修复的核心推导",
                                    "priority": 100,
                                    "depends_on": [],
                                },
                                {
                                    "kind": "verify",
                                    "objective": "完成剩余复核并注册候选",
                                    "priority": 90,
                                    "depends_on": [],
                                },
                            ],
                        },
                        ensure_ascii=False,
                    )
                if "Runtime 中的 Solver" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    self.solver_calls += 1
                    if "独立尝试推翻当前候选" in json.dumps(messages, ensure_ascii=False):
                        return self._step(
                            [
                                {
                                    "result_type": "derived_fact",
                                    "statement": "边界与反例检查未推翻候选 2",
                                    "justification": "独立检查最小规模",
                                    "depends_on": [],
                                }
                            ],
                            candidates=["2"],
                            request_finalization=True,
                        )
                    if self.solver_calls == 1:
                        return self._step(
                            [
                                {
                                    "result_type": "equation",
                                    "statement": "1+1=2",
                                    "justification": "由整数加法",
                                    "depends_on": [],
                                },
                                {
                                    "result_type": "derived_fact",
                                    "statement": "无依据的结论",
                                    "justification": "缺少依据",
                                    "depends_on": [],
                                },
                            ],
                            candidates=[],
                            request_finalization=False,
                        )
                    return self._step(
                        [
                            {
                                "result_type": "derived_fact",
                                "statement": "最终复核结果为 2",
                                "justification": "由已验证结果",
                                "depends_on": [],
                            }
                        ],
                        candidates=["2"],
                        request_finalization=True,
                    )
                if "定向修复器" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    return self._step(
                        [
                            {
                                "result_type": "derived_fact",
                                "statement": "修复后确认结果为 2",
                                "justification": "由已接受等式 R1",
                                "depends_on": ["R1"],
                            }
                        ],
                        candidates=[],
                        request_finalization=False,
                    )
                return super().chat(messages, **kwargs)

        client = DraftRepairMultiTaskClient()
        result = ReasoningRuntime(client, AgentConfig()).run("求 1+1。")

        self.assertEqual(result.final_response, "\\boxed{2}")
        self.assertGreaterEqual(client.solver_calls, 2)
        continuation = next(
            event
            for event in result.trace
            if event["type"] == "accepted_task_continuation"
            and event.get("after_repair") is True
        )
        self.assertTrue(continuation["next_task_id"])

    def test_draft_without_candidate_runs_generated_candidate_task(self) -> None:
        class CandidateExtractionClient(EfficientRuntimeFakeClient):
            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "解题策略设计器" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    return json.dumps(
                        {
                            "execution_mode": "draft",
                            "problem_type": "numeric",
                            "core_methods": ["先推导后提取答案"],
                            "phase_plan": ["完成推导"],
                            "risk_controls": [],
                            "do_not": [],
                            "first_step_instruction": "先完成推导。",
                            "initial_task_revisions": [],
                            "macro_tasks": [
                                {
                                    "kind": "derive",
                                    "objective": "完成全部数学推导但暂不猜测答案",
                                    "priority": 100,
                                    "depends_on": [],
                                }
                            ],
                        },
                        ensure_ascii=False,
                    )
                if "Runtime 中的 Solver" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    self.solver_calls += 1
                    if self.solver_calls == 1:
                        return self._step(
                            [
                                {
                                    "result_type": "equation",
                                    "statement": "1+1=2",
                                    "justification": "由整数加法",
                                    "depends_on": [],
                                }
                            ],
                            candidates=[],
                            request_finalization=False,
                        )
                    if self.solver_calls == 2:
                        return self._step(
                            [
                                {
                                    "result_type": "derived_fact",
                                    "statement": "复核确认 1+1=2",
                                    "justification": "复核整数加法",
                                    "depends_on": [],
                                }
                            ],
                            candidates=[],
                            request_finalization=False,
                        )
                    return self._step(
                        [], candidates=["2"], request_finalization=True
                    )
                return super().chat(messages, **kwargs)

        client = CandidateExtractionClient()
        result = ReasoningRuntime(client, AgentConfig()).run("求 1+1。")

        self.assertEqual(result.final_response, "\\boxed{2}")
        self.assertGreaterEqual(client.solver_calls, 4)
        started = [
            event
            for event in result.trace
            if event["type"] == "macro_task_started"
        ]
        self.assertGreaterEqual(len(started), 3)
        self.assertTrue(any("候选答案" in event["objective"] for event in started))
        self.assertNotIn("replan_triggered", [event["type"] for event in result.trace])

    def test_partial_accept_repair_finishes_with_candidate_closure(self) -> None:
        client = EfficientRuntimeFakeClient(repair=True)
        result = ReasoningRuntime(client, AgentConfig()).run("求 1+1。")
        self.assertEqual(result.final_response, "\\boxed{2}")
        self.assertEqual(len(client.calls), 12)
        self.assertEqual(result.state.repair_count, 1)
        self.assertEqual(len(result.state.accepted_claims), 3)
        self.assertIn("repair_started", [event["type"] for event in result.trace])

    def test_replan_replaces_old_tasks_and_activates_new_route(self) -> None:
        class ReplanClient:
            def chat(self, messages, **kwargs):
                return json.dumps(
                    {
                        "diagnosis": "原方法核心等价不成立",
                        "avoid_routes": ["原等价变形"],
                        "reuse_results": [],
                        "new_tasks": [
                            {
                                "kind": "construction",
                                "objective": "改用显式构造完成存在性证明",
                                "priority": 120,
                                "depends_on": [],
                            }
                        ],
                        "first_step_instruction": "先建立构造对象",
                    },
                    ensure_ascii=False,
                )

        state = AgentState(
            problem="证明存在性",
            efficient_runtime=True,
            tasks=[
                Task(
                    id="T1", kind="proof", objective="使用原等价变形证明", status="blocked"
                ),
                Task(id="T2", kind="verify", objective="复核原路线", status="open"),
            ],
        )
        runtime = ReasoningRuntime(ReplanClient(), AgentConfig())
        record = runtime._replan_blocked_task(
            state,
            state.tasks[0],
            StepVerification(
                verdict="reject",
                reason="核心等价不成立",
                retry_instruction="更换方法",
                error_category="unsupported_claim",
            ),
            [],
        )
        self.assertEqual(state.model_replan_count, 1)
        self.assertEqual([task.status for task in state.tasks[:2]], ["invalid", "invalid"])
        self.assertEqual(record.new_tasks, ["T3"])
        self.assertEqual(state.tasks[-1].status, "active")

    def test_best_effort_finalize_uses_solution_draft_without_candidate(self) -> None:
        class FinalClient:
            def __init__(self):
                self.finalizer_calls = 0

            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "CandidateAnswer 独立验证器" in system:
                    return json.dumps(
                        {
                            "verdict": "accept",
                            "reason": "临时候选反代成立",
                            **independent_verification_fields(
                                attempt="检查相邻整数与边界值"
                            ),
                        },
                        ensure_ascii=False,
                    )
                self.finalizer_calls += 1
                return json.dumps(
                    {
                        "answer": "\\boxed{2}",
                        "reasoning_summary": (
                            "独立验证后重新生成"
                            if self.finalizer_calls == 2
                            else "从已接受草稿提炼"
                        ),
                    },
                    ensure_ascii=False,
                )

        now = time.monotonic()
        state = AgentState(
            problem="求 1+1",
            efficient_runtime=True,
            started_at=now,
            deadline_at=now + 60,
            solution_draft=SolutionDraftState(
                version=1,
                task_id="T1",
                text="由整数加法得 1+1=2。",
                status="proposed",
            ),
        )
        client = FinalClient()
        result = ReasoningRuntime(client, AgentConfig())._finish_efficient(
            state, [], [], RuntimeLogger(None), "final reserve reached"
        )
        self.assertEqual(result.final_response, "\\boxed{2}")
        self.assertEqual(state.finalize_mode, "best_effort")
        self.assertEqual(result.trace[0]["candidate_ids"], [])
        self.assertEqual(client.finalizer_calls, 2)
        self.assertEqual(state.candidates[0].status, "verified")
        self.assertEqual(
            [event["type"] for event in result.trace[1:4]],
            [
                "best_effort_candidate_generated",
                "best_effort_candidate_verified",
                "best_effort_regeneration_started",
            ],
        )

    def test_best_effort_rejected_candidate_is_regenerated_with_audit(self) -> None:
        class RejectThenRegenerateClient:
            def __init__(self):
                self.finalizer_calls = 0
                self.verifier_calls = 0

            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "CandidateAnswer 独立验证器" in system:
                    payload = json.loads(messages[-1]["content"])
                    self.verifier_calls += 1
                    value = payload["candidate"]["value"]
                    if "2 \\cdot" not in value:
                        return json.dumps(
                            {
                                "verdict": "accept",
                                "reason": "k=1 复核后计数为 4",
                                **independent_verification_fields(
                                    method="对 k=1 直接枚举",
                                    attempt="检查最小规模 k=1",
                                    method_type="small_case_enumeration",
                                ),
                            },
                            ensure_ascii=False,
                        )
                    return json.dumps(
                        {
                            "verdict": "reject",
                            "reason": "k=1 时临时候选给出 8，但直接枚举只有 4 种",
                        },
                        ensure_ascii=False,
                    )
                self.finalizer_calls += 1
                if self.finalizer_calls == 1:
                    answer = "\\boxed{2 \\cdot \\binom{2k}{k}^2}"
                    summary = "未经验证的临时候选"
                else:
                    payload = json.loads(messages[-1]["content"])
                    audit = payload["best_effort_verification"]
                    if audit["verdict"] != "reject" or "k=1" not in audit["reason"]:
                        raise AssertionError(audit)
                    answer = "\\boxed{\\binom{2k}{k}^2}"
                    summary = "根据 k=1 反例去除重复计数因子 2"
                return json.dumps(
                    {"answer": answer, "reasoning_summary": summary},
                    ensure_ascii=False,
                )

        now = time.monotonic()
        state = AgentState(
            problem="计算骨牌放置数",
            efficient_runtime=True,
            started_at=now,
            deadline_at=now + 120,
        )
        client = RejectThenRegenerateClient()
        result = ReasoningRuntime(client, AgentConfig())._finish_efficient(
            state, [], [], RuntimeLogger(None), "state invariant violation"
        )

        self.assertEqual(result.final_response, "\\boxed{\\binom{2k}{k}^2}")
        self.assertEqual(client.finalizer_calls, 2)
        self.assertEqual(client.verifier_calls, 2)
        self.assertEqual(state.candidates[0].status, "rejected")
        self.assertEqual(state.candidates[1].status, "verified")
        verification_event = next(
            event
            for event in result.trace
            if event["type"] == "best_effort_candidate_verified"
        )
        self.assertEqual(verification_event["verdict"], "reject")
        regenerated_event = next(
            event
            for event in result.trace
            if event["type"] == "best_effort_regenerated_candidate_verified"
        )
        self.assertEqual(regenerated_event["verdict"], "accept")

    def test_best_effort_returns_concrete_answer_even_after_two_rejections(self) -> None:
        class AlwaysRejectClient:
            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "CandidateAnswer 独立验证器" in system:
                    return json.dumps(
                        {"verdict": "reject", "reason": "证据仍不充分"},
                        ensure_ascii=False,
                    )
                return json.dumps(
                    {"answer": "\\boxed{5}", "reasoning_summary": "当前最有依据的计算结果"},
                    ensure_ascii=False,
                )

        now = time.monotonic()
        state = AgentState(
            problem="求一个数值",
            efficient_runtime=True,
            started_at=now,
            deadline_at=now + 120,
        )
        result = ReasoningRuntime(AlwaysRejectClient(), AgentConfig())._finish_efficient(
            state, [], [], RuntimeLogger(None), "route rejected"
        )

        self.assertEqual(result.final_response, "\\boxed{5}")
        self.assertTrue(
            any(
                event["type"] == "best_effort_unverified_answer_selected"
                for event in result.trace
            )
        )

    def test_replan_limit_and_repeated_route_filter(self) -> None:
        class NoCallClient:
            def __init__(self):
                self.calls = 0

            def chat(self, messages, **kwargs):
                self.calls += 1
                raise AssertionError("replanner must not be called")

        now = time.monotonic()
        state = AgentState(
            problem="证明",
            efficient_runtime=True,
            deadline_at=now + 1000,
            model_replan_count=2,
            max_model_replans=2,
            tasks=[Task(id="T1", kind="proof", objective="使用反证法证明", status="blocked")],
        )
        client = NoCallClient()
        runtime = ReasoningRuntime(client, AgentConfig())
        changed = runtime._try_efficient_replan(
            state,
            state.tasks[0],
            "路线失败",
            "unsupported_claim",
            [],
            [],
            RuntimeLogger(None),
        )
        self.assertFalse(changed)
        self.assertEqual(client.calls, 0)
        self.assertTrue(
            _objectives_repeat_route("使用反证法证明目标命题", "使用反证法证明目标命题")
        )

    def test_conflicting_candidates_use_independent_verifier_once(self) -> None:
        class CandidateClient:
            def __init__(self):
                self.calls = 0

            def chat(self, messages, **kwargs):
                self.calls += 1
                return json.dumps(
                    {
                        "verdict": "accept",
                        "reason": "代回与完整性检查通过",
                        **independent_verification_fields(
                            method="逐个直接代回",
                            attempt="检查候选外的边界值",
                        ),
                    },
                    ensure_ascii=False,
                )

        state = AgentState(
            problem="求值",
            efficient_runtime=True,
            candidates=[
                CandidateAnswer(id="C1", value="2", support_results=["R1"]),
                CandidateAnswer(id="C2", value="3"),
            ],
        )
        client = CandidateClient()
        runtime = ReasoningRuntime(client, AgentConfig())
        runtime._resolve_candidate_conflict(state, [], RuntimeLogger(None))
        self.assertEqual(client.calls, 2)
        self.assertEqual(state.candidates[0].status, "verified")
        self.assertEqual(state.candidates[1].status, "verified")

    def test_debug_trace_is_bounded(self) -> None:
        bounded = _bounded_debug_trace(
            [{"type": "solver_response", "content": "x" * 10000}], 500
        )
        encoded = json.dumps(bounded, ensure_ascii=False)
        self.assertLessEqual(len(encoded), 510)
        self.assertNotEqual(bounded[0]["content"], "x" * 10000)

    def test_invalid_solver_output_uses_dedicated_json_repair_without_replan(self) -> None:
        class JsonRepairClient(EfficientRuntimeFakeClient):
            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "Runtime 中的 Solver" not in system:
                    return super().chat(messages, **kwargs)
                self.calls.append(messages)
                self.call_kwargs.append(kwargs)
                self.solver_calls += 1
                if self.solver_calls == 1:
                    return "自然语言草稿：1+1=2，但本轮漏掉了 JSON。"
                if self.solver_calls == 2:
                    self.assert_repair_prompt(messages)
                return self._step(
                    [
                        {
                            "result_type": "equation",
                            "statement": "1+1=2",
                            "justification": "由整数加法",
                            "depends_on": [],
                        }
                    ],
                    ["2"],
                )

            @staticmethod
            def assert_repair_prompt(messages):
                assert "上一轮输出不是合法" in messages[-1]["content"]
                assert "漏掉了 JSON" in messages[-1]["content"]

        client = JsonRepairClient()
        result = ReasoningRuntime(client, AgentConfig()).run("求 1+1。")
        event_types = [event["type"] for event in result.trace]
        call_types = [
            item.get("call_type")
            for item in result.debug_trace
            if item.get("type") == "model_response"
        ]
        self.assertEqual(result.final_response, "\\boxed{2}")
        self.assertEqual(result.state.solver_call_count, 2)
        self.assertIn("solver_json_repair", call_types)
        self.assertNotIn("route_rejected", event_types)
        self.assertNotIn("replan_triggered", event_types)
        solver_max_tokens = [
            kwargs["max_tokens"]
            for messages, kwargs in zip(client.calls, client.call_kwargs)
            if "Runtime 中的 Solver" in messages[0]["content"]
        ]
        self.assertEqual(solver_max_tokens, [131072, 131072, 131072])

    def test_solver_prompt_requires_registered_candidate_before_strict_verification(self) -> None:
        state = AgentState(
            problem="证明结论并给出答案",
            tasks=[Task(id="T1", kind="derive", objective="完成证明", status="done")],
        )
        messages = build_solver_messages(state, current_task=state.tasks[0])
        system = messages[0]["content"]
        self.assertIn("Solver 必须先注册至少一个明确的最终答案候选", system)
        self.assertIn("Critic 的 accept 不能豁免", system)

    def test_strict_verification_refuses_missing_candidate_for_every_problem_type(self) -> None:
        now = time.monotonic()
        state = AgentState(
            problem="证明某结论",
            problem_type="proof",
            efficient_runtime=True,
            started_at=now,
            deadline_at=now + 1000,
            requirements=[
                CompletionRequirement(
                    id="REQ_proof_complete", kind="proof_complete", status="satisfied"
                )
            ],
            tasks=[Task(id="T1", kind="derive", objective="完成证明", status="done")],
        )
        runtime = ReasoningRuntime(EfficientRuntimeFakeClient(), AgentConfig())
        ready, reason, instruction = runtime._verify_candidates_and_completeness(
            state, [], [], RuntimeLogger(None)
        )
        self.assertFalse(ready)
        self.assertIn("禁止进入严格验证", reason)
        self.assertIn("candidate_answers", instruction)

    def test_protocol_exhaustion_uses_raw_solver_text_in_emergency_finalizer(self) -> None:
        class RescueClient(EfficientRuntimeFakeClient):
            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "Runtime 中的 Solver" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    self.solver_calls += 1
                    return f"未结构化草稿 {self.solver_calls}：计算结果可能为 7。"
                if "最终答案整理器" in system:
                    payload = json.loads(messages[-1]["content"])
                    assert len(payload["unparsed_solver_responses"]) == 2
                    assert "计算结果可能为 7" in payload["unparsed_solver_responses"][-1]
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    return json.dumps(
                        {"answer": "\\boxed{7}", "reasoning_summary": "抢救原始草稿"},
                        ensure_ascii=False,
                    )
                return super().chat(messages, **kwargs)

        client = RescueClient()
        result = ReasoningRuntime(client, AgentConfig()).run("求一个结果。")
        event_types = [event["type"] for event in result.trace]
        self.assertEqual(result.final_response, "\\boxed{7}")
        self.assertEqual(result.state.solver_call_count, 0)
        self.assertIn("protocol_repair_exhausted", event_types)
        self.assertNotIn("route_rejected", event_types)
        self.assertNotIn("replan_triggered", event_types)

    def test_expired_deadline_returns_best_available_salvaged_answer(self) -> None:
        class NoCallClient:
            def __init__(self):
                self.calls = 0

            def chat(self, **kwargs):
                self.calls += 1
                raise AssertionError("expired runtime must not call finalizer")

        now = time.monotonic()
        state = AgentState(
            problem="求值",
            efficient_runtime=True,
            started_at=now - 2,
            deadline_at=now - 1,
        )
        client = NoCallClient()
        runtime = ReasoningRuntime(client, AgentConfig())
        runtime.solver_raw_responses = ["最后得到 \\boxed{9}"]
        result = runtime._finish_efficient(
            state, [], [], RuntimeLogger(None), "deadline exhausted"
        )
        self.assertEqual(client.calls, 0)
        self.assertEqual(result.final_response, "\\boxed{9}")
        self.assertEqual(result.debug_trace[-1]["type"], "finalizer_skipped")

    def test_model_call_enforces_deadline_and_records_response_metadata(self) -> None:
        class SlowClient:
            def chat(self, **kwargs):
                time.sleep(0.2)
                return "too late"

        now = time.monotonic()
        state = AgentState(
            problem="求值",
            efficient_runtime=True,
            started_at=now,
            deadline_at=now + 0.03,
            finalize_reserve_seconds=0.0,
        )
        debug_trace = []
        started = time.monotonic()
        with self.assertRaises(ModelCallTimedOut):
            call_model(
                SlowClient(), state, debug_trace, "slow_test", messages=[]
            )
        self.assertLess(time.monotonic() - started, 0.15)
        self.assertEqual(debug_trace[-1]["type"], "model_call_error")

        class MetadataClient:
            def chat(self, **kwargs):
                return {
                    "content": "abcdefgh",
                    "_finish_reason": "stop",
                    "_usage": {"completion_tokens": 3},
                }

        plain_state = AgentState(problem="求值")
        metadata_trace = []
        call_model(
            MetadataClient(), plain_state, metadata_trace, "metadata_test", messages=[]
        )
        event = metadata_trace[-1]
        self.assertEqual(event["content_head"], "abcdefgh")
        self.assertEqual(event["content_tail"], "abcdefgh")
        self.assertEqual(event["content_length"], 8)
        self.assertEqual(event["finish_reason"], "stop")
        self.assertEqual(event["token_usage"]["completion_tokens"], 3)

    def test_debug_trace_budget_prefers_recent_model_responses(self) -> None:
        bounded = _bounded_debug_trace(
            [
                {"type": "early", "content": "x" * 10000},
                {
                    "type": "model_response",
                    "call_type": "solver_json_repair",
                    "content_head": "head",
                    "content_tail": "tail",
                    "content_length": 5000,
                    "duration_seconds": 1.5,
                    "token_usage": {"completion_tokens": 20},
                    "finish_reason": "length",
                },
            ],
            1000,
        )
        self.assertTrue(
            any(item.get("call_type") == "solver_json_repair" for item in bounded)
        )

    def test_multiple_correct_candidates_are_all_verified_and_kept(self) -> None:
        class MultiAnswerClient(EfficientRuntimeFakeClient):
            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "Runtime 中的 Solver" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    self.solver_calls += 1
                    return self._step(
                        [
                            {
                                "result_type": "equation",
                                "statement": "x^2=1",
                                "justification": "整理原方程",
                                "depends_on": [],
                            }
                        ],
                        ["-1", "1"],
                    )
                if "CandidateAnswer 集合完备性验证器" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    payload = json.loads(messages[-1]["content"])
                    verified_ids = [
                        item["id"]
                        for item in payload["all_candidates"]
                        if item["status"] == "verified"
                    ]
                    assert verified_ids == ["C1", "C2"]
                    return json.dumps(
                        {
                            "verdict": "accept",
                            "verified_candidate_ids": verified_ids,
                            "rejected_candidate_ids": [],
                            "complete_answer": "\\boxed{\\{-1,1\\}}",
                            "missing_cases": [],
                            "reason": "两个根均已反代且二次方程无其他根",
                            "repair_instruction": "",
                        },
                        ensure_ascii=False,
                    )
                if "最终答案整理器" in system:
                    self.calls.append(messages)
                    self.call_kwargs.append(kwargs)
                    payload = json.loads(messages[-1]["content"])
                    complete = payload["candidate_set_verifications"][-1][
                        "complete_answer"
                    ]
                    return json.dumps(
                        {"answer": complete, "reasoning_summary": "候选集合已验证"},
                        ensure_ascii=False,
                    )
                return super().chat(messages, **kwargs)

        client = MultiAnswerClient()
        result = ReasoningRuntime(client, AgentConfig()).run("求方程 x^2=1 的所有解。")
        self.assertEqual(result.final_response, "\\boxed{\\{-1,1\\}}")
        self.assertEqual(
            [candidate.status for candidate in result.state.candidates],
            ["verified", "verified"],
        )
        self.assertEqual(result.state.candidate_set_verifications[-1].verdict, "accept")
        self.assertEqual(result.state.finalize_mode, "strict")

    def test_candidate_failure_is_remembered_and_can_trigger_replan(self) -> None:
        class RejectingClient:
            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "CandidateAnswer 独立验证器" in system:
                    return json.dumps(
                        {"verdict": "reject", "reason": "候选代回原式不成立"},
                        ensure_ascii=False,
                    )
                if "CandidateAnswer 集合完备性验证器" in system:
                    return json.dumps(
                        {
                            "verdict": "reject",
                            "verified_candidate_ids": [],
                            "rejected_candidate_ids": ["C1"],
                            "complete_answer": "",
                            "missing_cases": ["尚未找到正确解"],
                            "reason": "全部候选均被反代否定",
                            "repair_instruction": "重新推导候选并逐一反代",
                        },
                        ensure_ascii=False,
                    )
                if "换路规划器" in system:
                    payload_text = messages[-1]["content"]
                    assert "candidate_failure" in payload_text
                    return json.dumps(
                        {
                            "diagnosis": "已有候选反代失败",
                            "avoid_routes": ["原候选推导"],
                            "reuse_results": [],
                            "new_tasks": [
                                {
                                    "kind": "derive",
                                    "objective": "重新推导全部候选并逐一代回原条件",
                                    "priority": 120,
                                    "depends_on": [],
                                }
                            ],
                            "first_step_instruction": "从原条件重新推导",
                        },
                        ensure_ascii=False,
                    )
                raise AssertionError(system[:100])

        now = time.monotonic()
        state = AgentState(
            problem="求方程的所有解",
            efficient_runtime=True,
            started_at=now,
            deadline_at=now + 1000,
            requirements=[
                CompletionRequirement(
                    id="REQ_answer", kind="answer_candidate", status="satisfied"
                ),
                CompletionRequirement(
                    id="REQ_candidate_verified", kind="candidate_verified"
                ),
                CompletionRequirement(
                    id="REQ_candidate_set_complete", kind="candidate_set_complete"
                ),
            ],
            candidates=[CandidateAnswer(id="C1", value="3")],
            tasks=[Task(id="T1", kind="derive", objective="推导全部解", status="done")],
        )
        runtime = ReasoningRuntime(RejectingClient(), AgentConfig())
        ready, reason, instruction = runtime._verify_candidates_and_completeness(
            state, [], [], RuntimeLogger(None)
        )
        self.assertFalse(ready)
        self.assertEqual(state.candidates[0].status, "rejected")
        runtime._remember_candidate_failure(state, state.tasks[0], reason, instruction)
        changed = runtime._try_efficient_replan(
            state,
            state.tasks[0],
            reason,
            "candidate_failure",
            [],
            [],
            RuntimeLogger(None),
        )
        self.assertTrue(changed)
        self.assertEqual(state.error_memory[-1].category, "candidate_failure")
        self.assertIn("代回", state.error_memory[-1].reason)
        self.assertEqual(state.tasks[-1].status, "active")

    def test_valid_candidate_but_incomplete_set_does_not_pass_final_gate(self) -> None:
        class IncompleteClient:
            def chat(self, messages, **kwargs):
                system = messages[0]["content"]
                if "CandidateAnswer 独立验证器" in system:
                    return json.dumps(
                        {
                            "verdict": "accept",
                            "reason": "x=1 反代成立",
                            **independent_verification_fields(
                                method="直接代回 x^2=1",
                                attempt="检查 x=-1 这一对称边界候选",
                            ),
                        },
                        ensure_ascii=False,
                    )
                if "CandidateAnswer 集合完备性验证器" in system:
                    return json.dumps(
                        {
                            "verdict": "incomplete",
                            "verified_candidate_ids": ["C1"],
                            "rejected_candidate_ids": [],
                            "complete_answer": "",
                            "missing_cases": ["尚未检查 x=-1"],
                            "reason": "已有正确解，但尚未排除另一个根",
                            "repair_instruction": "求出全部根并逐一反代",
                        },
                        ensure_ascii=False,
                    )
                raise AssertionError(system[:100])

        now = time.monotonic()
        state = AgentState(
            problem="求 x^2=1 的所有解",
            efficient_runtime=True,
            started_at=now,
            deadline_at=now + 1000,
            requirements=[
                CompletionRequirement(id="REQ_answer", kind="answer_candidate"),
                CompletionRequirement(
                    id="REQ_candidate_verified", kind="candidate_verified"
                ),
                CompletionRequirement(
                    id="REQ_candidate_set_complete", kind="candidate_set_complete"
                ),
                CompletionRequirement(id="REQ_completeness", kind="completeness"),
            ],
            candidates=[CandidateAnswer(id="C1", value="1")],
            tasks=[
                Task(
                    id="T1",
                    kind="completeness",
                    objective="检查全部根",
                    status="done",
                )
            ],
        )
        runtime = ReasoningRuntime(IncompleteClient(), AgentConfig())
        ready, reason, instruction = runtime._verify_candidates_and_completeness(
            state, [], [], RuntimeLogger(None)
        )
        self.assertFalse(ready)
        self.assertIn("另一个根", reason)
        self.assertIn("全部根", instruction)
        self.assertEqual(state.candidates[0].status, "verified")
        self.assertEqual(
            state.candidate_set_verifications[-1].verdict, "incomplete"
        )
        self.assertFalse(
            all(requirement.status == "satisfied" for requirement in state.requirements)
        )

    def test_completeness_is_a_valid_runtime_task_kind(self) -> None:
        task = Task(id="T1", kind="completeness", objective="检查是否漏解")
        self.assertEqual(task.kind, "completeness")


if __name__ == "__main__":
    unittest.main()
