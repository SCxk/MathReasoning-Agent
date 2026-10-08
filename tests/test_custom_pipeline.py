import json
import os
import unittest
from unittest.mock import patch

from reasoning_agent.custom.agent import CustomAgent
from reasoning_agent.custom.config import AgentConfig, env_flag
from reasoning_agent.custom.parsers.final_answer_parser import normalize_final_response
from reasoning_agent.custom.pipeline.config import PipelineConfig
from reasoning_agent.custom.pipeline.orchestrator import PipelineOrchestrator
from reasoning_agent.custom.pipeline.strategy_preprocessor import StrategyPreprocessor
from reasoning_agent.custom.prompts.step_verifier import build_step_verifier_messages
from reasoning_agent.custom.runner.context import RunnerContext
from reasoning_agent.custom.runner.loop import ToolUseRunner
from reasoning_agent.custom.state import Candidate
from reasoning_agent.custom.task_runner import TaskRunner
from reasoning_agent.custom.tools.executor import ToolExecutor
from reasoning_agent.custom.tools.registry import ToolSpec


class FakeChatClient:
    retry = 1

    def __init__(self, response) -> None:
        self.response = response
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class SequenceChatClient:
    retry = 1

    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def add_numbers(left: int, right: int) -> int:
    return left + right


class FakeToolUseRunner:
    def __init__(self, candidate: Candidate) -> None:
        self.candidate = candidate
        self.calls = []

    def run(self, ctx):
        self.calls.append(ctx)
        ctx.debug_trace.append(
            {
                "type": "fake_tool_loop",
                "content": {"problem_chars": len(ctx.problem)},
            }
        )
        return self.candidate


class CustomPipelineTest(unittest.TestCase):
    def test_normalize_final_response_boxes_short_answer(self) -> None:
        self.assertEqual(normalize_final_response("答案：2"), "\\boxed{2}")

    def test_normalize_final_response_preserves_existing_boxed_answer(self) -> None:
        self.assertEqual(
            normalize_final_response("最终答案为 \\boxed{2}。"),
            "最终答案为 \\boxed{2}。",
        )

    def test_normalize_final_response_appends_boxed_conclusion_for_explanation(self) -> None:
        self.assertEqual(
            normalize_final_response("由计算可知结果唯一。\n答案为 2。"),
            "由计算可知结果唯一。\n答案为 2。\n\n\\boxed{2}",
        )

    def test_custom_agent_omits_debug_trace_by_default(self) -> None:
        raw_response = json.dumps({"type": "final_answer", "answer": "7"})
        with patch.dict(os.environ, {}, clear=True):
            agent = CustomAgent(
                client=FakeChatClient(raw_response),
                config=AgentConfig(emit_debug_trace=False),
            )

            result = agent.solve("3 + 4", {"idx": 0})

        self.assertEqual(result["final_response"], "\\boxed{7}")
        self.assertIn("trace", result)
        self.assertNotIn("debug_trace", result)

    def test_custom_agent_emits_debug_trace_when_config_enabled(self) -> None:
        raw_response = json.dumps({"type": "final_answer", "answer": "7"})
        agent = CustomAgent(
            client=FakeChatClient(raw_response),
            config=AgentConfig(emit_debug_trace=True),
        )

        result = agent.solve("3 + 4", {"idx": 0})

        self.assertIn("debug_trace", result)
        self.assertIn("model_call", [entry["type"] for entry in result["debug_trace"]])

    def test_env_flag_reads_debug_trace_switch(self) -> None:
        with patch.dict(os.environ, {"REASONING_AGENT_DEBUG_TRACE": "true"}, clear=True):
            self.assertTrue(env_flag("REASONING_AGENT_DEBUG_TRACE"))
            self.assertTrue(AgentConfig().emit_debug_trace)

    def test_tool_loop_supports_native_tool_call_messages(self) -> None:
        tool_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "add_numbers",
                        "arguments": json.dumps({"left": 2, "right": 3}),
                    },
                }
            ],
        }
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "5",
                "reasoning_summary": "tool result",
            }
        )
        client = SequenceChatClient([tool_message, final_message])
        config = AgentConfig(enable_step_logic_verifier=False)
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(
                tools={
                    "add_numbers": ToolSpec(
                        name="add_numbers",
                        function=add_numbers,
                        required_arguments=("left", "right"),
                        description="Add two integers.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "left": {"type": "integer"},
                                "right": {"type": "integer"},
                            },
                            "required": ["left", "right"],
                        },
                    )
                },
                config=config,
            ),
            config=config,
        )
        ctx = RunnerContext.create(problem="2 + 3", metadata={"idx": 0})

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, "5")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(
            client.calls[0]["tools"],
            [
                {
                    "type": "function",
                    "function": {
                        "name": "add_numbers",
                        "description": "Add two integers.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "left": {"type": "integer"},
                                "right": {"type": "integer"},
                            },
                            "required": ["left", "right"],
                        },
                    },
                }
            ],
        )
        second_messages = client.calls[1]["messages"]
        self.assertEqual(second_messages[-2]["role"], "assistant")
        self.assertEqual(second_messages[-2]["tool_calls"], tool_message["tool_calls"])
        self.assertEqual(second_messages[-1]["role"], "tool")
        self.assertEqual(second_messages[-1]["tool_call_id"], "call-1")
        self.assertEqual(json.loads(second_messages[-1]["content"])["result"], 5)
        tool_debug = [
            entry for entry in ctx.debug_trace if entry["type"] == "tool_call"
        ][0]
        self.assertEqual(
            tool_debug,
            {
                "type": "tool_call",
                "tool": "add_numbers",
                "arguments": {"left": 2, "right": 3},
            },
        )
        tool_result_debug = [
            entry for entry in ctx.debug_trace if entry["type"] == "tool_call_result"
        ][0]
        self.assertEqual(tool_result_debug["tool"], "add_numbers")
        self.assertEqual(tool_result_debug["content"]["result"], 5)
        self.assertEqual(ctx.solve_state.tool_results[0]["tool"], "add_numbers")
        self.assertEqual(ctx.solve_state.tool_results[0]["observation"]["result"], 5)
        self.assertEqual(ctx.solve_state.final_answer, "5")

    def test_tool_loop_continues_after_solve_step_until_boxed_final_answer(self) -> None:
        solve_step = json.dumps(
            {
                "type": "solve_step",
                "step_summary": "设未知量并得到关键关系。",
                "known_facts": ["x 为正整数"],
                "derived_results": ["x=2"],
                "remaining_tasks": ["写出最终答案"],
                "is_ready_for_final": True,
            },
            ensure_ascii=False,
        )
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "由上一步可得最终答案为 \\boxed{2}。",
                "reasoning_summary": "整理中间结果得到最终答案。",
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient([solve_step, final_message])
        config = AgentConfig(enable_step_logic_verifier=False)
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(tools={}, config=config),
            config=config,
        )
        ctx = RunnerContext.create(problem="求 x", metadata={"idx": 0})

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, "由上一步可得最终答案为 \\boxed{2}。")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("\\boxed{}", client.calls[1]["messages"][-1]["content"])
        self.assertIn("solve_step", [entry["type"] for entry in ctx.debug_trace])
        self.assertIn("state", [entry["type"] for entry in ctx.debug_trace])
        self.assertEqual(ctx.solve_state.summary()["solve_step_count"], 1)
        self.assertEqual(ctx.solve_state.final_answer, "由上一步可得最终答案为 \\boxed{2}。")

    def test_step_logic_verifier_accepts_step_without_consuming_main_budget(self) -> None:
        solve_step = json.dumps(
            {
                "type": "solve_step",
                "step_summary": "将题目转化为等价形式。",
                "known_facts": ["x>0"],
                "derived_results": ["x^2>0"],
                "remaining_tasks": ["继续求解"],
                "is_ready_for_final": False,
            },
            ensure_ascii=False,
        )
        verifier_accept = json.dumps(
            {"verdict": "accept", "reason": "该步骤由正数性质直接推出。"},
            ensure_ascii=False,
        )
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "最终答案为 \\boxed{1}。",
                "reasoning_summary": "根据已接受步骤收敛。",
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient([solve_step, verifier_accept, final_message])
        config = AgentConfig(max_model_calls=2, max_step_verify_calls=1)
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(tools={}, config=config),
            config=config,
        )
        ctx = RunnerContext.create(problem="正数性质", metadata={"idx": 0})

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, "最终答案为 \\boxed{1}。")
        self.assertEqual(ctx.model_calls, 2)
        self.assertEqual(ctx.step_verify_calls, 1)
        self.assertIn("step_verify_call", [entry["type"] for entry in ctx.debug_trace])
        self.assertIn("step_verify_result", [entry["type"] for entry in ctx.debug_trace])

    def test_step_logic_verifier_rejects_bad_step_and_requests_retry(self) -> None:
        bad_step = json.dumps(
            {
                "type": "solve_step",
                "step_summary": "引用未证明结论。",
                "known_facts": ["题目条件"],
                "derived_results": ["known result: 答案是 7"],
                "remaining_tasks": ["写答案"],
                "is_ready_for_final": False,
            },
            ensure_ascii=False,
        )
        verifier_reject = json.dumps(
            {
                "verdict": "reject",
                "reason": "derived_results 包含未经证明的 known result。",
                "retry_instruction": "请只推出可直接验证的中间结论。",
            },
            ensure_ascii=False,
        )
        good_step = json.dumps(
            {
                "type": "solve_step",
                "step_summary": "从题目条件推出基础关系。",
                "known_facts": ["题目条件"],
                "derived_results": ["得到一个可验证的基础关系"],
                "remaining_tasks": ["继续证明"],
                "is_ready_for_final": False,
            },
            ensure_ascii=False,
        )
        verifier_accept = json.dumps(
            {"verdict": "accept", "reason": "没有使用未证明结论。"},
            ensure_ascii=False,
        )
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "最终答案为 \\boxed{2}。",
                "reasoning_summary": "使用已接受步骤完成。",
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient(
            [bad_step, verifier_reject, good_step, verifier_accept, final_message]
        )
        config = AgentConfig(max_model_calls=3, max_step_verify_calls=2, max_logic_retries=1)
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(tools={}, config=config),
            config=config,
        )
        ctx = RunnerContext.create(problem="拒绝坏步骤", metadata={"idx": 0})

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, "最终答案为 \\boxed{2}。")
        self.assertEqual(ctx.model_calls, 3)
        self.assertEqual(ctx.step_verify_calls, 2)
        self.assertEqual(ctx.current_logic_retries, 0)
        self.assertEqual(len(ctx.solve_state.error_memory), 1)
        self.assertIn("known result", ctx.solve_state.error_memory[0]["summary"])
        self.assertEqual(len(ctx.solve_state.solve_steps), 1)
        self.assertEqual(ctx.solve_state.solve_steps[0]["step_summary"], "从题目条件推出基础关系。")
        trace_types = [entry["type"] for entry in ctx.debug_trace]
        self.assertIn("step_rejected", trace_types)
        rejected_index = trace_types.index("step_rejected")
        self.assertEqual(ctx.debug_trace[rejected_index + 1]["type"], "user")
        self.assertIn("未通过逻辑校验", ctx.debug_trace[rejected_index + 1]["content"])

    def test_step_logic_verifier_does_not_bypass_rejected_step_when_retry_budget_exhausts(self) -> None:
        bad_step = json.dumps(
            {
                "type": "solve_step",
                "step_summary": "重复错误路线。",
                "known_facts": [],
                "derived_results": ["known result: 错误结论"],
                "remaining_tasks": ["继续"],
                "is_ready_for_final": False,
            },
            ensure_ascii=False,
        )
        verifier_reject = json.dumps(
            {
                "verdict": "reject",
                "reason": "重复使用 known result。",
                "retry_instruction": "换一种可验证的小步骤。",
            },
            ensure_ascii=False,
        )
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "只能基于已接受状态给出 \\boxed{0}。",
                "reasoning_summary": "坏步骤没有写入 state。",
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient([bad_step, verifier_reject, final_message])
        config = AgentConfig(max_model_calls=2, max_step_verify_calls=1, max_logic_retries=0)
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(tools={}, config=config),
            config=config,
        )
        ctx = RunnerContext.create(problem="拒绝后不放行", metadata={"idx": 0})

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, "只能基于已接受状态给出 \\boxed{0}。")
        self.assertEqual(ctx.solve_state.solve_steps, [])
        self.assertEqual(len(ctx.solve_state.error_memory), 1)
        trace_types = [entry["type"] for entry in ctx.debug_trace]
        self.assertIn("force_final_answer", trace_types)
        self.assertNotIn("step_verify_bypass", trace_types)

    def test_tool_loop_forces_final_answer_after_solve_step_budget(self) -> None:
        solve_step = json.dumps(
            {
                "type": "solve_step",
                "step_summary": "继续拆解。",
                "known_facts": [],
                "derived_results": ["x=2"],
                "remaining_tasks": ["最终作答"],
                "is_ready_for_final": False,
            },
            ensure_ascii=False,
        )
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "预算用完后收敛为 \\boxed{2}。",
                "reasoning_summary": "根据已有状态给出最终答案。",
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient([solve_step, solve_step, final_message])
        config = AgentConfig(
            max_model_calls=3,
            max_loop_steps=5,
            max_solve_steps=1,
            enable_step_logic_verifier=False,
        )
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(tools={}, config=config),
            config=config,
        )
        ctx = RunnerContext.create(
            problem="求 x",
            metadata={"idx": 0},
            max_solve_steps=config.max_solve_steps,
        )

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, "预算用完后收敛为 \\boxed{2}。")
        self.assertIn("最多只能输出 1 次 solve_step", ctx.debug_trace[0]["content"])
        self.assertEqual(ctx.solve_state.summary(config.max_solve_steps)["remaining_solve_steps"], 0)
        self.assertIn("force_final_answer", [entry["type"] for entry in ctx.debug_trace])
        self.assertIn("预算已经用完", client.calls[2]["messages"][-1]["content"])

    def test_tool_loop_repairs_invalid_json_response(self) -> None:
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "修正格式后得到 \\boxed{4}。",
                "reasoning_summary": "按 JSON schema 重写答案。",
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient(["答案是 4", final_message])
        config = AgentConfig(max_model_calls=2, max_loop_steps=4)
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(tools={}, config=config),
            config=config,
        )
        ctx = RunnerContext.create(problem="2+2", metadata={"idx": 0})

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, "修正格式后得到 \\boxed{4}。")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("不是合法的任务 JSON", client.calls[1]["messages"][-1]["content"])
        trace_types = [entry["type"] for entry in ctx.debug_trace]
        self.assertIn("invalid_json", trace_types)
        invalid_index = trace_types.index("invalid_json")
        self.assertEqual(ctx.debug_trace[invalid_index + 1]["type"], "user")
        self.assertIn("不是合法的任务 JSON", ctx.debug_trace[invalid_index + 1]["content"])
        self.assertEqual(ctx.solve_state.invalid_json_count, 1)

    def test_tool_loop_uses_last_json_object_when_response_contains_multiple(self) -> None:
        solve_step = json.dumps(
            {
                "type": "solve_step",
                "step_summary": "先分析。",
                "known_facts": ["已知条件"],
                "derived_results": ["中间结论"],
                "remaining_tasks": ["最终作答"],
                "is_ready_for_final": False,
            },
            ensure_ascii=False,
        )
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "最终答案为 \\boxed{1}。",
                "reasoning_summary": "最后一个 JSON 对象是最终答案。",
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient([solve_step + "\n\n" + final_message])
        config = AgentConfig(max_model_calls=1, max_loop_steps=2)
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(tools={}, config=config),
            config=config,
        )
        ctx = RunnerContext.create(problem="返回多个 JSON", metadata={"idx": 0})

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, "最终答案为 \\boxed{1}。")
        self.assertEqual(ctx.solve_state.invalid_json_count, 0)

    def test_pipeline_keeps_debug_trace_when_generation_exhausts_budget(self) -> None:
        solve_step = json.dumps(
            {
                "type": "solve_step",
                "step_summary": "只给步骤，不收敛。",
                "known_facts": [],
                "derived_results": [],
                "remaining_tasks": ["继续"],
                "is_ready_for_final": False,
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient([solve_step, solve_step])
        config = AgentConfig(
            max_model_calls=2,
            max_loop_steps=4,
            max_solve_steps=7,
            enable_step_logic_verifier=False,
        )
        agent = CustomAgent(
            client=client,
            config=config,
            pipeline_config=PipelineConfig(),
        )

        result = agent.solve("预算耗尽题", {"idx": 0})

        self.assertEqual(result["final_response"], "无法确定唯一答案")
        self.assertIn("debug_trace", result)
        self.assertIn("model_call", [entry["type"] for entry in result["debug_trace"]])
        self.assertIn("state", [entry["type"] for entry in result["debug_trace"]])

    def test_strategy_preprocessor_injects_guidance_before_generation(self) -> None:
        strategy = json.dumps(
            {
                "problem_type": "extremal_constant",
                "core_transforms": ["先做等价变形"],
                "phase_plan": ["规范化", "下界", "上界"],
                "lower_bound_requirements": ["验证所有选择"],
                "upper_bound_requirements": ["给出任意输入选择策略"],
                "risk_controls": ["不要先猜常数"],
                "do_not": ["不要把猜测写入 derived_results"],
                "first_step_instruction": "只做规范化。",
            },
            ensure_ascii=False,
        )
        final_message = json.dumps(
            {
                "type": "final_answer",
                "answer": "策略注入后得到 \\boxed{1}。",
                "reasoning_summary": "strategy used",
            },
            ensure_ascii=False,
        )
        client = SequenceChatClient([strategy, final_message])
        runner = TaskRunner(
            client=client,
            tools={},
            config=AgentConfig(enable_step_logic_verifier=False),
        )

        result = runner.run("求最小常数", {"idx": 0})

        self.assertEqual(result.final_response, "策略注入后得到 \\boxed{1}。")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["max_tokens"], 4096)
        self.assertIn("strategy_preprocess", [entry["step"] for entry in result.trace])
        self.assertIn(
            "strategy_preprocess_result",
            [entry["type"] for entry in result.debug_trace],
        )
        self.assertIn("正式解题前的策略约束", client.calls[1]["messages"][-1]["content"])

    def test_strategy_preprocessor_sanitizes_unproved_candidate_constants(self) -> None:
        raw_strategy = json.dumps(
            {
                "problem_type": "extremal_constant",
                "core_transforms": ["先做等价变形"],
                "phase_plan": ["验证 T = sqrt(5)-2 是最终常数", "规范化"],
                "lower_bound_requirements": ["known result: worst case is golden ratio"],
                "upper_bound_requirements": ["证明任意输入选择策略"],
                "risk_controls": ["检查变量位置"],
                "do_not": [],
                "first_step_instruction": "只做规范化。",
            },
            ensure_ascii=False,
        )

        guidance = StrategyPreprocessor._parse_guidance(raw_strategy)

        guidance_text = json.dumps(guidance, ensure_ascii=False)
        self.assertNotIn("sqrt(5)-2", guidance_text)
        self.assertNotIn("known result: worst case is golden ratio", guidance_text)
        self.assertIn("sanitization_warnings", guidance)
        self.assertIn("不得采用这些候选", guidance_text)
        self.assertIn("硬编码兜底", guidance_text)

    def test_step_verifier_prompt_requires_equivalence_audit(self) -> None:
        messages = build_step_verifier_messages(
            problem="证明等价变形",
            state_summary={"solve_step_count": 0},
            candidate_step={
                "step_summary": "等价变形",
                "known_facts": [],
                "derived_results": ["A 等价于 B"],
                "remaining_tasks": [],
                "is_ready_for_final": False,
            },
        )

        prompt = messages[-1]["content"]
        self.assertIn("等价变形审计要求", prompt)
        self.assertIn("逐项代入复算", prompt)
        self.assertIn("分母是否正确、变量位置是否正确", prompt)
        self.assertIn("两个不同的等价式", prompt)

    def test_tool_loop_parses_full_response_even_when_stored_copy_is_truncated(self) -> None:
        answer = "x" * 80
        raw_response = json.dumps(
            {
                "type": "final_answer",
                "answer": answer,
                "reasoning_summary": "long answer",
            }
        )
        client = FakeChatClient(raw_response)
        config = AgentConfig(max_trace_chars=20)
        runner = ToolUseRunner(
            client=client,
            tool_executor=ToolExecutor(tools={}, config=config),
            config=config,
        )
        ctx = RunnerContext.create(problem="return a long answer", metadata={"idx": 0})

        candidate = runner.run(ctx)

        self.assertEqual(candidate.answer, answer)
        self.assertEqual(ctx.raw_responses, [raw_response[:20]])
        self.assertEqual(ctx.debug_trace[0]["type"], "user")
        self.assertIn("return a long answer", ctx.debug_trace[0]["content"])
        self.assertEqual(ctx.debug_trace[1]["type"], "model_call")
        self.assertEqual(ctx.debug_trace[1]["content"], raw_response[:20])

    def test_task_runner_returns_answer_through_pipeline_without_raw_trace(self) -> None:
        raw_response = json.dumps(
            {
                "type": "final_answer",
                "answer": "最终答案：42",
                "reasoning_summary": "compute directly",
            },
            ensure_ascii=False,
        )
        client = FakeChatClient(raw_response)
        runner = TaskRunner(
            client=client,
            tools={},
            config=AgentConfig(enable_strategy_preprocess=False, thinking_mode=True),
        )
        problem = "PRIVATE PROBLEM TEXT: 6 * 7"

        result = runner.run(problem, {"idx": 1})

        self.assertEqual(result.final_response, "\\boxed{42}")
        self.assertEqual(client.calls[0]["max_tokens"], runner.config.tool_loop_max_tokens)
        self.assertIs(client.calls[0]["thinking_mode"], True)
        self.assertIsNone(client.calls[0]["tools"])
        trace_text = json.dumps(result.trace, ensure_ascii=False)
        self.assertNotIn(problem, trace_text)
        self.assertNotIn(raw_response, trace_text)
        self.assertEqual(result.trace[0]["step"], "generate_candidates")
        self.assertEqual(result.trace[-1]["step"], "finalize")
        self.assertEqual(
            [entry["step"] for entry in result.trace],
            ["generate_candidates", "select", "finalize"],
        )
        self.assertNotIn("model_call", [entry["step"] for entry in result.trace])
        self.assertIn("model_call", [entry["type"] for entry in result.debug_trace])
        self.assertIn("user", [entry["type"] for entry in result.debug_trace])

    def test_orchestrator_reuses_tool_use_runner_as_generator_node(self) -> None:
        fake_runner = FakeToolUseRunner(
            Candidate(answer="答案：x = 2", source="fake_loop")
        )
        orchestrator = PipelineOrchestrator(
            client=object(),
            tool_executor=object(),
            agent_config=AgentConfig(),
            pipeline_config=PipelineConfig(max_candidates=1),
            tool_use_runner=fake_runner,
        )

        result = orchestrator.run("求 x 的值", {"idx": 2})

        self.assertEqual(result.final_response, "\\boxed{x = 2}")
        self.assertEqual(len(fake_runner.calls), 1)
        self.assertIn(
            "generate_candidates",
            [entry["step"] for entry in result.trace],
        )
        self.assertIn(
            "fake_tool_loop",
            [entry["type"] for entry in result.debug_trace],
        )

    def test_repair_node_is_traced_for_failed_proof_candidate(self) -> None:
        fake_runner = FakeToolUseRunner(Candidate(answer="显然成立", source="fake_loop"))
        orchestrator = PipelineOrchestrator(
            client=object(),
            tool_executor=object(),
            agent_config=AgentConfig(),
            pipeline_config=PipelineConfig(
                enable_classify=True,
                enable_verify=True,
                enable_repair=True,
                max_repair_attempts=1,
            ),
            tool_use_runner=fake_runner,
        )

        result = orchestrator.run("证明：若 n 为偶数，则 n^2 为偶数。", {"idx": 3})

        steps = [entry["step"] for entry in result.trace]
        self.assertIn("verify", steps)
        self.assertIn("repair", steps)
        self.assertTrue(result.final_response.strip())


if __name__ == "__main__":
    unittest.main()
