import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from reasoning_agent.custom2.models import (
    AgentState,
    CandidateAnswer,
    CandidateVerificationRecord,
    CompletionRequirement,
    Definition,
    DerivedResult,
    ErrorRecord,
    ProblemFact,
    SolutionDraftState,
    StrategyGuidance,
    Task,
)
from reasoning_agent.custom2.prompts import (
    CANDIDATE_VERIFIER_PROMPT,
    EMERGENCY_FINALIZER_PROMPT,
    FINALIZER_PROMPT,
    FORMALIZER_SYSTEM_PROMPT,
    SOLVER_SYSTEM_PROMPT,
    STEP_VERIFIER_SYSTEM_PROMPT,
    STRATEGY_PREPROCESS_SYSTEM_PROMPT,
)
from reasoning_agent.custom2.context import (
    build_candidate_verifier_messages,
    build_solver_messages,
    render_solver_context,
)
from reasoning_agent.custom2.context import build_step_verifier_messages
from reasoning_agent.custom2.runner import ReasoningRuntime
from reasoning_agent.custom2.runner import (
    _build_json_retry_message,
    _build_replanner_skill_reference_message,
    _build_strategy_preprocess_context_message,
    _build_strategy_skill_reference_message,
    _build_fallback_route_reset_task,
    _build_replanner_context_message,
    _replan_output_to_tasks,
    _apply_strategy_task_revisions,
    _maybe_add_candidate_extraction_task,
    _maybe_add_candidate_falsification_task,
    _next_task_after_accepted_draft,
    _normalize_reasoning_step_payload,
    _normalize_task_payload,
    _sanitize_strategy_payload,
)
from reasoning_agent.custom2.schemas import (
    CandidateVerification,
    DomainClassificationOutput,
    ReplanOutput,
    ReasoningStep,
    SolutionDraft,
    StepVerification,
    StrategyOutput,
)
from reasoning_agent.custom2.runner import _sanitize_domain_classification
from reasoning_agent.custom2.strategy_skills import SelectedStrategySkill, select_strategy_skills
from reasoning_agent.custom2.storage import RuntimeLogger
from reasoning_agent.custom2.state_manager import (
    apply_candidate_verification,
    audit_step_progress,
    can_finalize,
    commit_step,
    choose_active_task,
    ensure_tasks_from_tasks,
    infer_completion_requirements,
    maybe_replan_from_requirements,
    record_protocol_failure,
    register_candidate,
    reject_step,
    rollback_invalid_result,
    route,
    snapshot_authoritative_state,
    validate_state_invariants,
)
from reasoning_agent.custom2.verifier import (
    CandidateVerifier,
    DraftCritic,
    FormalizationVerifier,
    StepVerifier,
)


def sample_state() -> AgentState:
    return AgentState(
        problem="一个长方形面积为48平方厘米，长比宽多2厘米。求长和宽。",
        problem_type="numeric",
        problem_facts=[
            ProblemFact(
                id="P1",
                fact_type="given_value",
                statement="长方形面积为48",
                source_text="面积为48平方厘米",
            ),
            ProblemFact(
                id="P2",
                fact_type="relation",
                statement="长=宽+2",
                source_text="长比宽多2厘米",
            ),
        ],
        definitions=[
            Definition(
                id="D1",
                definition_type="variable",
                statement="x表示长方形的宽",
                purpose="表示宽",
            )
        ],
        tasks=[
            Task(id="T1", kind="derive", objective="建立面积方程")
        ],
    )


def independent_verification_fields(
    method: str = "直接代回原条件",
    attempt: str = "检查边界与其他可能值",
) -> dict:
    return {
        "independent_method": method,
        "falsification_attempt": attempt,
        "method_type": "direct_substitution",
        "checked_claims": ["候选满足原题全部条件"],
        "tested_cases": [attempt],
        "route_difference": "不沿用原推导，直接从原题条件核验候选",
    }


class NoChatClient:
    pass


class SequenceChatClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.responses:
            return self.responses.pop(0)
        return "{}"


class FailingChatClient:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[dict] = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        raise self.error


class Custom2StateRuntimeTest(unittest.TestCase):
    def test_rejected_step_does_not_modify_state(self) -> None:
        state = sample_state()
        before = snapshot_authoritative_state(state)
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="错误推出方程",
            new_results=[
                {
                    "result_type": "equation",
                    "statement": "x(x+3)=48",
                    "justification": "误读长宽关系",
                    "depends_on": ["P1", "P2", "D1"],
                }
            ],
            closed_tasks=["T1"],
        )
        reject_step(
            state,
            step,
            StepVerification(
                verdict="reject",
                reason="关系误读",
                retry_instruction="重新使用 P2",
                error_category="unsupported_claim",
            ),
        )
        after = snapshot_authoritative_state(state)
        self.assertEqual(before["problem_facts"], after["problem_facts"])
        self.assertEqual(before["definitions"], after["definitions"])
        self.assertEqual(before["derived_results"], after["derived_results"])
        self.assertEqual(before["candidates"], after["candidates"])
        self.assertNotEqual(before["tasks"], after["tasks"])
        self.assertEqual(len(state.error_memory), 1)

    def test_definition_conflict_is_rejected(self) -> None:
        state = sample_state()
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="重定义 x",
            new_definitions=[
                {
                    "definition_type": "variable",
                    "statement": "x表示长方形的长",
                    "purpose": "冲突定义",
                }
            ],
        )
        verification = StepVerifier().verify(state, step)
        self.assertEqual(verification.verdict, "reject")
        self.assertEqual(verification.error_category, "definition_drift")

    def test_problem_fact_must_match_original_problem(self) -> None:
        verifier = FormalizationVerifier()
        fact = ProblemFact(
            id="P1",
            fact_type="given_value",
            statement="面积为50",
            source_text="面积为50平方厘米",
        )
        self.assertFalse(verifier.verify_problem_fact("面积为48平方厘米。", fact))

    def test_result_cannot_depend_on_unknown_id(self) -> None:
        state = sample_state()
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="引用未知前提",
            new_results=[
                {
                    "result_type": "equation",
                    "statement": "x(x+2)=48",
                    "justification": "由未知前提",
                    "depends_on": ["P9"],
                }
            ],
        )
        verification = StepVerifier().verify(state, step)
        self.assertEqual(verification.verdict, "reject")
        self.assertEqual(verification.error_category, "dependency_error")

    def test_result_cannot_depend_on_invalid_result(self) -> None:
        state = sample_state()
        state.derived_results.append(
            DerivedResult(
                id="R1",
                result_type="equation",
                statement="x(x+2)=48",
                justification="由 P1 P2 D1",
                depends_on=["P1", "P2", "D1"],
                status="invalid",
            )
        )
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="引用 invalid result",
            new_results=[
                {
                    "result_type": "derived_fact",
                    "statement": "x=6或x=-8",
                    "justification": "由 R1",
                    "depends_on": ["R1"],
                }
            ],
        )
        verification = StepVerifier().verify(state, step)
        self.assertEqual(verification.verdict, "reject")

    def test_accepted_result_is_verified(self) -> None:
        state = sample_state()
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="建立方程",
            new_results=[
                {
                    "result_type": "equation",
                    "statement": "x(x+2)=48",
                    "justification": "由 P1 P2 D1",
                    "depends_on": ["P1", "P2", "D1"],
                }
            ],
            closed_tasks=["T1"],
        )
        commit_step(state, step, StepVerification(verdict="accept", reason="ok"))
        self.assertEqual(state.derived_results[0].status, "verified")
        self.assertEqual(state.tasks[0].status, "done")
        self.assertEqual(state.tasks[0].completed_by, ["R1"])

    def test_candidate_starts_as_candidate(self) -> None:
        state = sample_state()
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="提出候选",
            new_results=[
                {
                    "result_type": "derived_fact",
                    "statement": "宽=6，长=8",
                    "justification": "由计算",
                    "depends_on": ["P1", "P2", "D1"],
                }
            ],
            candidate_answers=["宽=6，长=8"],
        )
        commit_step(state, step, StepVerification(verdict="accept", reason="ok"))
        self.assertEqual(state.candidates[0].status, "candidate")
        self.assertEqual(state.tasks[-1].kind, "verify")

    def test_candidate_must_be_verified_before_final(self) -> None:
        state = sample_state()
        state.tasks = []
        state.candidates.append(CandidateAnswer(id="C1", value="宽=6，长=8"))
        self.assertFalse(can_finalize(state))

    def test_closed_task_is_only_committed_after_accept(self) -> None:
        state = sample_state()
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="申请关闭",
            new_results=[
                {
                    "result_type": "equation",
                    "statement": "x(x+2)=48",
                    "justification": "由 P1 P2 D1",
                    "depends_on": ["P1", "P2", "D1"],
                }
            ],
            closed_tasks=["T1"],
        )
        reject_step(
            state,
            step,
            StepVerification(verdict="reject", reason="not enough", error_category="other"),
        )
        self.assertEqual(state.tasks[0].status, "open")
        commit_step(state, step, StepVerification(verdict="accept", reason="ok"))
        self.assertEqual(state.tasks[0].status, "done")

    def test_max_budget_returns_incomplete(self) -> None:
        state = sample_state()
        state.max_solver_calls = 0
        self.assertEqual(route(state), "incomplete")

    def test_local_retry_budget_does_not_kill_run_when_another_task_exists(self) -> None:
        state = sample_state()
        ensure_tasks_from_tasks(state)
        state.tasks[0].status = "blocked"
        state.tasks.append(
            Task(
                id="T2",
                kind="derive",
                objective="备用路线",
                priority=5,
                status="open",
            )
        )
        state.local_retry_count = state.max_local_retries
        self.assertEqual(route(state), "solve")

    def test_route_does_not_replan_as_side_effect(self) -> None:
        state = sample_state()
        state.tasks[0].status = "blocked"
        state.local_retry_count = state.max_local_retries
        state.requirements = [
            CompletionRequirement(
                id="REQ_answer",
                kind="answer_candidate",
                status="unsatisfied",
            )
        ]

        self.assertEqual(route(state), "solve")
        self.assertEqual(state.replan_records, [])

    def test_protocol_failure_blocks_task_after_threshold(self) -> None:
        state = sample_state()
        ensure_tasks_from_tasks(state)
        task = state.tasks[0]

        first = record_protocol_failure(
            state,
            task,
            reason="JSON 解析失败",
            error_id="PROTO1",
        )
        second = record_protocol_failure(
            state,
            task,
            reason="JSON 解析失败",
            error_id="PROTO2",
        )

        self.assertFalse(first)
        self.assertTrue(second)
        self.assertEqual(task.protocol_failures, 2)
        self.assertEqual(task.status, "blocked")
        self.assertEqual(state.replan_records[0].trigger, "task_protocol_failure")
        self.assertEqual(state.tasks[-1].kind, "replan")
        self.assertIn("切换路线", state.tasks[-1].objective)
        self.assertIn("必须切换方法", state.tasks[-1].blocked_reason)

    def test_math_reject_counts_local_retry_and_replans_task(self) -> None:
        state = sample_state()
        ensure_tasks_from_tasks(state)
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="错误推进",
            new_results=[
                {
                    "result_type": "equation",
                    "statement": "x(x+3)=48",
                    "justification": "误读关系",
                    "depends_on": ["P1", "P2", "D1"],
                }
            ],
        )
        verification = StepVerification(
            verdict="reject",
            reason="关系误读",
            retry_instruction="重新使用 P2",
            error_category="unsupported_claim",
        )

        reject_step(state, step, verification)
        self.assertEqual(state.local_retry_count, 1)
        self.assertEqual(state.tasks[0].math_rejects, 1)
        self.assertEqual(state.tasks[0].status, "open")

        reject_step(state, step, verification)
        self.assertEqual(state.local_retry_count, 2)
        self.assertEqual(state.tasks[0].math_rejects, 2)
        self.assertEqual(state.tasks[0].status, "blocked")
        self.assertEqual(state.replan_records, [])
        self.assertIn("必须切换方法", state.tasks[0].blocked_reason)

    def test_replan_task_objective_does_not_stack_route_prefixes(self) -> None:
        state = sample_state()
        state.tasks = [
            Task(
                id="T1",
                kind="replan",
                objective="切换路线：切换路线：推进完成条件：提出可判分的候选答案",
                priority=100,
                status="open",
                requirement_ids=["REQ_answer"],
                math_rejects=1,
            )
        ]
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="仍然失败",
            new_results=[
                {
                    "result_type": "derived_fact",
                    "statement": "无效结论",
                    "justification": "重复路线",
                    "depends_on": ["P1"],
                }
            ],
        )

        reject_step(
            state,
            step,
            StepVerification(
                verdict="reject",
                reason="重复路线",
                retry_instruction="换方法",
                error_category="repeated_route",
            ),
        )
        fallback = _build_fallback_route_reset_task(
            state,
            state.tasks[0],
            reason=state.tasks[0].blocked_reason,
        )

        self.assertEqual(
            fallback.objective,
            "切换路线：推进完成条件：提出可判分的候选答案",
        )

    def test_budget_exhaustion_uses_emergency_finalizer(self) -> None:
        runtime = ReasoningRuntime(client=NoChatClient())
        result = runtime.run("求 1+1。")
        self.assertNotEqual(result.final_response, "incomplete")
        self.assertTrue(
            any(event.get("type") == "final" and event.get("emergency") for event in result.trace)
        )
        self.assertEqual(result.state.error_memory, [])
        self.assertFalse(
            any(
                "ReasoningStep JSON" in str(message.get("content", ""))
                for message in runtime.solver_history_messages
            )
        )
        self.assertTrue(any(event.get("type") == "solver_chat_error" for event in result.trace))
        self.assertFalse(any(event["type"] == "incomplete" for event in result.trace))

    def test_runtime_logger_appends_events_and_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {"REASONING_AGENT_CUSTOM2_LOG_DIR": temp_dir},
                clear=False,
            ):
                runtime = ReasoningRuntime(client=NoChatClient())
                result = runtime.run("求 1+1。", metadata={"idx": 7})

            run_dirs = list(Path(temp_dir).iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]
            events_path = run_dir / "events.jsonl"
            states_path = run_dir / "states.jsonl"
            self.assertTrue(events_path.exists())
            self.assertTrue(states_path.exists())
            self.assertFalse((run_dir / "state.json").exists())
            self.assertTrue((run_dir / "final.json").exists())

            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            states = [
                json.loads(line)
                for line in states_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertGreater(len(events), 1)
            self.assertEqual(len(events), len(states))
            self.assertEqual([event["seq"] for event in events], list(range(1, len(events) + 1)))
            self.assertEqual([state["seq"] for state in states], list(range(1, len(states) + 1)))
            self.assertNotEqual(result.final_response, "incomplete")

    def test_rollback_invalidates_descendants(self) -> None:
        state = sample_state()
        state.derived_results.extend(
            [
                DerivedResult(
                    id="R1",
                    result_type="equation",
                    statement="x(x+2)=48",
                    justification="由 P1 P2 D1",
                    depends_on=["P1", "P2", "D1"],
                ),
                DerivedResult(
                    id="R2",
                    result_type="derived_fact",
                    statement="x=6或x=-8",
                    justification="由 R1",
                    depends_on=["R1"],
                ),
            ]
        )
        rollback_invalid_result(state, "R1")
        self.assertEqual(state.derived_results[0].status, "invalid")
        self.assertEqual(state.derived_results[1].status, "invalid")

    def test_rollback_reopens_task(self) -> None:
        state = sample_state()
        state.derived_results.append(
            DerivedResult(
                id="R1",
                result_type="equation",
                statement="x(x+2)=48",
                justification="由 P1 P2 D1",
                depends_on=["P1", "P2", "D1"],
            )
        )
        state.tasks[0].status = "done"
        state.tasks[0].completed_by = ["R1"]
        rollback_invalid_result(state, "R1")
        self.assertEqual(state.tasks[0].status, "open")
        self.assertEqual(state.tasks[0].completed_by, [])

    def test_rollback_rejects_supported_candidate(self) -> None:
        state = sample_state()
        state.derived_results.append(
            DerivedResult(
                id="R1",
                result_type="derived_fact",
                statement="宽=6，长=8",
                justification="由计算",
                depends_on=["P1", "P2", "D1"],
            )
        )
        state.candidates.append(
            CandidateAnswer(
                id="C1",
                value="宽=6，长=8",
                status="verified",
                support_results=["R1"],
                verification_record="CV1",
            )
        )
        state.candidate_verifications.append(
            CandidateVerificationRecord(
                id="CV1", candidate_id="C1", verdict="accept", reason="checked"
            )
        )
        rollback_invalid_result(state, "R1")
        self.assertEqual(state.candidates[0].status, "rejected")

    def test_final_gate_blocks_open_required_task(self) -> None:
        state = sample_state()
        state.candidates.append(
            CandidateAnswer(
                id="C1",
                value="宽=6，长=8",
                status="verified",
                verification_record="CV1",
            )
        )
        self.assertFalse(can_finalize(state))

    def test_final_gate_allows_open_optional_task_when_requirements_satisfied(self) -> None:
        state = sample_state()
        state.tasks[0].required = False
        state.candidates.append(
            CandidateAnswer(
                id="C1",
                value="宽=6，长=8",
                status="verified",
                verification_record="CV1",
            )
        )
        self.assertTrue(can_finalize(state))

    def test_final_gate_blocks_unsatisfied_requirement(self) -> None:
        state = sample_state()
        state.requirements = [
            CompletionRequirement(
                id="REQ_answer",
                kind="answer_candidate",
                status="unsatisfied",
            )
        ]
        state.tasks = []
        self.assertFalse(can_finalize(state))

    def test_final_gate_blocks_candidate_conflict(self) -> None:
        state = sample_state()
        state.tasks = []
        state.candidates.append(
            CandidateAnswer(
                id="C1",
                value="宽=6，长=8",
                status="conflict",
                verification_record="CV1",
            )
        )
        self.assertFalse(can_finalize(state))

    def test_candidate_verification_record_is_required_for_verified_candidate(self) -> None:
        state = sample_state()
        state.tasks = []
        state.candidates.append(
            CandidateAnswer(id="C1", value="宽=6，长=8", status="verified")
        )
        self.assertIn("C1: verified candidate needs independent verification", validate_state_invariants(state))

    def test_candidate_verification_can_close_verify_task(self) -> None:
        state = sample_state()
        state.tasks = [
            Task(
                id="T1",
                kind="verify",
                objective="独立验证候选答案",
                candidate_id="C1",
            )
        ]
        candidate = CandidateAnswer(id="C1", value="宽=6，长=8")
        state.candidates = [candidate]
        apply_candidate_verification(
            state,
            candidate,
            CandidateVerification(
                verdict="accept",
                reason="代回成立",
                **independent_verification_fields(
                    "直接代回原方程", "检查另一根与正长度边界"
                ),
            ),
        )
        self.assertEqual(candidate.status, "verified")
        self.assertEqual(state.tasks[0].status, "done")
        self.assertEqual(state.tasks[0].candidate_verification_record, "CV1")

    def test_requirements_are_inferred_by_problem_type(self) -> None:
        state = sample_state()
        state.problem_type = "extremum"
        requirements = infer_completion_requirements(state)
        self.assertEqual(
            [req.kind for req in requirements],
            [
                "answer_candidate",
                "candidate_verified",
                "lower_bound",
                "upper_bound",
                "construction_verified",
                "case_coverage",
            ],
        )

    def test_case_analysis_task_adds_case_coverage_requirement(self) -> None:
        state = sample_state()
        state.problem_type = "unknown"
        state.tasks.append(
            Task(
                id="T2",
                kind="case_analysis",
                objective="分类讨论",
            )
        )
        requirements = infer_completion_requirements(state)
        self.assertIn("case_coverage", [req.kind for req in requirements])

    def test_completion_requirement_is_added_for_all_possible_values_questions(self) -> None:
        state = sample_state()
        state.problem = "求所有可能值。"
        requirements = infer_completion_requirements(state)
        self.assertIn("completeness", [req.kind for req in requirements])

    def test_tasks_sync_to_dynamic_tasks(self) -> None:
        state = sample_state()
        ensure_tasks_from_tasks(state)
        self.assertEqual(len(state.tasks), 1)
        self.assertEqual(state.tasks[0].id, "T1")
        self.assertEqual(state.tasks[0].kind, "derive")
        self.assertEqual(state.tasks[0].objective, "建立面积方程")

    def test_formalizer_task_payload_maps_to_task_fields(self) -> None:
        payload = _normalize_task_payload(
            {
                "task_type": "formalize",
                "statement": "逐项比较四个选项的统计图形用途",
                "priority": 10,
                "depends_on_tasks": ["T0"],
            }
        )
        task = Task.model_validate(
            {
                **payload,
                "id": "T1",
                "status": "open",
            }
        )

        self.assertEqual(task.kind, "formalize")
        self.assertEqual(task.objective, "逐项比较四个选项的统计图形用途")
        self.assertEqual(task.depends_on, ["T0"])

    def test_no_executable_task_replans_from_unsatisfied_requirements(self) -> None:
        state = sample_state()
        state.tasks = []
        state.requirements = [
            CompletionRequirement(
                id="REQ_answer",
                kind="answer_candidate",
                status="unsatisfied",
                description="提出候选答案",
            )
        ]
        self.assertTrue(maybe_replan_from_requirements(state, "no_executable_task"))
        self.assertEqual(state.replan_records[0].trigger, "no_executable_task")
        self.assertEqual(state.tasks[0].kind, "derive")
        self.assertEqual(state.tasks[0].requirement_ids, ["REQ_answer"])

    def test_replan_does_not_reuse_terminal_duplicate_task(self) -> None:
        state = sample_state()
        state.tasks = [
            Task(
                id="T1",
                kind="derive",
                objective="推进完成条件：提出候选答案",
                status="blocked",
                requirement_ids=["REQ_answer"],
            )
        ]
        state.requirements = [
            CompletionRequirement(
                id="REQ_answer",
                kind="answer_candidate",
                status="unsatisfied",
                description="提出候选答案",
            )
        ]

        self.assertTrue(maybe_replan_from_requirements(state, "no_executable_task"))
        self.assertEqual(len(state.tasks), 2)
        self.assertEqual(state.tasks[-1].status, "open")
        self.assertNotEqual(state.replan_records[-1].new_tasks, ["T1"])

    def test_solver_messages_keep_history_and_inject_runtime_state_transiently(self) -> None:
        state = sample_state()
        state.requirements = infer_completion_requirements(state)
        ensure_tasks_from_tasks(state)
        history = [
            {
                "role": "assistant",
                "content": json.dumps({"type": "reasoning_step", "step_summary": "已验证"}),
            }
        ]

        messages = build_solver_messages(
            state,
            history_messages=history,
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1], history[0])
        self.assertEqual(messages[-1]["role"], "user")
        self.assertIn("## Completion Requirements", messages[-1]["content"])
        self.assertIn("## Dynamic Tasks", messages[-1]["content"])
        self.assertIn("## Strategy Guidance", messages[-1]["content"])
        self.assertNotIn("主技能参考文档", messages[-1]["content"])
        self.assertEqual(len(history), 1)

    def test_progress_audit_replans_when_no_new_evidence(self) -> None:
        state = sample_state()
        state.requirements = [
            CompletionRequirement(
                id="REQ_answer",
                kind="answer_candidate",
                status="unsatisfied",
                description="提出候选答案",
            )
        ]
        ensure_tasks_from_tasks(state)
        state.tasks[0].status = "active"
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="空推进",
        )

        audit = audit_step_progress(state, step, [])

        self.assertEqual(audit.verdict, "no_progress")
        self.assertEqual(state.replan_records[0].trigger, "no_new_evidence")

    def test_derived_result_status_has_no_candidate_lifecycle(self) -> None:
        with self.assertRaises(ValidationError):
            DerivedResult(
                id="R1",
                result_type="derived_fact",
                statement="x=1",
                justification="test",
                status="candidate",
            )

    def test_result_cannot_depend_on_unknown_id_in_invariant_check(self) -> None:
        state = sample_state()
        state.derived_results.append(
            DerivedResult(
                id="R1",
                result_type="derived_fact",
                statement="x=1",
                justification="bad",
                depends_on=["R404"],
            )
        )
        self.assertIn("R1: unknown dependency R404", validate_state_invariants(state))

    def test_legacy_solver_json_is_normalized_but_not_committed_as_ids(self) -> None:
        state = sample_state()
        legacy = {
            "new_definitions": [
                {
                    "id": "D99",
                    "term": "primitive element condition",
                    "definition": "alpha generates the extension iff it is not in a proper subfield",
                    "justification": "standard finite field theory",
                }
            ],
            "new_results": [
                {
                    "id": "R99",
                    "statement": "T is the complement of the proper subfield",
                    "justification": "by the generated field criterion",
                    "depends_on": ["D99"],
                }
            ],
            "closed_tasks": [{"id": "T1", "status": "completed"}],
            "request_finalization": False,
        }
        normalized = _normalize_reasoning_step_payload(legacy, state)
        step = ReasoningStep.model_validate(normalized)
        self.assertEqual(step.type, "reasoning_step")
        self.assertEqual(step.current_task, "T1")
        self.assertEqual(step.new_definitions[0].definition_type, "notation")
        self.assertNotIn("id", step.new_definitions[0].model_dump())
        self.assertEqual(step.new_results[0].result_type, "derived_fact")
        self.assertEqual(step.closed_tasks, ["T1"])
        verification = StepVerifier().verify(state, step)
        self.assertEqual(verification.verdict, "reject")
        self.assertEqual(verification.error_category, "dependency_error")

    def test_new_task_string_ids_are_dropped_during_normalization(self) -> None:
        state = sample_state()
        payload = {
            "current_task": "T1",
            "step_summary": "提出后续任务引用",
            "new_results": [],
            "new_tasks": ["T2", "T3"],
        }

        normalized = _normalize_reasoning_step_payload(payload, state)
        step = ReasoningStep.model_validate(normalized)

        self.assertEqual(step.new_tasks, [])

    def test_task_style_new_tasks_are_normalized(self) -> None:
        state = sample_state()
        payload = {
            "current_task": "T1",
            "step_summary": "提出后续任务",
            "new_results": [],
            "new_tasks": [
                {
                    "kind": "derive",
                    "objective": "prove upper bound",
                    "priority": 10,
                }
            ],
        }

        normalized = _normalize_reasoning_step_payload(payload, state)
        step = ReasoningStep.model_validate(normalized)

        self.assertEqual(len(step.new_tasks), 1)
        self.assertEqual(step.new_tasks[0].task_type, "derive")
        self.assertEqual(step.new_tasks[0].statement, "prove upper bound")
        self.assertEqual(step.new_tasks[0].priority, 10)

    def test_invalid_json_uses_retry_message_instead_of_error_memory(self) -> None:
        runtime = ReasoningRuntime(client=NoChatClient())

        def fake_solve_step(state: AgentState, debug_trace: list[dict], current_task: Task):
            runtime.last_solver_invalid = {
                "error": "2 validation errors for ReasoningStep",
                "response_excerpt": "{\"type\":\"reasoning_step\"",
            }
            return None

        with patch.object(runtime, "_solve_step", side_effect=fake_solve_step):
            with patch.object(runtime, "formalization_verifier", runtime.formalization_verifier):
                runtime.step_verifier = StepVerifier()
                result = runtime.run("求 1+1。")

        self.assertNotEqual(result.final_response, "incomplete")
        self.assertTrue(
            any(event.get("type") == "final" and event.get("emergency") for event in result.trace)
        )

    def test_solver_chat_error_does_not_append_json_retry_message(self) -> None:
        runtime = ReasoningRuntime(client=FailingChatClient(RuntimeError("400 Bad Request")))
        state = sample_state()
        debug_trace: list[dict] = []

        step = runtime._solve_step(state, debug_trace, state.tasks[0])

        self.assertIsNone(step)
        self.assertEqual(runtime.last_solver_invalid["kind"], "chat_error")
        self.assertEqual(runtime.solver_history_messages, [])
        self.assertTrue(any(item["type"] == "solver_chat_error" for item in debug_trace))

    def test_runtime_records_chat_error_without_json_retry_history(self) -> None:
        runtime = ReasoningRuntime(client=NoChatClient())

        def fake_solve_step(state: AgentState, debug_trace: list[dict], current_task: Task):
            runtime.last_solver_invalid = {
                "kind": "chat_error",
                "error": "400 Bad Request",
                "response_excerpt": "",
            }
            return None

        with patch.object(runtime, "_solve_step", side_effect=fake_solve_step):
            runtime.step_verifier = StepVerifier()
            result = runtime.run("求 1+1。")

        self.assertTrue(any(event.get("type") == "solver_chat_error" for event in result.trace))
        self.assertFalse(
            any(
                "上一轮输出不是合法的ReasoningStep JSON" in message.get("content", "")
                for message in runtime.solver_history_messages
            )
        )
        self.assertIn("current_task", _build_json_retry_message("err", "ex", "T1"))
        self.assertIn(
            "new_tasks.statement 是解题计划/阶段目标",
            _build_json_retry_message("err", "ex", "T1"),
        )

    def test_step_verifier_prompt_requires_full_json_schema(self) -> None:
        prompt = STEP_VERIFIER_SYSTEM_PROMPT
        self.assertIn('"verdict": "accept"', prompt)
        self.assertIn('"logical_validity"', prompt)
        self.assertIn('"definition_consistency"', prompt)
        self.assertIn('"dependency_validity"', prompt)
        self.assertIn('"task_completion_validity"', prompt)
        self.assertIn('"error_category": "none"', prompt)
        self.assertIn("dependency_error", prompt)
        self.assertIn("definition_drift", prompt)

    def test_prompts_explain_type_and_status_enum_meanings(self) -> None:
        self.assertIn("given_value：题目直接给出的数值", FORMALIZER_SYSTEM_PROMPT)
        self.assertIn("domain_constraint：题目或数学对象天然带来的定义域", FORMALIZER_SYSTEM_PROMPT)
        self.assertNotIn("initial_tasks", FORMALIZER_SYSTEM_PROMPT)
        self.assertIn("compute：执行代数、数值、递推等计算", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("kind/objective/priority/depends_on", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("选择题 Task 必须保持中立", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn('"T1"', STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("禁止使用 0、1、2 这类数字下标", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("objective 是解题计划/阶段目标", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("要比较的对象", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("已经完成的定义内容", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("求出候选解后代回检验", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("主技能参考文档", STRATEGY_PREPROCESS_SYSTEM_PROMPT)

        self.assertIn('CandidateAnswer.status="candidate"', SOLVER_SYSTEM_PROMPT)
        self.assertIn("definition_type 语义", SOLVER_SYSTEM_PROMPT)
        self.assertIn("result_type 语义", SOLVER_SYSTEM_PROMPT)
        self.assertIn("completeness：所有情况已覆盖", SOLVER_SYSTEM_PROMPT)
        self.assertIn('new_tasks 不能写 ["T2", "T3"]', SOLVER_SYSTEM_PROMPT)
        self.assertIn("继续证明", SOLVER_SYSTEM_PROMPT)
        self.assertIn("枚举反例", SOLVER_SYSTEM_PROMPT)
        self.assertIn("改换分类/构造路线", SOLVER_SYSTEM_PROMPT)
        self.assertIn("连续失败两次", SOLVER_SYSTEM_PROMPT)
        self.assertIn('"kind": "derive"', SOLVER_SYSTEM_PROMPT)
        self.assertIn('"task_type": "derive"', SOLVER_SYSTEM_PROMPT)
        self.assertIn("new_tasks.statement 是解题计划/阶段目标", SOLVER_SYSTEM_PROMPT)
        self.assertIn("new_tasks.statement 不得写已经完成的定义内容", SOLVER_SYSTEM_PROMPT)

        self.assertIn("dependency_validity：depends_on", STEP_VERIFIER_SYSTEM_PROMPT)
        self.assertIn("unsupported_claim：结论缺少足够依据", STEP_VERIFIER_SYSTEM_PROMPT)
        self.assertIn("candidate_failure：候选答案代回失败", STEP_VERIFIER_SYSTEM_PROMPT)
        self.assertIn("同一路线的重复尝试", STEP_VERIFIER_SYSTEM_PROMPT)
        self.assertIn("repeated_route", STEP_VERIFIER_SYSTEM_PROMPT)
        self.assertIn("等价变形", STEP_VERIFIER_SYSTEM_PROMPT)
        self.assertIn("候选答案或上下界", STEP_VERIFIER_SYSTEM_PROMPT)
        self.assertIn("最小/最大/最佳/紧", STEP_VERIFIER_SYSTEM_PROMPT)
        self.assertIn("所有可能值 / 所有解 / 完整分类 / 穷尽列表", CANDIDATE_VERIFIER_PROMPT)
        self.assertIn("completeness / case_coverage", FINALIZER_PROMPT)
        self.assertIn("\\boxed{}", FINALIZER_PROMPT)
        self.assertIn("预算耗尽前的最后一次请求", EMERGENCY_FINALIZER_PROMPT)
        self.assertIn("必须输出一个非空 answer", EMERGENCY_FINALIZER_PROMPT)
        self.assertIn("\\boxed{}", EMERGENCY_FINALIZER_PROMPT)

        self.assertIn("verdict 语义", CANDIDATE_VERIFIER_PROMPT)
        self.assertIn("verified：已通过 Candidate Verifier", CANDIDATE_VERIFIER_PROMPT)
        self.assertIn("更简单的反例", CANDIDATE_VERIFIER_PROMPT)
        self.assertIn("不是 ProblemFact", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("不要猜最终答案", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("first_step_instruction", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("initial_task_revisions", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("不得倾向任何具体选项", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("initial_task_revisions：可选的 Task 修正建议", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("objective 是解题计划/阶段目标", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("未转义的英文双引号", STRATEGY_PREPROCESS_SYSTEM_PROMPT)
        self.assertIn("不要依赖'标准答案'直接选择", STRATEGY_PREPROCESS_SYSTEM_PROMPT)

    def test_solver_context_keeps_runtime_selected_in_progress_task(self) -> None:
        state = sample_state()
        state.tasks = [
            Task(id="T1", kind="derive", objective="first task", priority=10),
            Task(id="T2", kind="compute", objective="selected task", priority=20),
        ]
        state.tasks[1].status = "active"

        current = choose_active_task(state)
        context = render_solver_context(state)

        self.assertIsNotNone(current)
        self.assertEqual(current.id, "T2")
        self.assertIn('"id": "T2"', context)
        self.assertIn("selected task", context)

    def test_solver_context_exposes_route_pressure_after_repeated_failures(self) -> None:
        state = sample_state()
        task = state.tasks[0]
        task.math_rejects = 2

        context = render_solver_context(state, current_task=task)

        self.assertIn("Route Pressure", context)
        self.assertIn("当前路线已连续失败两次", context)
        self.assertIn("继续证明 / 枚举反例 / 改换分类/构造路线", context)

    def test_solver_context_injects_strategy_guidance_as_untrusted_prompt_hint(self) -> None:
        state = sample_state()
        state.strategy_guidance.append(
            StrategyGuidance(
                id="S1",
                problem_type="numeric",
                core_methods=["先定义变量并建立方程"],
                phase_plan=["整理条件", "求解方程", "回代检查"],
                risk_controls=["检查正数约束"],
                do_not=["不要猜最终答案"],
                first_step_instruction="先把长和宽的关系写成变量表达式。",
            )
        )

        context = render_solver_context(state)

        self.assertIn("## Strategy Guidance", context)
        self.assertIn("先定义变量并建立方程", context)
        self.assertIn("只是未证明的路线建议", context)

    def test_strategy_guidance_is_not_authoritative_snapshot(self) -> None:
        state = sample_state()
        before = snapshot_authoritative_state(state)
        state.strategy_guidance.append(
            StrategyGuidance(
                id="S1",
                core_methods=["建立变量"],
                first_step_instruction="整理条件。",
            )
        )
        after = snapshot_authoritative_state(state)

        self.assertEqual(before, after)

    def test_strategy_payload_sanitizes_unproved_candidate_leaks(self) -> None:
        payload = {
            "problem_type": "numeric",
            "core_methods": ["先建立方程", "最终答案是 72"],
            "phase_plan": ["answer is 72"],
            "risk_controls": ["检查定义域"],
            "do_not": [],
            "first_step_instruction": "先猜最终答案为 72 再验证",
        }

        sanitized = _sanitize_strategy_payload(payload)

        self.assertEqual(sanitized["core_methods"], ["先建立方程"])
        self.assertEqual(sanitized["phase_plan"], [])
        self.assertIn(
            "removed_unproved_candidate_or_known_result",
            sanitized["sanitization_warnings"],
        )
        self.assertIn("不要猜最终答案", sanitized["first_step_instruction"])

    def test_strategy_payload_sanitizes_answer_leaking_task_revisions(self) -> None:
        payload = {
            "initial_task_revisions": [
                {
                    "kind": "derive",
                    "objective": "逐项比较所有选项与题干关键词的匹配程度",
                    "priority": 80,
                },
                {
                    "kind": "derive",
                    "objective": "选择 A 是正确选项",
                    "priority": 100,
                },
            ]
        }

        sanitized = _sanitize_strategy_payload(payload)

        self.assertEqual(len(sanitized["initial_task_revisions"]), 1)
        self.assertEqual(
            sanitized["initial_task_revisions"][0]["objective"],
            "逐项比较所有选项与题干关键词的匹配程度",
        )

    def test_strategy_task_revisions_replace_generic_fallback_task(self) -> None:
        state = sample_state()
        state.tasks = [
            Task(
                id="T1",
                kind="derive",
                objective="基于原题和已验证事实推进求解",
                priority=10,
            )
        ]
        output = StrategyOutput(
            initial_task_revisions=[
                {
                    "kind": "formalize",
                    "objective": "列出题干关键词和所有选项的适用场景，不判断最终选项。",
                    "priority": 90,
                    "depends_on": [],
                },
                {
                    "kind": "derive",
                    "objective": "逐项比较所有选项与题干关键词的匹配程度，先不提交 candidate_answers。",
                    "priority": 80,
                    "depends_on": [],
                },
            ]
        )

        update = _apply_strategy_task_revisions(state, output)

        self.assertEqual(update["invalidated_tasks"], ["T1"])
        self.assertEqual(update["created_tasks"], ["T2", "T3"])
        self.assertEqual(state.tasks[0].status, "invalid")
        self.assertEqual(state.tasks[1].created_by, "strategy")
        self.assertIn("逐项比较", state.tasks[2].objective)

    def test_strategy_task_revisions_preserve_optional_task(self) -> None:
        state = sample_state()
        output = StrategyOutput(
            initial_task_revisions=[
                {
                    "kind": "derive",
                    "objective": "建立主要求解结构",
                    "priority": 90,
                    "required": True,
                },
                {
                    "kind": "sanity_check",
                    "objective": "补充一个非必要的表示法说明",
                    "priority": 10,
                    "required": False,
                },
            ]
        )

        _apply_strategy_task_revisions(state, output)

        self.assertTrue(state.tasks[1].required)
        self.assertFalse(state.tasks[2].required)

    def test_strategy_dependencies_resolve_aliases_and_discard_unknown_or_cycles(self) -> None:
        state = sample_state()
        state.efficient_runtime = True
        output = StrategyOutput(
            execution_mode="macro",
            macro_tasks=[
                {
                    "kind": "derive",
                    "objective": "建立结构",
                    "priority": 100,
                    "depends_on": [],
                },
                {
                    "kind": "compute",
                    "objective": "计算公式",
                    "priority": 90,
                    "depends_on": ["T2_derive_structure"],
                },
                {
                    "kind": "verify",
                    "objective": "复核公式",
                    "priority": 80,
                    "depends_on": ["T3_compute_formula", "T99_unknown", "T4"],
                },
            ],
        )

        update = _apply_strategy_task_revisions(state, output)

        self.assertEqual(update["created_tasks"], ["T2", "T3", "T4"])
        self.assertEqual(state.tasks[2].depends_on, ["T2"])
        self.assertEqual(state.tasks[3].depends_on, ["T3"])
        self.assertEqual(len(update["dependency_warnings"]), 2)
        self.assertEqual(validate_state_invariants(state), [])

    def test_failed_route_memory_overrides_critic_and_candidate_accept(self) -> None:
        failed_reason = "交替窄带构造存在反例，单条直线可以同时分隔多对点。"
        state = sample_state()
        state.error_memory.append(
            ErrorRecord(
                id="E1",
                step_summary="使用交替窄带构造证明下界",
                category="unsupported_claim",
                reason=failed_reason,
                retry_instruction="改用不同下界构造",
            )
        )
        state.solution_draft.text = "继续使用交替窄带构造证明下界，故答案成立。"
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="重复下界构造",
            solution_draft=state.solution_draft.text,
            candidate_answers=["2025"],
        )
        draft = SolutionDraft(
            task_id="T1",
            text=state.solution_draft.text,
            candidate_answers=["2025"],
        )
        critic_client = SequenceChatClient(
            [
                json.dumps(
                    {
                        "verdict": "accept",
                        "accepted_claims": [],
                        "invalid_claims": [],
                        "candidate_assessment": "supported",
                        "reason": "构造正确",
                        "repair_instruction": "",
                        "failed_route_summary": "",
                    },
                    ensure_ascii=False,
                )
            ]
        )
        critique = DraftCritic(critic_client).critique(state, step, draft)
        self.assertEqual(critique.verdict, "reject_route")
        self.assertEqual(critique.failed_route_assessment, "unresolved")

        candidate = CandidateAnswer(id="C1", value="2025")
        candidate_client = SequenceChatClient(
            [
                json.dumps(
                    {
                        "verdict": "accept",
                        "reason": "候选成立",
                        **independent_verification_fields(
                            "直接检查构造的分隔性质",
                            "尝试构造单条直线覆盖多对点的反例",
                        ),
                    },
                    ensure_ascii=False,
                )
            ]
        )
        verification = CandidateVerifier(candidate_client).verify(state, candidate)
        self.assertEqual(verification.verdict, "reject")
        self.assertEqual(verification.failed_route_assessment, "unresolved")

    def test_strategy_preprocess_fallback_without_chat_client(self) -> None:
        state = sample_state()
        runtime = ReasoningRuntime(client=NoChatClient())
        trace: list[dict] = []
        debug_trace: list[dict] = []
        logger = RuntimeLogger(run_dir=None)

        runtime._strategy_preprocess(state, trace, debug_trace, logger)

        self.assertEqual(len(state.strategy_guidance), 1)
        self.assertEqual(state.strategy_guidance[0].id, "S1")
        self.assertTrue(
            any("不要猜最终答案" in item for item in state.strategy_guidance[0].do_not)
        )
        self.assertTrue(
            any(event["type"] == "strategy_preprocess_committed" for event in trace)
        )

    def test_strategy_preprocess_retries_invalid_json_once(self) -> None:
        state = sample_state()
        state.tasks = [
            Task(
                id="T1",
                kind="derive",
                objective="基于原题和已验证事实推进求解",
                priority=10,
            )
        ]
        client = SequenceChatClient(
            [
                '{"problem_type":"choice","do_not":["不要依赖"标准答案"直接选择"]}',
                json.dumps(
                    {
                        "problem_type": "choice",
                        "core_methods": ["逐项比较选项"],
                        "phase_plan": ["先列出适用场景"],
                        "risk_controls": ["避免倾向具体选项"],
                        "do_not": ["不要依赖'标准答案'直接选择"],
                        "first_step_instruction": "列出题干关键词，暂不判断最优选项。",
                        "initial_task_revisions": [
                            {
                                "kind": "derive",
                                "objective": "逐项比较所有选项与题干关键词的匹配程度，先不提交 candidate_answers。",
                                "priority": 80,
                                "depends_on": [],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        runtime = ReasoningRuntime(client=client)
        trace: list[dict] = []
        debug_trace: list[dict] = []
        logger = RuntimeLogger(run_dir=None)

        runtime._strategy_preprocess(state, trace, debug_trace, logger)

        self.assertEqual(len(client.calls), 2)
        self.assertTrue(any(item["type"] == "strategy_preprocess_retry" for item in debug_trace))
        self.assertEqual(state.strategy_guidance[0].problem_type, "choice")
        self.assertEqual(state.tasks[0].status, "invalid")
        self.assertEqual(state.tasks[1].created_by, "strategy")

    def test_strategy_preprocessor_injects_skill_reference_as_separate_message(self) -> None:
        state = sample_state()
        client = SequenceChatClient(
            [
                json.dumps(
                    {
                        "problem_type": "随机过程",
                        "core_methods": ["先判断转移结构"],
                        "phase_plan": ["建模后再计算"],
                        "risk_controls": ["不要混淆静态概率和过程"],
                        "do_not": ["不要猜答案"],
                        "first_step_instruction": "整理状态和时间索引。",
                        "initial_task_revisions": [],
                    },
                    ensure_ascii=False,
                )
            ]
        )
        runtime = ReasoningRuntime(client=client)
        debug_trace: list[dict] = []
        selected_skills = [
            SelectedStrategySkill(
                category="随机过程",
                path="skills/随机过程/随机过程skill.md",
                prompt="Markov 链。",
            )
        ]

        output = runtime._call_strategy_preprocessor(
            state,
            debug_trace,
            selected_skills=selected_skills,
        )

        messages = client.calls[0]["messages"]
        self.assertEqual(len(messages), 3)
        self.assertIn("主技能参考文档", messages[1]["content"])
        self.assertIn("Markov 链。", messages[1]["content"])
        self.assertNotIn("已验证 ProblemFact", messages[1]["content"])
        self.assertIn("已验证 ProblemFact", messages[2]["content"])
        self.assertEqual(output.selected_skill_ids, ["随机过程"])

    def test_replan_output_to_tasks_rejects_answer_leaks_and_keeps_safe_tasks(self) -> None:
        state = sample_state()
        blocked = state.tasks[0]
        output = ReplanOutput(
            diagnosis="重复路线",
            new_tasks=[
                {
                    "kind": "derive",
                    "objective": "最终答案是 A",
                    "priority": 100,
                    "depends_on": [],
                },
                {
                    "kind": "derive",
                    "objective": "换用最小反例法建立必要条件，不提交候选答案。",
                    "priority": 110,
                    "depends_on": ["P1"],
                },
            ],
        )

        tasks = _replan_output_to_tasks(state, blocked, output)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].kind, "derive")
        self.assertIn("最小反例", tasks[0].objective)
        self.assertEqual(tasks[0].created_by, "replanner")

    def test_blocked_task_uses_model_replanner_before_fallback(self) -> None:
        state = sample_state()
        state.tasks[0].status = "blocked"
        state.tasks[0].math_rejects = 2
        state.tasks[0].blocked_reason = "连续数学拒绝 2 次，必须切换方法。"
        verification = StepVerification(
            verdict="reject",
            reason="重复路线",
            retry_instruction="换方法",
            error_category="repeated_route",
        )
        client = SequenceChatClient(
            [
                json.dumps(
                    {
                        "diagnosis": "上界证明循环",
                        "avoid_routes": ["不要重复未证上界"],
                        "reuse_results": ["P1"],
                        "new_tasks": [
                            {
                                "kind": "derive",
                                "objective": "换用反证法建立必要条件，不提交候选答案。",
                                "priority": 120,
                                "depends_on": ["P1"],
                            }
                        ],
                        "first_step_instruction": "先修复循环论证。",
                    },
                    ensure_ascii=False,
                )
            ]
        )
        runtime = ReasoningRuntime(client=client)
        debug_trace: list[dict] = []

        record = runtime._replan_blocked_task(
            state,
            state.tasks[0],
            verification,
            debug_trace,
        )

        self.assertEqual(record.trigger, "model_replan")
        self.assertEqual(record.reason, "上界证明循环")
        self.assertEqual(state.tasks[-1].created_by, "replanner")
        self.assertIn("反证法", state.tasks[-1].objective)
        self.assertTrue(any(item["type"] == "replanner_response" for item in debug_trace))

    def test_replanner_context_renders_structured_markdown_not_payload_json(self) -> None:
        state = sample_state()
        state.error_memory.append(
            ErrorRecord(
                id="E1",
                step_summary="重复上界证明",
                category="repeated_route",
                reason="循环论证",
                retry_instruction="换方法",
            )
        )
        message = _build_replanner_context_message(
            state,
            state.tasks[0],
            StepVerification(
                verdict="reject",
                reason="重复路线",
                retry_instruction="换方法",
                error_category="repeated_route",
            ),
        )

        self.assertIn("## Problem", message)
        self.assertIn("## Blocked Task", message)
        self.assertIn("## Recent Error Memory", message)
        self.assertIn("## Replan Instruction", message)
        self.assertIn('"category": "repeated_route"', message)
        self.assertFalse(message.lstrip().startswith("{"))

    def test_solver_step_uses_strategy_guidance_without_skill_reference_message(self) -> None:
        client = SequenceChatClient(
            [
                json.dumps(
                    {
                        "type": "reasoning_step",
                        "current_task": "T1",
                        "step_summary": "整理变量",
                    },
                    ensure_ascii=False,
                )
            ]
        )
        runtime = ReasoningRuntime(client=client)
        runtime.selected_strategy_skills = [
            SelectedStrategySkill(
                category="数学分析",
                path="skills/数学分析/数学分析skill.md",
                prompt="极限、连续、导数。",
            )
        ]
        state = sample_state()
        state.strategy_guidance = [
            StrategyGuidance(
                id="S1",
                status="active",
                problem_type="数学分析",
                selected_skill_ids=["数学分析"],
                core_methods=["用单调性和极限控制表达式"],
                phase_plan=["先建立不等式"],
            )
        ]

        step = runtime._solve_step(state, [], state.tasks[0])

        self.assertIsNotNone(step)
        messages = client.calls[0]["messages"]
        self.assertEqual(len(messages), 2)
        self.assertIn("## Problem", messages[-1]["content"])
        self.assertIn("## Strategy Guidance", messages[-1]["content"])
        self.assertIn("用单调性和极限控制表达式", messages[-1]["content"])
        self.assertNotIn("主技能参考文档", messages[-1]["content"])
        self.assertNotIn("极限、连续、导数。", messages[-1]["content"])

    def test_replanner_receives_complete_selected_skill_prompts(self) -> None:
        skills = [
            SelectedStrategySkill(
                category="数学分析",
                path="skills/数学分析/数学分析skill.md",
                prompt="主技能" * 1000,
            ),
            SelectedStrategySkill(
                category="概率论",
                path="skills/概率论/概率论skill.md",
                prompt="辅助技能" * 1000,
            ),
        ]

        message = _build_replanner_skill_reference_message(skills)

        self.assertIn("完整技能参考文档", message)
        self.assertIn("主技能【数学分析】", message)
        self.assertIn("辅助技能【概率论】", message)
        self.assertIn(skills[0].prompt, message)
        self.assertIn(skills[1].prompt, message)
        self.assertNotIn("...[已截断]", message)

    def test_formalizer_retries_invalid_json_once(self) -> None:
        client = SequenceChatClient(
            [
                '{"problem_type":"unknown","problem_facts":["bad"',
                json.dumps(
                    {
                        "problem_facts": [
                            {
                                "fact_type": "target",
                                "statement": "求解题目",
                                "source_text": "求解题目",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        runtime = ReasoningRuntime(client=client)
        state = AgentState(problem="求解题目")
        debug_trace: list[dict] = []

        output = runtime._call_formalizer(state, debug_trace)

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(len(output.problem_facts), 1)
        self.assertTrue(any(item["type"] == "formalizer_retry" for item in debug_trace))

    def test_domain_classification_sanitizes_to_allowed_categories(self) -> None:
        output = _sanitize_domain_classification(
            DomainClassificationOutput(
                primary_category="不存在的领域",
                secondary_categories=["数学分析", "数学分析", "概率论", "高等代数"],
                confidence=1.5,
                reason="需要分析方法",
            )
        )

        self.assertEqual(output.primary_category, "unknown")
        self.assertEqual(
            output.secondary_categories,
            ["mathematical_analysis", "probability"],
        )
        self.assertEqual(output.confidence, 1.0)

    def test_strategy_skill_selector_prefers_english_skill_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_dir = root / "skill2_en" / "mathematical_analysis"
            skill_dir.mkdir(parents=True)
            (skill_dir / "mathematical_analysis_skill.md").write_text(
                "# Mathematical Analysis\n" + "主技能全文。" * 3000,
                encoding="utf-8",
            )
            probability_dir = root / "skill2_en" / "probability"
            probability_dir.mkdir(parents=True)
            (probability_dir / "probability_skill.md").write_text(
                "# Probability\n" + "辅助技能全文。" * 1000,
                encoding="utf-8",
            )
            algebra_dir = root / "skill2_en" / "linear_algebra"
            algebra_dir.mkdir(parents=True)
            (algebra_dir / "linear_algebra_skill.md").write_text(
                "# Linear Algebra\n不应被选中。",
                encoding="utf-8",
            )

            selected = select_strategy_skills(
                "数学分析",
                ["概率论", "高等代数"],
                repo_root=root,
            )

        self.assertEqual(
            [skill.id for skill in selected],
            ["mathematical_analysis", "probability"],
        )
        self.assertEqual(
            selected[0].path,
            "skill2_en/mathematical_analysis/mathematical_analysis_skill.md",
        )
        self.assertEqual(selected[1].path, "skill2_en/probability/probability_skill.md")
        self.assertTrue(selected[0].prompt.startswith("# Mathematical Analysis"))
        self.assertGreater(len(selected[0].prompt), 5000)
        self.assertGreater(len(selected[1].prompt), 5000)
        self.assertTrue(selected[1].prompt.endswith("辅助技能全文。"))

    def test_strategy_skill_reference_message_is_independent_from_runtime_context(self) -> None:
        state = sample_state()
        state.problem_type = "随机过程"
        state.secondary_problem_types = ["概率论"]
        state.classification_confidence = 0.9
        state.classification_reason = "含随时间演化模型"
        skills = [
            SelectedStrategySkill(
                category="随机过程",
                path="skills/随机过程/随机过程skill.md",
                prompt="Markov 链、Poisson 过程。",
            ),
            SelectedStrategySkill(
                category="概率论",
                path="skills/概率论/概率论skill.md",
                prompt="分布、期望、方差。",
            ),
        ]

        skill_message = _build_strategy_skill_reference_message(skills)
        context_message = _build_strategy_preprocess_context_message(
            state=state,
            metadata={"source": "unit"},
        )

        self.assertIn("主技能参考文档：\n【随机过程】", skill_message)
        self.assertIn("辅助技能参考文档：\n【概率论】", skill_message)
        self.assertIn("Markov 链、Poisson 过程。", skill_message)
        self.assertIn("分布、期望、方差。", skill_message)
        self.assertNotIn("已验证 ProblemFact", skill_message)
        self.assertNotIn("当前 Task", skill_message)
        self.assertNotIn("selected_strategy_skills", skill_message)
        self.assertNotIn('"prompt"', skill_message)
        self.assertIn("已验证 ProblemFact", context_message)
        self.assertIn("当前 Task", context_message)
        self.assertIn("输出要求", context_message)

    def test_finalizer_retries_invalid_json_once(self) -> None:
        client = SequenceChatClient(
            [
                '{"answer":"bad"',
                json.dumps(
                    {"answer": "\\boxed{2}", "reasoning_summary": "verified"},
                    ensure_ascii=False,
                ),
            ]
        )
        runtime = ReasoningRuntime(client=client)
        debug_trace: list[dict] = []

        answer = runtime._finalize(sample_state(), debug_trace)

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(answer.answer, "\\boxed{2}")
        self.assertTrue(any(item["type"] == "finalizer_retry" for item in debug_trace))

    def test_step_verifier_retries_invalid_json_once(self) -> None:
        client = SequenceChatClient(
            [
                '{"verdict":"accept"',
                json.dumps(
                    {
                        "verdict": "accept",
                        "reason": "ok",
                        "error_category": "none",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        verifier = StepVerifier(client=client)
        step = ReasoningStep(
            type="reasoning_step",
            current_task="T1",
            step_summary="建立方程",
            new_results=[
                {
                    "result_type": "equation",
                    "statement": "x(x+2)=48",
                    "justification": "面积公式",
                    "depends_on": ["P1", "P2", "D1"],
                }
            ],
        )

        result = verifier.verify(sample_state(), step)

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(result.verdict, "accept")

    def test_candidate_verifier_retries_invalid_json_once(self) -> None:
        client = SequenceChatClient(
            [
                '{"verdict":"accept"',
                json.dumps(
                    {
                        "verdict": "accept",
                        "reason": "ok",
                        **independent_verification_fields(
                            "直接代回原方程", "检查负根和定义域边界"
                        ),
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        verifier = CandidateVerifier(client=client)

        result = verifier.verify(sample_state(), CandidateAnswer(id="C1", value="2"))

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(result.verdict, "accept")

    def test_candidate_verifier_retries_then_rejects_accept_without_independent_checks(self) -> None:
        response = json.dumps({"verdict": "accept", "reason": "沿用原推导"}, ensure_ascii=False)
        client = SequenceChatClient([response, response])
        verifier = CandidateVerifier(client=client)

        result = verifier.verify(sample_state(), CandidateAnswer(id="C1", value="2"))

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(result.verdict, "reject")
        retry_message = client.calls[1]["messages"][-1]["content"]
        self.assertIn("independent_method", retry_message)
        self.assertIn("falsification_attempt", retry_message)

    def test_candidate_verifier_accepts_independent_checks(self) -> None:
        client = SequenceChatClient(
            [
                json.dumps(
                    {
                        "verdict": "accept",
                        "reason": "独立检查通过",
                        **independent_verification_fields(
                            "使用另一表示并直接代回",
                            "枚举最小边界并尝试构造反例",
                        ),
                    },
                    ensure_ascii=False,
                )
            ]
        )

        result = CandidateVerifier(client=client).verify(
            sample_state(), CandidateAnswer(id="C1", value="2")
        )

        self.assertEqual(result.verdict, "accept")
        self.assertEqual(result.independent_method, "使用另一表示并直接代回")

    def test_candidate_verifier_rejects_exact_solver_route_repetition(self) -> None:
        candidate = CandidateAnswer(
            id="C1",
            value="2",
            source_solution_draft="使用生成函数展开并提取目标系数",
        )
        payload = {
            "verdict": "accept",
            "reason": "检查通过",
            **independent_verification_fields(
                method="使用生成函数展开并提取目标系数",
                attempt="检查最小参数情形",
            ),
        }
        client = SequenceChatClient(
            [json.dumps(payload, ensure_ascii=False), json.dumps(payload, ensure_ascii=False)]
        )

        result = CandidateVerifier(client=client).verify(sample_state(), candidate)

        self.assertEqual(result.verdict, "reject")
        self.assertEqual(len(client.calls), 2)

    def test_candidate_verifier_uses_candidate_source_route_snapshot(self) -> None:
        state = sample_state()
        state.solution_draft = SolutionDraftState(
            version=3,
            task_id="T1",
            text="原始路线：建立递推关系后求解。",
            status="accepted",
        )
        state.strategy_guidance = [
            StrategyGuidance(
                id="S1",
                status="active",
                core_methods=["递推法"],
            )
        ]
        candidate = register_candidate(state, "2", [])
        state.solution_draft = SolutionDraftState(
            version=4,
            task_id="T2",
            text="后续反证草稿，不是候选来源路线。",
            status="accepted",
        )

        messages = build_candidate_verifier_messages(state, candidate)
        solver_route = json.loads(messages[1]["content"])["solver_route"]

        self.assertEqual(solver_route["source_draft_version"], 3)
        self.assertEqual(solver_route["solution_draft"], "原始路线：建立递推关系后求解。")
        self.assertEqual(solver_route["strategy_methods"], ["递推法"])

    def test_candidate_verifier_messages_include_completion_requirements(self) -> None:
        state = sample_state()
        state.requirements = infer_completion_requirements(state)
        candidate = CandidateAnswer(id="C1", value="1234")

        messages = build_candidate_verifier_messages(state, candidate)
        payload = json.loads(messages[1]["content"])

        self.assertIn("completion_requirements", payload)
        self.assertGreater(len(payload["completion_requirements"]), 0)
        self.assertEqual(payload["candidate"]["value"], "1234")
        self.assertEqual(payload["choice_options"], [])
        self.assertIn("solver_route", payload)
        self.assertIn("required_verification_mode", payload)

    def test_choice_problem_verifier_context_includes_options(self) -> None:
        state = sample_state()
        state.problem = "示例选择题：A. 选项甲 B. 选项乙 C. 选项丙 D. 选项丁"
        candidate = CandidateAnswer(id="C1", value="C")

        messages = build_candidate_verifier_messages(state, candidate)
        payload = json.loads(messages[1]["content"])

        self.assertEqual(
            payload["choice_options"],
            [
                "A. 选项甲",
                "B. 选项乙",
                "C. 选项丙",
                "D. 选项丁",
            ],
        )

    def test_choice_verifier_prompts_require_option_by_option_comparison(self) -> None:
        self.assertIn("逐个比较所有选项", CANDIDATE_VERIFIER_PROMPT)
        self.assertIn("明显更优的选项", CANDIDATE_VERIFIER_PROMPT)
        self.assertIn("题干关键词与选项功能", CANDIDATE_VERIFIER_PROMPT)
        self.assertIn("逐项对比", FINALIZER_PROMPT)
        self.assertIn("没有明显更优选项被遗漏", FINALIZER_PROMPT)
        self.assertIn("题干关键词与选项功能已正确匹配", FINALIZER_PROMPT)

    def test_step_verifier_messages_include_recent_failed_approaches(self) -> None:
        state = sample_state()
        state.error_memory.append(
            ErrorRecord(
                id="E1",
                branch_id="B1",
                step_summary="沿用同一路线补洞",
                category="repeated_route",
                reason="same route",
                retry_instruction="换方法",
                related_ids=["T1"],
            )
        )

        messages = build_step_verifier_messages(
            state,
            ReasoningStep(
                type="reasoning_step",
                current_task="T1",
                step_summary="继续补洞",
            ),
        )
        payload = json.loads(messages[1]["content"])
        self.assertIn("recent_failed_approaches", payload)
        self.assertEqual(payload["recent_failed_approaches"][0]["category"], "repeated_route")
        self.assertEqual(payload["recent_failed_approaches"][0]["step_summary"], "沿用同一路线补洞")

    def test_done_tasks_without_candidate_add_candidate_extraction_task(self) -> None:
        state = sample_state()
        state.tasks[0].status = "done"
        state.tasks[0].completed_by = ["R1"]
        state.derived_results.append(
            DerivedResult(
                id="R1",
                result_type="derived_fact",
                statement="最终值为 72",
                justification="由计算得到",
                depends_on=["P1"],
            )
        )

        task = _maybe_add_candidate_extraction_task(state)

        self.assertIsNotNone(task)
        self.assertEqual(task.id, "T2")
        self.assertEqual(task.kind, "verify")
        self.assertEqual(task.priority, 100)
        self.assertIn("candidate_answers", task.objective)

    def test_request_finalization_does_not_skip_next_required_task(self) -> None:
        state = sample_state()
        state.execution_mode = "macro"
        state.tasks[0].status = "done"
        state.tasks.append(
            Task(
                id="T2",
                kind="compute",
                objective="完成必要的小规模枚举",
                priority=80,
                required=True,
            )
        )

        next_task = _next_task_after_accepted_draft(
            state, state.tasks[0], request_finalization=True
        )

        self.assertIsNotNone(next_task)
        self.assertEqual(next_task.id, "T2")

    def test_candidate_falsification_task_is_added_once(self) -> None:
        state = sample_state()
        state.tasks[0].status = "done"
        state.candidates = [CandidateAnswer(id="C1", value="2")]

        first = _maybe_add_candidate_falsification_task(state)
        second = _maybe_add_candidate_falsification_task(state)

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertTrue(first.required)
        self.assertEqual(first.kind, "sanity_check")
        self.assertEqual(first.created_by, "candidate_falsification")

    def test_unbound_counterexample_task_does_not_cover_candidate(self) -> None:
        state = sample_state()
        state.tasks[0].status = "done"
        state.tasks.append(
            Task(
                id="T2",
                kind="sanity_check",
                objective="用小规模枚举检查边界并尝试构造反例",
                status="done",
                required=True,
            )
        )
        state.candidates = [CandidateAnswer(id="C1", value="2")]

        task = _maybe_add_candidate_falsification_task(state)

        self.assertIsNotNone(task)
        self.assertEqual(task.candidate_id, "C1")

    def test_falsification_task_is_scoped_to_candidate_and_route_version(self) -> None:
        state = sample_state()
        state.tasks[0].status = "done"
        first_candidate = CandidateAnswer(
            id="C1", value="2", source_draft_version=3
        )
        second_candidate = CandidateAnswer(
            id="C2", value="3", source_draft_version=3
        )
        state.candidates = [first_candidate, second_candidate]

        first_task = _maybe_add_candidate_falsification_task(state)
        first_task.status = "done"
        first_task.completed_by = ["C1"]
        second_task = _maybe_add_candidate_falsification_task(state)

        self.assertEqual(first_task.candidate_id, "C1")
        self.assertEqual(second_task.candidate_id, "C2")
        self.assertEqual(second_task.candidate_source_draft_version, 3)

        second_task.status = "done"
        second_task.completed_by = ["C2"]
        first_candidate.source_draft_version = 4
        repeated_task = _maybe_add_candidate_falsification_task(state)

        self.assertEqual(repeated_task.candidate_id, "C1")
        self.assertEqual(repeated_task.candidate_source_draft_version, 4)

    def test_terminal_candidate_extraction_task_does_not_block_new_one(self) -> None:
        state = sample_state()
        state.tasks[0].status = "done"
        state.tasks[0].completed_by = ["R1"]
        state.tasks.append(
            Task(
                id="T2",
                kind="verify",
                objective=(
                    "基于已 verified 的 ProblemFacts、Definitions、DerivedResults 提出最终候选答案；"
                    "本步必须把候选写入 candidate_answers，并说明支持它的已验证结果。"
                ),
                status="invalid",
                priority=100,
                requirement_ids=["REQ_candidate_verified"],
            )
        )
        state.derived_results.append(
            DerivedResult(
                id="R1",
                result_type="derived_fact",
                statement="宽=6，长=8",
                justification="由计算",
                depends_on=["P1", "P2", "D1"],
            )
        )

        task = _maybe_add_candidate_extraction_task(state)

        self.assertIsNotNone(task)
        self.assertEqual(task.id, "T3")
        self.assertEqual(task.status, "open")


if __name__ == "__main__":
    unittest.main()
