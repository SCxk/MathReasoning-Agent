import json
import unittest
from unittest.mock import patch

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom2.agent import Custom2Agent
from reasoning_agent.custom2.models import AgentState, ProblemFact, Task
from reasoning_agent.custom2.runner import ReasoningRuntime
from reasoning_agent.custom2.prompts import REPLANNER_SYSTEM_PROMPT
from reasoning_agent.custom2.schemas import CritiqueOutput, ReasoningStep, StepVerification
from reasoning_agent.custom2.solver_text_runtime import (
    SOLVER_TEXT_SYSTEM_PROMPT, SolverTextReasoningRuntime,
    format_solver_text_response, text_to_reasoning_step,
)
from reasoning_agent.custom2.state_manager import (
    commit_step, reasoning_step_to_solution_draft, validate_reasoning_step_protocol,
)
from test_custom2_efficient_runtime import EfficientRuntimeFakeClient


class SolverTextClient(EfficientRuntimeFakeClient):
    def __init__(self, texts=None, repair=False, strategy=None):
        super().__init__(repair=repair)
        self.texts = list(texts or ["由整数加法可得 1+1=2。\n整题候选答案：2"])
        self.strategy = strategy

    def chat(self, messages, **kwargs):
        system = messages[0]["content"]
        if system == SOLVER_TEXT_SYSTEM_PROMPT:
            self.calls.append(messages)
            self.call_kwargs.append(kwargs)
            self.solver_calls += 1
            if "独立尝试推翻当前候选" in json.dumps(messages, ensure_ascii=False):
                return "直接检查边界与最小规模，未发现反例。\n整题候选答案：2"
            return self.texts[min(self.solver_calls - 1, len(self.texts) - 1)]
        if self.strategy is not None and "解题策略设计器" in system:
            self.calls.append(messages)
            self.call_kwargs.append(kwargs)
            return json.dumps(self.strategy, ensure_ascii=False)
        return super().chat(messages, **kwargs)


class SolverTextAdapterTests(unittest.TestCase):
    def setUp(self):
        self.task = Task(id="T1", kind="compute", objective="计算当前等式", status="active")
        self.state = AgentState(problem="求 1+1。", tasks=[self.task], problem_facts=[
            ProblemFact(id="P1", fact_type="target", statement="求 1+1", source_text="求 1+1", status="verified"),
            ProblemFact(id="P2", fact_type="target", statement="未验证", source_text="", status="invalid"),
        ])

    def test_plain_text_is_a_proposal_not_an_accepted_result(self):
        text = "由加法定义得 1+1=2。"
        step = text_to_reasoning_step(text, self.state, self.task)
        self.assertEqual(step.solution_draft, text)
        self.assertEqual(step.new_results[0].statement, text)
        self.assertEqual(step.new_results[0].depends_on, ["P1"])
        self.assertEqual(step.closed_tasks, ["T1"])
        self.assertFalse(step.request_finalization)
        self.assertEqual(step.candidate_answers, [])
        self.assertEqual(self.state.derived_results, [])
        self.assertEqual(self.task.status, "active")
        self.assertEqual(validate_reasoning_step_protocol(self.state, step, self.task), [])
        commit_step(self.state, step, StepVerification(verdict="accept", reason="计算成立"))
        self.assertEqual(self.state.derived_results[0].statement, text)
        self.assertEqual(self.task.status, "done")

    def test_subtask_box_and_unmarked_number_are_not_final_candidates(self):
        for text in [r"本任务结论：\boxed{2}", "本任务结论：2", "暂不能证明当前等式。"]:
            with self.subTest(text=text):
                step = text_to_reasoning_step(text, self.state, self.task)
                self.assertEqual(step.candidate_answers, [])
                self.assertEqual(self.state.candidates, [])

    def test_marked_candidate_keeps_all_results(self):
        step = text_to_reasoning_step(
            "各部分已计算。\n整题候选答案：(1) 2；(2) 3", self.state, self.task,
        )
        self.assertEqual(step.candidate_answers, ["(1) 2；(2) 3"])

    def test_ambiguous_or_verbose_candidate_is_not_guessed(self):
        for text in [
            "整题候选答案：2\n整题候选答案：3",
            "整题候选答案：我们还需要推导，因此暂时无法确定。",
        ]:
            self.assertEqual(text_to_reasoning_step(text, self.state, self.task).candidate_answers, [])

    def test_valid_json_solver_response_remains_supported(self):
        original = ReasoningStep(
            type="reasoning_step", current_task="T1", step_summary="计算",
            solution_draft="1+1=2", candidate_answers=["2"],
        )
        parsed = text_to_reasoning_step(original.model_dump_json(), self.state, self.task)
        self.assertEqual(parsed.candidate_answers, ["2"])
        self.assertEqual(parsed.solution_draft, "1+1=2")

    def test_truncated_and_empty_text_do_not_enter_critique(self):
        for response in ["", {"content": "尚未完成的推导", "finish_reason": "length"}]:
            client = SolverTextClient(texts=[response])
            runtime = SolverTextReasoningRuntime(client, AgentConfig())
            self.assertIsNone(runtime._solve_step(self.state, [], self.task))
            self.assertEqual(runtime.last_solver_invalid["kind"], "text_error")

    def test_json_repair_is_inherited_unchanged(self):
        client = SolverTextClient()
        runtime = SolverTextReasoningRuntime(client, AgentConfig())
        step = text_to_reasoning_step("1+1=2", self.state, self.task)
        repaired = runtime._repair_draft(
            self.state, step, reasoning_step_to_solution_draft(step),
            CritiqueOutput(verdict="repair", repair_instruction="补充候选"), self.task, [],
        )
        self.assertIsInstance(repaired, ReasoningStep)
        self.assertIn("ReasoningStep JSON", client.calls[-1][-1]["content"])
        self.assertEqual(repaired.candidate_answers, ["2"])

    def test_replanner_still_expects_original_json_schema(self):
        class ReplanClient:
            def chat(self, messages, **kwargs):
                self.messages = messages
                return json.dumps({
                    "diagnosis": "当前论证不足", "avoid_routes": [], "reuse_results": [],
                    "new_tasks": [{"kind": "derive", "objective": "补充必要论证", "priority": 100}],
                    "first_step_instruction": "重新核查条件",
                })

        client = ReplanClient()
        runtime = SolverTextReasoningRuntime(client, AgentConfig())
        output = runtime._call_replanner(
            self.state, self.task, StepVerification(verdict="reject", reason="论证不足"), [],
        )
        self.assertEqual(client.messages[0]["content"], REPLANNER_SYSTEM_PROMPT)
        self.assertEqual(output.new_tasks[0]["objective"], "补充必要论证")


class SolverTextRuntimeTests(unittest.TestCase):
    def test_all_non_solver_runtime_methods_are_inherited(self):
        for name in [
            "run", "_run_efficient", "_formalize", "_classify_domain", "_strategy_preprocess",
            "_critique_draft", "_repair_draft", "_call_replanner", "_replan_blocked_task",
            "_verify_candidates_and_completeness", "_finalize", "_finish_efficient",
        ]:
            self.assertIs(getattr(SolverTextReasoningRuntime, name), getattr(ReasoningRuntime, name))

    def test_text_runs_original_json_stages_without_adapter_model_call(self):
        client = SolverTextClient()
        result = SolverTextReasoningRuntime(client, AgentConfig()).run("求 1+1。")
        self.assertEqual(result.final_response, r"\boxed{2}")
        self.assertEqual(len(client.calls), 10)
        self.assertEqual(client.solver_calls, 2)
        self.assertEqual(client.critique_calls, 2)
        self.assertEqual(result.state.model_call_count, 10)
        self.assertIn("critique_completed", [event["type"] for event in result.trace])
        self.assertNotIn("task_plan_committed", [event["type"] for event in result.trace])

    def test_original_strategy_controls_multiple_tasks(self):
        client = SolverTextClient(
            texts=["本任务结论：由整数加法可得 1+1=2。", "复核等式成立。\n整题候选答案：2"],
            strategy={
                "execution_mode": "macro", "problem_type": "numeric",
                "macro_tasks": [
                    {"kind": "derive", "objective": "建立等式", "priority": 100},
                    {"kind": "verify", "objective": "复核并形成候选", "priority": 90},
                ],
            },
        )
        result = SolverTextReasoningRuntime(client, AgentConfig()).run("求 1+1。")
        self.assertEqual(result.final_response, r"\boxed{2}")
        self.assertEqual(client.solver_calls, 3)
        calls = [messages for messages in client.calls if messages[0]["content"] == SOLVER_TEXT_SYSTEM_PROMPT]
        self.assertIn("本任务结论：由整数加法可得 1+1=2。", calls[1][-1]["content"])
        self.assertEqual(len([event for event in result.trace if event["type"] == "accepted_task_continuation"]), 1)

    def test_repair_path_keeps_original_json_roles(self):
        client = SolverTextClient(texts=["由整数加法可得 1+1=2。"], repair=True)
        result = SolverTextReasoningRuntime(client, AgentConfig()).run("求 1+1。")
        self.assertEqual(result.final_response, r"\boxed{2}")
        self.assertEqual(result.state.repair_count, 1)
        repairs = [messages for messages in client.calls if "定向修复器" in messages[0]["content"]]
        self.assertEqual(len(repairs), 1)
        self.assertIn("ReasoningStep JSON", repairs[0][-1]["content"])
        self.assertEqual(client.critique_calls, 3)

    def test_strategy_config_semantics_match_original_runtime(self):
        client = SolverTextClient()
        original_client = EfficientRuntimeFakeClient()
        config = AgentConfig(enable_strategy_preprocess=False)
        result = SolverTextReasoningRuntime(client, config).run("求 1+1。")
        ReasoningRuntime(original_client, config).run("求 1+1。")
        self.assertEqual(result.final_response, r"\boxed{2}")
        self.assertEqual(
            sum("解题策略设计器" in messages[0]["content"] for messages in client.calls),
            sum("解题策略设计器" in messages[0]["content"] for messages in original_client.calls),
        )
        self.assertEqual(client.solver_calls, 2)

    def test_legacy_step_scheduler_can_use_text_solver(self):
        client = SolverTextClient()
        runtime = SolverTextReasoningRuntime(client, AgentConfig(custom2_efficient_runtime=False))
        task = Task(id="T1", kind="derive", objective="推导当前等式", status="active")
        state = AgentState(problem="求 1+1。", tasks=[task])
        step = runtime._solve_step(state, [], task)
        self.assertIsNotNone(step)
        self.assertEqual(validate_reasoning_step_protocol(state, step, task), [])
        self.assertIn("当前任务", client.calls[0][0]["content"])

    def test_thinking_switch_changes_only_solver(self):
        for mode in ["false", "true", "default"]:
            client = SolverTextClient()
            runtime = SolverTextReasoningRuntime(client, AgentConfig(custom2_text_thinking_mode=mode))
            runtime.run("求 1+1。")
            for messages, options in zip(client.calls, client.call_kwargs):
                if messages[0]["content"] == SOLVER_TEXT_SYSTEM_PROMPT:
                    if mode == "default":
                        self.assertNotIn("thinking_mode", options)
                    else:
                        self.assertEqual(options["thinking_mode"], mode == "true")
                else:
                    self.assertFalse(options.get("thinking_mode", False))

    def test_agent_routes_text_to_new_runtime_and_json_to_original(self):
        with patch("reasoning_agent.custom2.text_runtime.TextReasoningRuntime.run", side_effect=AssertionError("obsolete runtime")):
            for protocol, client in [("text", SolverTextClient()), ("json", EfficientRuntimeFakeClient())]:
                result = Custom2Agent(client, AgentConfig(custom2_solver_protocol=protocol)).solve("求 1+1。", None)
                self.assertEqual(result["final_response"], r"\boxed{2}")
                json.dumps(result)

    def test_final_answer_formatting_does_not_change_json_finalizer(self):
        self.assertEqual(format_solver_text_response("2", "求 1+1。"), r"\boxed{2}")
        self.assertEqual(format_solver_text_response("(1) 2；(2) 3", "求两个结果。"), r"\boxed{(1) 2；(2) 3}")
        proof = "证明：由实数乘法定义，任意实数 x 满足 x+x=2x。"
        self.assertEqual(format_solver_text_response(proof, "证明任意实数 x 满足 x+x=2x。"), proof)
        self.assertEqual(format_solver_text_response("我们还需要推导。", "求结果。"), "未能提取最终答案。")

    def test_public_debug_trace_omits_raw_model_responses(self):
        client = SolverTextClient(texts=["完整推导的原始响应标记。\n整题候选答案：2"])
        result = Custom2Agent(client, AgentConfig(custom2_solver_protocol="text")).solve("求 1+1。", None)
        self.assertNotIn("完整推导的原始响应标记", json.dumps(result["debug_trace"], ensure_ascii=False))
        self.assertTrue(any(item["type"] == "solver_text_adapted" for item in result["debug_trace"]))


if __name__ == "__main__":
    unittest.main()

class StructuredTraceTests(unittest.TestCase):
    def test_trace_contains_expected_stage_summaries(self):
        result = SolverTextReasoningRuntime(
            SolverTextClient(), AgentConfig()
        ).run("求 1+1。")
        summaries = [
            item for item in result.trace
            if item.get("type") == "stage_summary"
        ]
        self.assertEqual(
            [item["step"] for item in summaries],
            ["classification", "strategy", "reasoning", "validation", "coordination", "timing"],
        )
        reasoning = next(item for item in summaries if item["step"] == "reasoning")
        self.assertGreaterEqual(reasoning["attempts"], 1)
        self.assertEqual(reasoning["answer"], result.final_response)
        self.assertIn("model_call_count", next(item for item in summaries if item["step"] == "timing"))
