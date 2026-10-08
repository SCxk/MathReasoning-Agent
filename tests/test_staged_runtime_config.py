import io
import os
import time
import unittest
import warnings
from contextlib import redirect_stderr
from unittest.mock import Mock, patch

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom2.agent import Custom2Agent
from reasoning_agent.custom2.models import AgentState
from reasoning_agent.custom2.staged_models import (
    StagedAudit,
    StagedModelFidelity,
    StagedStrategy,
)
from reasoning_agent.custom2.staged_prompts import STAGED_DIRECT_EMERGENCY_PROMPT
from reasoning_agent.custom2.staged_runtime import (
    StagedReasoningRuntime,
    effective_staged_budget_seconds,
)
from reasoning_agent.custom2.text_models import ProblemProfile
from reasoning_agent.strategy_retrieval import build_structure_messages


class CaptureClient:
    def __init__(self, responses=None) -> None:
        self.calls: list[dict] = []
        self.responses = list(responses or ["{}"])

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class StagedRuntimeConfigTests(unittest.TestCase):
    def test_platform_deadline_headroom_reduces_effective_staged_budget(self):
        self.assertEqual(effective_staged_budget_seconds(AgentConfig()), (1200.0, 0.0, 1200.0))
        self.assertEqual(
            effective_staged_budget_seconds(AgentConfig(
                custom2_total_budget_seconds=30,
                custom2_platform_deadline_headroom_seconds=60,
            )),
            (30.0, 30.0, 0.0),
        )

    def test_staged_strategy_defaults_to_no_thinking_and_has_own_token_budget(self):
        config = AgentConfig()
        self.assertEqual(config.custom2_max_repairs, 3)
        self.assertFalse(config.staged_classifier_thinking_mode)
        self.assertFalse(config.staged_strategy_thinking_mode)
        self.assertFalse(config.staged_strategy_model_enabled)
        self.assertEqual(config.staged_strategy_max_tokens, 8192)
        self.assertEqual(config.staged_strategy_timeout_seconds, 360.0)
        self.assertEqual(config.staged_strategy_temperature, 0.3)
        self.assertEqual(config.staged_best_candidate_return_seconds, 25.0)
        self.assertEqual(config.staged_new_work_cutoff_seconds, 300.0)
        self.assertEqual(config.staged_strategy_skill_material_max_chars, 8000)
        self.assertFalse(config.staged_solver_compact_by_default)
        self.assertTrue(config.staged_compact_reasoning_only)
        self.assertEqual(config.staged_classifier_timeout_seconds, 180.0)
        self.assertFalse(config.staged_solver_thinking_mode)
        self.assertTrue(config.staged_solver_repair_thinking_mode)
        self.assertEqual(config.staged_solver_max_tokens, 24576)
        self.assertEqual(config.staged_solver_timeout_seconds, 660.0)
        self.assertTrue(config.staged_solver_compressed_thinking_mode)
        self.assertFalse(config.staged_strategy_retrieval_thinking_mode)
        self.assertFalse(config.staged_targeted_audit_thinking_mode)
        self.assertFalse(config.staged_model_fidelity_thinking_mode)
        self.assertFalse(config.staged_emergency_thinking_mode)
        self.assertEqual(config.staged_primary_solver_temperature, 0.3)
        self.assertEqual(config.staged_repair_solver_temperature, 0.8)
        self.assertEqual(config.staged_solver_compressed_max_tokens, 131072)
        self.assertEqual(config.staged_primary_compact_timeout_seconds, 660.0)
        self.assertEqual(config.staged_solver_compressed_call_estimate_seconds, 660.0)
        self.assertEqual(config.staged_targeted_audit_timeout_seconds, 360.0)
        self.assertEqual(config.staged_audit_retry_max_tokens, 4096)
        self.assertEqual(config.staged_audit_retry_timeout_seconds, 60.0)
        self.assertTrue(config.staged_model_fidelity_enabled)
        self.assertEqual(config.staged_model_fidelity_thinking_max_tokens, 65536)
        self.assertEqual(config.staged_model_fidelity_timeout_seconds, 200.0)
        self.assertEqual(config.staged_constraint_ledger_max_chars, 12000)
        self.assertEqual(config.staged_emergency_timeout_seconds, 300.0)
        self.assertEqual(config.staged_final_arbitrator_timeout_seconds, 600.0)
        self.assertTrue(config.staged_strategy_retrieval_enabled)
        self.assertEqual(config.staged_strategy_retrieval_top_k, 2)

    def test_audit_models_coerce_singleton_list_fields(self):
        audit = StagedAudit.model_validate({
            "verdict": "fail",
            "required_changes": "recompute the state transition",
            "forbidden_reuse": "scalar additive recurrence",
            "unmet_obligations": "verify a multi-component state",
            "additional_errors": {
                "error_type": "calculation",
                "required_changes": "check base state",
                "forbidden_reuse": "unchecked table",
            },
        })
        fidelity = StagedModelFidelity.model_validate({
            "verdict": "fail",
            "required_changes": "rebuild the model",
        })

        self.assertEqual(audit.required_changes, ["recompute the state transition"])
        self.assertEqual(audit.forbidden_reuse, ["scalar additive recurrence"])
        self.assertEqual(audit.unmet_obligations, ["verify a multi-component state"])
        self.assertEqual(audit.additional_errors[0].required_changes, ["check base state"])
        self.assertEqual(fidelity.required_changes, ["rebuild the model"])

    def test_runtime_normalizes_audit_shape_and_records_it(self):
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())

        payload = runtime._normalize_audit_payload({
            "verdict": "fail",
            "required_changes": "recompute the state transition",
            "additional_errors": [
                {
                    "error_type": "calculation",
                    "forbidden_reuse": "unchecked recurrence",
                },
                "not an audit issue object",
            ],
        }, call_type="targeted_audit")

        self.assertEqual(payload["verdict"], "fail")
        self.assertEqual(payload["required_changes"], ["recompute the state transition"])
        self.assertEqual(payload["additional_errors"], [{
            "error_type": "calculation",
            "forbidden_reuse": ["unchecked recurrence"],
        }])
        event = runtime.trace[-1]
        self.assertEqual(event["type"], "audit_payload_normalized")
        self.assertEqual(event["data"]["call_type"], "targeted_audit")
        self.assertIn("required_changes:string_to_list", event["data"]["adjustments"])

    def test_audit_retries_once_with_prior_schema_rejection(self):
        client = CaptureClient([
            "not valid json",
            '{"verdict":"pass","additional_errors":[]}',
        ])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="审查重试", efficient_runtime=True, started_at=now,
            deadline_at=now + 300, finalize_reserve_seconds=0,
        )

        audit = runtime._audit(
            "审查重试", ProblemProfile(), StagedStrategy(), "草稿", {"ok": True, "summary": []},
        )

        self.assertEqual(audit.verdict, "pass")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[1]["thinking_mode"], False)
        self.assertEqual(client.calls[1]["max_tokens"], 4096)
        self.assertIn("previous_audit_output", client.calls[1]["messages"][1]["content"])
        self.assertIn(
            "audit_parse_retry_started",
            [item["type"] for item in runtime.trace],
        )

    def test_saved_candidate_preserves_primary_until_arbitration_replaces_it(self):
        primary = "## 最终答案\n\\boxed{3}"
        repair = "## 最终答案\n\\boxed{7}"
        arbitrated = "## 最终答案\n\\boxed{11}"
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())

        self.assertTrue(runtime._save_candidate(primary, source="primary_solver"))
        self.assertTrue(runtime._save_candidate(repair, source="repair_1"))
        self.assertEqual(runtime._saved_candidate_answer(), "\\boxed{3}")
        self.assertEqual(runtime._best_candidate_source, "primary_solver")

        self.assertTrue(
            runtime._save_candidate(arbitrated, source="final_arbitration", replace=True)
        )
        self.assertEqual(runtime._saved_candidate_answer(), "\\boxed{11}")
        self.assertEqual(runtime._best_candidate_source, "final_arbitration")

    def test_proof_candidate_returns_full_proof_instead_of_only_final_answer(self):
        proof = (
            "## 问题分析\n待证命题。\n"
            "## 详细解题步骤\n步骤 1｜目标：证明\n由定义和引理推出结论。\n"
            "```check\n{\"ok\": true}\n```\n"
            "## 最终答案\n命题成立。\n## 关键验证点\n边界情形满足。"
        )
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        runtime._answer_mode = "proof"

        self.assertTrue(runtime._save_candidate(proof, source="primary_solver"))
        rendered = runtime._saved_candidate_answer()

        self.assertIn("## 详细解题步骤", rendered)
        self.assertIn("由定义和引理推出结论", rendered)
        self.assertIn("## 最终答案", rendered)
        self.assertNotIn("```check", rendered)
        self.assertNotEqual(rendered, r"\\boxed{命题成立。}")

    def test_passed_repair_replaces_saved_primary_answer(self):
        primary = (
            "## 问题分析\n初始路线。\n## 详细解题步骤\n步骤 1。\n"
            "## 最终答案\n\\boxed{3}\n## 关键验证点\n代回。"
        )
        repaired = (
            "## 问题分析\n修复路线。\n## 详细解题步骤\n步骤 1。\n"
            "## 最终答案\n\\boxed{7}\n## 关键验证点\n复算。"
        )
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        runtime._profile = Mock(return_value=ProblemProfile(answer_mode="computation"))
        runtime._retrieve_strategy_examples = Mock()
        runtime._strategy = Mock(return_value=StagedStrategy(risk_level="high"))
        runtime._solve = Mock(side_effect=[primary, repaired])
        runtime._local_checks = Mock(return_value={"ok": False, "summary": []})
        runtime._model_fidelity = Mock(return_value=StagedModelFidelity(verdict="pass"))
        runtime._audit = Mock(side_effect=[
            StagedAudit(verdict="fail", first_fatal_error="初稿错误"),
            StagedAudit(verdict="pass"),
        ])
        runtime._convergence_due = lambda: False
        runtime._best_candidate_return_due = lambda: False

        with patch(
            "reasoning_agent.custom2.staged_runtime.retrieve_skill_material",
            return_value=([], ""),
        ), patch(
            "reasoning_agent.custom2.staged_runtime.select_strategy_skills",
            return_value=[],
        ):
            result = runtime.run("求值")

        self.assertEqual(result["final_response"], "\\boxed{7}")
        self.assertEqual(runtime._best_candidate_source, "repair_1")

    def test_local_checks_reject_false_numeric_equality(self):
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        draft = (
            "## 问题分析\n计算。\n## 详细解题步骤\n步骤 1。\n"
            "## 最终答案\n\\boxed{3}\n## 关键验证点\n$2+3=6$"
        )

        result = runtime._local_checks(
            "求值", ProblemProfile(answer_mode="computation"), StagedStrategy(), draft,
        )

        self.assertFalse(result["ok"])
        self.assertIn("2+3==6 => False", result["summary"])

    def test_deadline_candidate_selection_uses_answer_plurality_then_first(self):
        primary = "## 最终答案\n\\boxed{3}"
        repeated = "## 最终答案\n\\boxed{7}"
        other = "## 最终答案\n\\boxed{11}"
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())

        selected = runtime._select_deadline_candidate([
            {"draft": primary}, {"draft": repeated},
            {"draft": repeated}, {"draft": other},
        ], primary)
        self.assertEqual(selected, repeated)
        self.assertEqual(runtime._saved_candidate_answer(), "\\boxed{7}")

        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        selected = runtime._select_deadline_candidate([
            {"draft": primary}, {"draft": repeated}, {"draft": other},
        ], primary)
        self.assertEqual(selected, primary)
        self.assertEqual(runtime._saved_candidate_answer(), "\\boxed{3}")

    def test_unhandled_runtime_exception_recovers_saved_candidate(self):
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        runtime._save_candidate("## 最终答案\n\\boxed{13}", source="primary_solver")

        result = runtime.recover_unhandled_exception(RuntimeError("skill file unavailable"))

        self.assertEqual(result["final_response"], "\\boxed{13}")
        self.assertEqual(result["solve_status"], "success")
        event = next(
            item for item in result["trace"]
            if item["type"] == "staged_runtime_recovered_exception"
        )
        self.assertEqual(event["data"]["error_type"], "RuntimeError")

    def test_custom2_agent_staged_exception_returns_nonempty_result(self):
        recovered = {
            "final_response": "\\boxed{13}",
            "solve_status": "success",
            "trace": [],
            "debug_trace": [],
        }
        with patch("reasoning_agent.custom2.staged_runtime.StagedReasoningRuntime") as runtime_cls:
            runtime = runtime_cls.return_value
            runtime.run.side_effect = RuntimeError("unexpected local failure")
            runtime.recover_unhandled_exception.return_value = recovered

            result = Custom2Agent(
                CaptureClient(), AgentConfig(custom2_solver_protocol="staged")
            ).solve("求值", None)

        self.assertEqual(result, recovered)
        runtime.recover_unhandled_exception.assert_called_once()

    def test_convergence_stops_repairs_but_allows_final_arbitration(self):
        primary = (
            "## 问题分析\n初始路线。\n## 详细解题步骤\n步骤 1。\n"
            "## 最终答案\n\\boxed{3}\n## 关键验证点\n代回。"
        )
        arbitrated = (
            "## 问题分析\n比较候选。\n## 详细解题步骤\n步骤 1。\n"
            "## 最终答案\n\\boxed{7}\n## 关键验证点\n复算。"
        )
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        runtime._profile = Mock(return_value=ProblemProfile())
        runtime._retrieve_strategy_examples = Mock()
        runtime._strategy = Mock(return_value=StagedStrategy(risk_level="high"))
        runtime._solve = Mock(return_value=primary)
        runtime._local_checks = Mock(return_value={"ok": False, "summary": []})
        runtime._model_fidelity = Mock(return_value=StagedModelFidelity(
            verdict="fail", first_fatal_error="模型不保真",
        ))
        runtime._final_arbitrate = Mock(return_value=arbitrated)
        convergence = iter((False, False, True))
        runtime._convergence_due = lambda: next(convergence)
        runtime._best_candidate_return_due = lambda: False

        with patch(
            "reasoning_agent.custom2.staged_runtime.retrieve_skill_material",
            return_value=([], ""),
        ), patch(
            "reasoning_agent.custom2.staged_runtime.select_strategy_skills",
            return_value=[],
        ):
            result = runtime.run("求值")

        self.assertEqual(result["final_response"], "\\boxed{7}")
        self.assertEqual(runtime._solve.call_count, 1)
        runtime._final_arbitrate.assert_called_once()
        self.assertIn(
            "stop_repairs_allow_final_arbitration",
            [item["data"].get("action") for item in runtime.trace],
        )

    def test_staged_strategy_retrieval_uses_exact_query_and_layered_cards(self):
        structure = (
            "Domain: algebra\nGoal: compute a value\nObjects: integers\n"
            "Constraints: positive input\nStructure:\n- finite calculation"
        )
        compact = (
            "简析。\n## 详细解题步骤\n步骤 1：计算。\n"
            "## 最终答案\n\\boxed{2}\n## 关键验证点\n代回成立。"
        )
        client = CaptureClient([
            '{"domain":"algebra","answer_mode":"computation","obligations":[]}',
            structure,
            '{"problem_type":"calculation","risk_level":"low","skill_domains":[],"skill_sections":[]}',
            compact,
        ])

        class Retriever:
            def retrieve_for_structure(self, problem, retrieval_text, *, top_k):
                self.problem = problem
                self.retrieval_text = retrieval_text
                self.top_k = top_k
                return {"retrieval_text": retrieval_text, "results": [{
                    "id": 7, "name": "Test strategy", "tags": ["algebra"],
                    "description": "Use a checked transformation.",
                    "applicability": ["Finite algebra problem"],
                    "steps": [{"step": "Transform", "detail": "Preserve constraints"}],
                    "example": {"problem": "EXAMPLE_PROBLEM", "solution": "EXAMPLE_SOLUTION"},
                    "score": 0.8, "raw_score": 0.7, "structure_score": 0.9,
                }]}

        retriever = Retriever()
        with patch("reasoning_agent.custom2.staged_runtime.get_shared_strategy_retriever", return_value=retriever):
            result = StagedReasoningRuntime(
                client, AgentConfig(
                    staged_strategy_retrieval_top_k=3,
                    staged_strategy_model_enabled=True,
                    staged_strategy_retrieval_mode="legacy_embedding",
                )
            ).run("求 1+1。")

        self.assertEqual(result["final_response"], r"\boxed{2}")
        self.assertEqual(retriever.top_k, 3)
        self.assertEqual(client.calls[1]["messages"], build_structure_messages("求 1+1。"))
        strategy_payload = client.calls[2]["messages"][1]["content"]
        self.assertIn("Test strategy", strategy_payload)
        self.assertIn("strategy_skill_material", strategy_payload)
        self.assertNotIn("（无匹配技能节选）", strategy_payload)
        self.assertIn("constraint_ledger", strategy_payload)
        self.assertIn("【原题约束原文（不得改写）】", strategy_payload)
        self.assertIn("同一具体主题的", client.calls[2]["messages"][0]["content"])
        self.assertNotIn("EXAMPLE_PROBLEM", strategy_payload)
        self.assertNotIn("EXAMPLE_SOLUTION", strategy_payload)
        solver_prompt = client.calls[3]["messages"][1]["content"]
        self.assertIn("EXAMPLE_PROBLEM", solver_prompt)
        self.assertIn("EXAMPLE_SOLUTION", solver_prompt)
        self.assertIn("高价值策略案例", solver_prompt)
        self.assertIn("应多参考并优先把其中的表示、步骤和验证方法映射到当前题", solver_prompt)
        self.assertIn("【题面约束台账】", solver_prompt)
        self.assertIn("【原题约束原文（不得改写）】\n求 1+1。", solver_prompt)
        self.assertIn("【检索结构摘要（待题面核验）】", solver_prompt)
        self.assertIn("Constraints: positive input", solver_prompt)
        self.assertIn("Directionality: Unspecified", solver_prompt)
        self.assertNotIn("不可信方法参考", solver_prompt)
        event = next(item for item in result["trace"] if item["type"] == "staged_strategy_retrieval_completed")
        self.assertEqual(event["data"]["results"][0]["score"], 0.8)
        self.assertIn("EXAMPLE_SOLUTION", event["data"]["solver_cards"])
        planning_event = next(
            item for item in result["trace"]
            if item["type"] == "strategy_skill_material_injected"
        )
        self.assertEqual(planning_event["data"]["target"], "strategy_planner")
        self.assertTrue(planning_event["data"]["skills"])

    def test_staged_strategy_retrieval_budget_and_resource_failures_degrade(self):
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig(staged_strategy_retrieval_pool_seconds=0))
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求值", efficient_runtime=True, started_at=now,
            deadline_at=now + 100, finalize_reserve_seconds=10,
        )
        runtime._retrieve_strategy_examples("求值")
        self.assertEqual(runtime.trace[-1]["type"], "staged_strategy_retrieval_degraded")
        self.assertEqual(runtime.trace[-1]["data"]["reason"], "budget_insufficient")

        runtime = StagedReasoningRuntime(CaptureClient(["invalid"]), AgentConfig())
        runtime.state = AgentState(
            problem="求值", efficient_runtime=True, started_at=now,
            deadline_at=now + 100, finalize_reserve_seconds=10,
        )
        runtime._retrieve_strategy_examples("求值")
        self.assertEqual(runtime.trace[-1]["type"], "staged_strategy_retrieval_degraded")
        self.assertEqual(runtime.trace[-1]["data"]["error_type"], "ValueError")

    def test_staged_skips_model_strategy_when_disabled(self):
        runtime = StagedReasoningRuntime(
            CaptureClient(), AgentConfig(staged_strategy_model_enabled=False)
        )
        strategy = runtime._strategy("求值", ProblemProfile(answer_mode="computation"))
        self.assertEqual(strategy.problem_type, "computation")
        self.assertEqual(runtime.trace[-1]["type"], "strategy_skipped")

    def test_strategy_keeps_sections_when_an_advisory_field_exceeds_old_schema_limit(self):
        response = (
            '{"risk_level":"high","main_method":"' + "x" * 2500 + '",'
            '"skill_domains":["combinatorics"],'
            '"skill_sections":["竞赛拓展：Hamilton 路径块分解"],'
            '"key_theorems":[{"name":"状态转移",'
            '"applicability":"用于窄网格"}]}'
        )
        runtime = StagedReasoningRuntime(
            CaptureClient([response]), AgentConfig(staged_strategy_model_enabled=True)
        )
        now = time.monotonic()
        runtime.state = AgentState(
            problem="Hamilton 路径", efficient_runtime=True, started_at=now,
            deadline_at=now + 300, finalize_reserve_seconds=0,
        )

        strategy = runtime._strategy("Hamilton 路径", ProblemProfile(answer_mode="computation"))

        self.assertEqual(strategy.skill_domains, ["combinatorics"])
        self.assertEqual(strategy.skill_sections, ["竞赛拓展：Hamilton 路径块分解"])
        self.assertEqual(strategy.key_theorems, ["状态转移：用于窄网格"])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            strategy.model_dump()
        self.assertFalse(caught)
        self.assertIn("strategy_unvalidated_payload_accepted", [item["type"] for item in runtime.trace])

    def test_staged_audit_does_not_receive_strategy_examples(self):
        client = CaptureClient([
            '{"verdict":"pass","first_fatal_error":"","invalid_claim":"",'
            '"evidence":"checked","counterexample_or_evidence":"",'
            '"unmet_obligations":[],"required_changes":[],"forbidden_reuse":[],'
            '"replacement_route":"","repair_instruction":""}'
        ])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求值", efficient_runtime=True, started_at=now,
            deadline_at=now + 100, finalize_reserve_seconds=0,
        )
        runtime._solver_strategy_cards = "EXAMPLE_PROBLEM\nEXAMPLE_SOLUTION"
        runtime._planner_strategy_cards = "RETRIEVAL_METHOD_SUMMARY"
        runtime._audit_skill_summary = "RELATED_SKILL_SUMMARY"
        runtime._strategy_retrieval_text = "RETRIEVAL_SUMMARY"
        runtime._audit("求值", ProblemProfile(), StagedStrategy(), "草稿", {"ok": True, "summary": []})
        audit_payload = client.calls[0]["messages"][1]["content"]
        self.assertIn("RETRIEVAL_METHOD_SUMMARY", audit_payload)
        self.assertIn("RELATED_SKILL_SUMMARY", audit_payload)
        self.assertNotIn("EXAMPLE_PROBLEM", audit_payload)
        self.assertNotIn("EXAMPLE_SOLUTION", audit_payload)
        self.assertNotIn("RETRIEVAL_SUMMARY", audit_payload)

    def test_audit_preserves_independent_errors_and_prevention_rules(self):
        response = (
            '{"verdict":"fail","error_type":"model",'
            '"first_fatal_error":"首个模型错误",'
            '"invalid_claim":"把有向边当作无向边",'
            '"evidence":"题面：原题给出有序转移",'
            '"required_changes":["按有向边重建模型"],'
            '"additional_errors":[{'
            '"error_type":"missing_proof",'
            '"invalid_claim":"每列连续访问",'
            '"evidence":"没有从题面推出该断言",'
            '"affected_reasoning":"唯一性计数失效",'
            '"required_changes":["建立 frontier 状态"],'
            '"forbidden_reuse":["列连续块假设"],'
            '"prevention_rule":"不得因相似蛇形题而假设列连续"'
            '}]}'
        )
        runtime = StagedReasoningRuntime(CaptureClient([response]), AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="有向计数", efficient_runtime=True, started_at=now,
            deadline_at=now + 300, finalize_reserve_seconds=0,
        )

        audit = runtime._audit(
            "有向计数", ProblemProfile(), StagedStrategy(),
            "把有向边当作无向边；每列连续访问", {"ok": True, "summary": []},
        )
        runtime._remember_audit_findings(audit)
        trace_data = runtime._audit_trace_data(audit)

        self.assertEqual(audit.additional_errors[0].error_type, "missing_proof")
        self.assertEqual(trace_data["additional_errors"][0]["invalid_claim"], "每列连续访问")
        self.assertIn("列连续块假设", runtime._persistent_avoidance_context())
        self.assertIn("不得因相似蛇形题", runtime._persistent_avoidance_context())

    def test_audit_rejects_unquoted_or_unsupported_failure(self):
        response = (
            '{"verdict":"fail","first_fatal_error":"分类错误",'
            '"invalid_claim":"exotic 整数恰为所有平方数",'
            '"evidence":"反例：另一个未经推导的分类",'
            '"required_changes":["改用另一分类"]}'
        )
        runtime = StagedReasoningRuntime(CaptureClient([response]), AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="函数分类", efficient_runtime=True, started_at=now,
            deadline_at=now + 300, finalize_reserve_seconds=0,
        )

        audit = runtime._audit(
            "函数分类", ProblemProfile(), StagedStrategy(),
            "草稿结论：exotic 整数恰为奇完全平方数。", {"ok": True, "summary": []},
        )

        self.assertEqual(audit.verdict, "uncertain")
        self.assertIn("完整证据链", audit.evidence)

    def test_repair_carries_prior_audit_prevention_rules(self):
        compact = (
            "## 问题分析\n重新建模。\n## 详细解题步骤\n步骤 1：状态递推。\n"
            "## 最终答案\n\\boxed{2}\n## 关键验证点\n边界成立。"
        )
        runtime = StagedReasoningRuntime(CaptureClient([compact]), AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求值", efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )
        prior = StagedAudit(
            verdict="fail", first_fatal_error="旧模型错误",
            additional_errors=[{
                "error_type": "missing_proof",
                "forbidden_reuse": ["未经证明的列连续假设"],
                "prevention_rule": "不得套用相似题的蛇形唯一性",
            }],
        )
        runtime._remember_audit_findings(prior)

        runtime._solve(
            "求值", ProblemProfile(), StagedStrategy(), "技能",
            attempt=2, previous="旧答案", audit=prior,
        )

        prompt = runtime.client.calls[0]["messages"][1]["content"]
        self.assertIn("本题跨轮防类比清单", prompt)
        self.assertIn("未经证明的列连续假设", prompt)
        self.assertIn("不得套用相似题的蛇形唯一性", prompt)

    def test_periodic_directed_hamiltonian_gets_special_requirements_in_all_solver_paths(self):
        problem = (
            "Count Hamiltonian paths on a cyclic 3 by n grid. Vertices are (x,y), "
            "with 0 <= x <= n-1; horizontal transitions satisfy "
            "x_i-x_{i+1} is -1 or n-1, and the path starts and ends on fixed rows."
        )
        profile = ProblemProfile(domain="combinatorics", answer_mode="computation")
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        runtime._constraint_ledger = runtime._build_constraint_ledger(problem)
        regular = runtime._render_solver_prompt(
            problem, profile, StagedStrategy(), "", repair_context="", recovery_context="",
        )
        self.assertIn("【专项建模与完整性检查】", regular)
        self.assertIn("frontier", regular)
        self.assertIn("不能反向走", regular)
        self.assertIn("每列连续块访问", regular)
        self.assertIn("完整周期回到该列", regular)

        now = time.monotonic()
        client = CaptureClient(["## 详细解题步骤\n状态递推。\n## 最终答案\n\\boxed{1}\n## 关键验证点\n小规模核验。"])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        runtime.state = AgentState(
            problem=problem, efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )
        runtime._constraint_ledger = runtime._build_constraint_ledger(problem)
        runtime._compressed_solve(
            problem, profile, StagedStrategy(), "", "system",
            repair_context="", attempt=1, failure_reason="compact_reasoning_only",
        )
        compact = client.calls[0]["messages"][1]["content"]
        self.assertIn("【专项建模与完整性检查】", compact)
        self.assertIn("frontier", compact)
        self.assertIn("完整周期回到该列", compact)

    def test_special_requirements_reuse_all_problem_structure_checks(self):
        problem = (
            "Let f: Q -> F_2. Find all possible values for f(a)+f(b). Determine the minimum "
            "number strictly between 0 and 1; is it possible, and if so how many? "
            "What is the 7th smallest value?"
        )
        requirements = StagedReasoningRuntime._build_special_requirements(
            problem, ProblemProfile(answer_mode="computation")
        )
        for label in (
            "值域聚合警告", "全部解检查单", "极值题对照检查", "端点可达性检查",
            "序号对齐检查", "可行性与数量检查",
        ):
            self.assertIn(label, requirements)

    def test_audit_receives_special_checks_but_not_strategy_examples(self):
        problem = (
            "Hamiltonian paths in a cyclic grid with directed transitions "
            "x_i-x_{i+1} is -1 or 39."
        )
        client = CaptureClient([
            '{"verdict":"uncertain","first_fatal_error":"","invalid_claim":"",'
            '"evidence":"","counterexample_or_evidence":"",'
            '"unmet_obligations":[],"required_changes":[],"forbidden_reuse":[],'
            '"replacement_route":"","repair_instruction":""}'
        ])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem=problem, efficient_runtime=True, started_at=now,
            deadline_at=now + 100, finalize_reserve_seconds=0,
        )
        runtime._solver_strategy_cards = "EXAMPLE_PROBLEM\nEXAMPLE_SOLUTION"
        runtime._audit(
            problem, ProblemProfile(domain="combinatorics", answer_mode="computation"),
            StagedStrategy(), "草稿", {"ok": True, "summary": []},
        )
        audit_payload = client.calls[0]["messages"][1]["content"]
        self.assertIn("special_requirements", audit_payload)
        self.assertIn("完整周期回到该列", audit_payload)
        self.assertNotIn("EXAMPLE_PROBLEM", audit_payload)

    def test_model_fidelity_rejects_a_relaxed_directed_transition(self):
        response = (
            '{"verdict":"fail","first_fatal_error":"草稿将单向横向转移扩成双向。",'
            '"source_constraint":"x_next = x_current + 1 (mod 20)",'
            '"solver_claim":"x_next = x_current ± 1 (mod 20)",'
            '"affected_reasoning":"后续计数对应无向图而非题面有向图。",'
            '"required_changes":["按单向边重新建立状态转移"],'
            '"additional_errors":[{"error_type":"endpoint","invalid_claim":"固定端点",'
            '"evidence":"题面只固定端点所在行",'
            '"affected_reasoning":"端点分类失效",'
            '"required_changes":["枚举端点状态"],'
            '"forbidden_reuse":["从相似切口题固定端点"],'
            '"prevention_rule":"端点只能按题面明确条件固定"}]}'
        )
        client = CaptureClient([response])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="有向图计数", efficient_runtime=True, started_at=now,
            deadline_at=now + 300, finalize_reserve_seconds=0,
        )
        runtime._constraint_ledger = "Constraints: x_next = x_current + 1 (mod 20)"

        fidelity = runtime._model_fidelity(
            "有向图计数", "图中允许 x_next = x_current ± 1 (mod 20)。"
        )
        audit = runtime._fidelity_failure_as_audit(fidelity)

        self.assertEqual(fidelity.verdict, "fail")
        self.assertEqual(audit.verdict, "fail")
        self.assertEqual(audit.error_type, "model")
        self.assertIn("按单向边重新建立状态转移", audit.required_changes)
        self.assertEqual(audit.additional_errors[0].error_type, "endpoint")
        self.assertIn("从相似切口题固定端点", audit.additional_errors[0].forbidden_reuse)
        fidelity_prompt = client.calls[0]["messages"][1]["content"]
        self.assertIn("x_next = x_current + 1", fidelity_prompt)
        self.assertNotIn("EXAMPLE_PROBLEM", fidelity_prompt)

    def test_constraint_ledger_preserves_raw_formula_not_retrieval_interpretation(self):
        problem = (
            r"For all \(1 \leq i \leq 59\), exactly one holds: "
            r"\(x_i-x_{i+1}\) is \(-1\) or \(19\)."
        )
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())

        ledger = runtime._build_constraint_ledger(problem)

        self.assertIn(r"\(x_i-x_{i+1}\)", ledger)
        self.assertIn(r"\(-1\)", ledger)
        self.assertIn(r"\(19\)", ledger)
        self.assertNotIn("±1", ledger)

    def test_model_fidelity_rejects_unquoted_solver_claim(self):
        client = CaptureClient([
            '{"verdict":"fail","first_fatal_error":"方向相反",'
            '"source_constraint":"x_i-x_{i+1} is -1 or 19",'
            '"solver_claim":"directed horizontal edges from x to x-1",'
            '"affected_reasoning":"后续计数失效","required_changes":[]}'
        ])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="有向图计数", efficient_runtime=True, started_at=now,
            deadline_at=now + 300, finalize_reserve_seconds=0,
        )
        runtime._constraint_ledger = "x_i-x_{i+1} is -1 or 19"

        fidelity = runtime._model_fidelity(
            "有向图计数", "草稿明确写 x_{i+1}=x_i+1 (mod 20)。"
        )

        self.assertEqual(fidelity.verdict, "uncertain")
        self.assertIn("未在草稿中逐字出现", fidelity.first_fatal_error)

    def test_model_fidelity_retries_without_thinking_after_invalid_response(self):
        client = CaptureClient([
            "not valid json",
            '{"verdict":"pass","first_fatal_error":"","source_constraint":"",'
            '"solver_claim":"","affected_reasoning":"","required_changes":[]}',
        ])
        runtime = StagedReasoningRuntime(
            client, AgentConfig(staged_model_fidelity_thinking_mode=True)
        )
        now = time.monotonic()
        runtime.state = AgentState(
            problem="模型检查", efficient_runtime=True, started_at=now,
            deadline_at=now + 300, finalize_reserve_seconds=0,
        )
        runtime._constraint_ledger = "x_next = x_current + 1"

        fidelity = runtime._model_fidelity("模型检查", "草稿按该约束建模。")

        self.assertEqual(fidelity.verdict, "pass")
        self.assertEqual(len(client.calls), 2)
        self.assertTrue(client.calls[0]["thinking_mode"])
        self.assertEqual(client.calls[0]["max_tokens"], 65536)
        self.assertFalse(client.calls[1]["thinking_mode"])
        self.assertEqual(client.calls[1]["max_tokens"], 4096)
        self.assertIn(
            "model_fidelity_retry_without_thinking",
            [item["type"] for item in runtime.trace],
        )

    def test_staged_calls_use_per_stage_settings(self):
        client = CaptureClient()
        config = AgentConfig(
            staged_strategy_thinking_mode=False,
            staged_strategy_max_tokens=1234,
            staged_solver_thinking_mode=False,
            staged_solver_repair_thinking_mode=True,
            staged_solver_max_tokens=5678,
        )
        runtime = StagedReasoningRuntime(client, config)
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求 1+1。",
            efficient_runtime=True,
            started_at=now,
            deadline_at=now + 100,
            finalize_reserve_seconds=0,
        )

        runtime._call("strategy", "strategy", {}, max_tokens=config.staged_strategy_max_tokens)
        runtime._call("solver", "solver", {}, max_tokens=config.staged_solver_max_tokens)
        runtime._call(
            "solver_repair", "solver repair", {}, max_tokens=config.staged_solver_max_tokens
        )

        self.assertFalse(client.calls[0]["thinking_mode"])
        self.assertEqual(client.calls[0]["max_tokens"], 1234)
        self.assertEqual(client.calls[0]["temperature"], 0.3)
        self.assertFalse(client.calls[1]["thinking_mode"])
        self.assertEqual(client.calls[1]["max_tokens"], 5678)
        self.assertTrue(client.calls[2]["thinking_mode"])
        self.assertEqual(client.calls[2]["max_tokens"], 131072)

    def test_model_response_debug_is_emitted_before_runtime_returns(self):
        client = CaptureClient(["即时响应"])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求值", efficient_runtime=True, started_at=now,
            deadline_at=now + 100, finalize_reserve_seconds=0,
        )
        stderr = io.StringIO()
        with patch.dict(os.environ, {"CUSTOM2_DEBUG_MODEL_RESPONSES": "1"}), redirect_stderr(stderr):
            self.assertEqual(runtime._call("strategy", "x", {}, max_tokens=8), "即时响应")
        output = stderr.getvalue()
        self.assertIn("[custom2_model_response]", output)
        self.assertIn('"call_type": "strategy"', output)
        self.assertIn("即时响应", output)

    def test_incomplete_solver_uses_one_compressed_prefill_retry(self):
        compressed_continuation = (
            "简短分析。\n\n## 详细解题步骤\n步骤 1：计算。\n\n"
            "## 最终答案\n\\boxed{2}\n\n## 关键验证点\n代回成立。"
        )
        client = CaptureClient(["尚未形成完整章节", compressed_continuation])
        config = AgentConfig(
            staged_compact_reasoning_only=False,
            staged_solver_thinking_mode=True,
            staged_solver_max_tokens=24576,
            staged_solver_compressed_thinking_mode=False,
            staged_solver_compressed_max_tokens=8192,
        )
        runtime = StagedReasoningRuntime(client, config)
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求 1+1。", efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )

        result = runtime._solve(
            "求 1+1。",
            ProblemProfile(domain="algebra", answer_mode="computation"),
            StagedStrategy(problem_type="calculation", risk_level="low"),
            "代数技能",
            attempt=1,
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("## 问题分析\n"))
        self.assertEqual(len(client.calls), 2)
        self.assertTrue(client.calls[0]["thinking_mode"])
        self.assertEqual(client.calls[0]["max_tokens"], 131072)
        self.assertEqual(
            client.calls[0]["messages"][0],
            {"role": "system", "content": "你是algebra领域的数学专家。"},
        )
        normal_user = client.calls[0]["messages"][1]
        self.assertEqual(normal_user["role"], "user")
        self.assertIn("【原题】\n求 1+1。", normal_user["content"])
        self.assertIn("【数学领域技能参考】\n代数技能", normal_user["content"])
        self.assertIn("【策略建议（不是已证事实）】", normal_user["content"])
        self.assertIn("严格输出四个 Markdown 章节", normal_user["content"])
        self.assertIn("使用公式/定理", normal_user["content"])
        self.assertIn("验证点 2", normal_user["content"])
        self.assertIn("【格式示例：仅展示格式", normal_user["content"])
        self.assertFalse(client.calls[1]["thinking_mode"])
        self.assertEqual(client.calls[1]["temperature"], 0.3)
        self.assertEqual(client.calls[1]["max_tokens"], 8192)
        self.assertEqual(
            client.calls[1]["messages"][0],
            {"role": "system", "content": "你是algebra领域的数学专家。"},
        )
        compressed_user = client.calls[1]["messages"][1]
        self.assertEqual(compressed_user["role"], "user")
        self.assertIn("【压缩不思考救援】", compressed_user["content"])
        self.assertIn("失败原因：missing_fixed_sections", compressed_user["content"])
        self.assertIn("代数技能", compressed_user["content"])
        self.assertEqual(
            client.calls[1]["messages"][-1],
            {"role": "assistant", "content": "## 问题分析\n"},
        )
        events = [item["type"] for item in runtime.trace]
        self.assertEqual(events.count("compressed_solver_retry_started"), 1)
        self.assertIn("compressed_solution_received", events)

    def test_complete_solver_does_not_use_compressed_retry(self):
        complete = (
            "## 问题分析\n直接计算。\n## 详细解题步骤\n1+1=2。\n"
            "## 最终答案\n\\boxed{2}\n## 关键验证点\n代回成立。"
        )
        client = CaptureClient([complete])
        runtime = StagedReasoningRuntime(
            client, AgentConfig(staged_compact_reasoning_only=False)
        )
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求 1+1。", efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )

        result = runtime._solve(
            "求 1+1。", ProblemProfile(), StagedStrategy(), "", attempt=1,
        )

        self.assertEqual(result, complete)
        self.assertEqual(len(client.calls), 1)
        self.assertFalse(client.calls[0]["thinking_mode"])
        self.assertEqual(client.calls[0]["max_tokens"], 24576)
        self.assertNotIn("【压缩推理模式】", client.calls[0]["messages"][1]["content"])
        self.assertEqual(len(client.calls[0]["messages"]), 2)

    def test_default_switch_uses_compact_solver_for_primary_attempt(self):
        compact = (
            "简析。\n## 详细解题步骤\n步骤 1：计算。\n"
            "## 最终答案\n\\boxed{2}\n## 关键验证点\n代回成立。"
        )
        client = CaptureClient([compact])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求 1+1。", efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )

        result = runtime._solve(
            "求 1+1。", ProblemProfile(), StagedStrategy(), "定理卡片", attempt=1,
        )

        self.assertIsNotNone(result)
        self.assertTrue(client.calls[0]["thinking_mode"])
        self.assertEqual(client.calls[0]["temperature"], 0.3)
        self.assertEqual(client.calls[0]["max_tokens"], 131072)
        self.assertIn("使用公式/定理", client.calls[0]["messages"][1]["content"])
        self.assertIn("至少两条", client.calls[0]["messages"][1]["content"])
        self.assertIn("【格式示例：仅展示格式", client.calls[0]["messages"][1]["content"])
        self.assertIn("primary_direct_compressed_started", [item["type"] for item in runtime.trace])

    def test_solver_saves_candidate_before_trace_recording_can_fail(self):
        complete = (
            "## 问题分析\n简析。\n## 详细解题步骤\n步骤 1。\n"
            "## 最终答案\n\\boxed{17}\n## 关键验证点\n代回。"
        )
        runtime = StagedReasoningRuntime(CaptureClient([complete]), AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求值", efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )
        runtime._record_solution_steps = Mock(side_effect=RuntimeError("trace failure"))

        with self.assertRaisesRegex(RuntimeError, "trace failure"):
            runtime._solve("求值", ProblemProfile(), StagedStrategy(), "", attempt=1)

        recovered = runtime.recover_unhandled_exception(RuntimeError("trace failure"))
        self.assertEqual(recovered["final_response"], "\\boxed{17}")
        self.assertEqual(recovered["solve_status"], "success")

    def test_audit_repair_goes_directly_to_one_compact_rederivation(self):
        compact = (
            "重新建模。\n## 详细解题步骤\n步骤 1：独立推导。\n"
            "## 最终答案\n\\boxed{3}\n## 关键验证点\n边界代回成立。"
        )
        client = CaptureClient([compact])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求 1+1。", efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )
        audit = StagedAudit(
            verdict="fail", first_fatal_error="旧路线不成立",
            required_changes=["从定义重新推导"],
        )

        result = runtime._solve(
            "求 1+1。", ProblemProfile(), StagedStrategy(), "技能",
            attempt=2, previous="旧答案", audit=audit,
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(client.calls), 1)
        self.assertTrue(client.calls[0]["thinking_mode"])
        self.assertEqual(client.calls[0]["temperature"], 0.8)
        self.assertIn("失败原因：audit_rejected_original_route", client.calls[0]["messages"][1]["content"])
        self.assertIn("【修复强制要求】", client.calls[0]["messages"][1]["content"])
        self.assertIn("【修复闭环要求】", client.calls[0]["messages"][1]["content"])
        self.assertIn("【验证一致性硬门槛】", client.calls[0]["messages"][1]["content"])
        self.assertIn("repair_direct_compressed_started", [item["type"] for item in runtime.trace])

    def test_final_arbitrator_uses_reserved_finalization_call(self):
        decision = (
            "## 问题分析\n根据反例排除旧路线。\n"
            "## 详细解题步骤\n重新代回定义。\n"
            "## 最终答案\n\\boxed{7}\n"
            "## 关键验证点\n边界成立。"
        )
        client = CaptureClient([decision])
        runtime = StagedReasoningRuntime(client, AgentConfig())
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求值", efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )
        result = runtime._final_arbitrate(
            "求值", ProblemProfile(), StagedStrategy(), "旧稿", "修复稿",
            StagedAudit(verdict="fail", first_fatal_error="反例"),
            candidates=[
                {
                    "attempt": 1,
                    "draft": "## 最终答案\n\\boxed{3}",
                    "audit": StagedAudit(verdict="fail", first_fatal_error="待核验"),
                },
                {
                    "attempt": 2,
                    "draft": "## 最终答案\n\\boxed{7}",
                    "audit": StagedAudit(verdict="fail", first_fatal_error="待核验"),
                },
            ],
        )

        self.assertEqual(result, decision)
        self.assertEqual(client.calls[0]["max_tokens"], 131072)
        self.assertFalse(client.calls[0]["thinking_mode"])
        self.assertIn("final_arbitration_started", [item["type"] for item in runtime.trace])
        arbitration_payload = client.calls[0]["messages"][1]["content"]
        self.assertIn("候选 1", arbitration_payload)
        self.assertIn("候选 2", arbitration_payload)
        self.assertIn("\\boxed{3}", arbitration_payload)
        self.assertIn("\\boxed{7}", arbitration_payload)

    def test_timeout_and_reasoning_exhaustion_trigger_compressed_retry(self):
        complete = (
            "## 问题分析\n简析。\n## 详细解题步骤\n步骤 1：计算。\n"
            "## 最终答案\n\\boxed{2}\n## 关键验证点\n代回成立。"
        )
        failures = [
            TimeoutError("network read timed out"),
            {
                "content": "",
                "reasoning_content": "未能在预算内完成内部推理",
                "finish_reason": "length",
            },
        ]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                client = CaptureClient([failure, complete])
                runtime = StagedReasoningRuntime(
                    client, AgentConfig(staged_compact_reasoning_only=False)
                )
                now = time.monotonic()
                runtime.state = AgentState(
                    problem="求 1+1。", efficient_runtime=True, started_at=now,
                    deadline_at=now + 1000, finalize_reserve_seconds=120,
                )
                result = runtime._solve(
                    "求 1+1。", ProblemProfile(), StagedStrategy(), "", attempt=1,
                )
                self.assertIsNotNone(result)
                self.assertEqual(len(client.calls), 2)
                self.assertTrue(client.calls[1]["thinking_mode"])

    def test_transport_runtime_error_triggers_compressed_retry(self):
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        runtime._last_call_error = (
            "RuntimeError",
            "Chat completion failed after 3 attempts: SSLEOFError",
        )
        reason = runtime._solver_failure_reason("")
        self.assertTrue(reason.startswith("network_transport_error:"))
        self.assertTrue(runtime._should_compressed_retry(reason))

    def test_emergency_without_partial_uses_small_direct_solver(self):
        direct = "## 详细解题步骤\n1+1=2。\n## 最终答案\n\\boxed{2}"
        client = CaptureClient([direct])
        config = AgentConfig(
            staged_emergency_max_tokens=2048,
            staged_emergency_timeout_seconds=45,
        )
        runtime = StagedReasoningRuntime(client, config)
        now = time.monotonic()
        runtime.state = AgentState(
            problem="求 1+1。", efficient_runtime=True, started_at=now,
            deadline_at=now + 1000, finalize_reserve_seconds=120,
        )

        result = runtime._emergency_solve(
            "求 1+1。", ProblemProfile(),
            StagedStrategy(main_method="直接计算"), "普通求解超时",
        )

        self.assertEqual(result, direct)
        self.assertEqual(
            client.calls[0]["messages"][0]["content"],
            STAGED_DIRECT_EMERGENCY_PROMPT,
        )
        self.assertEqual(client.calls[0]["max_tokens"], 131072)
        self.assertFalse(client.calls[0]["thinking_mode"])
        self.assertEqual(runtime.debug_trace[-1]["timeout_seconds"], 45)
        payload = client.calls[0]["messages"][1]["content"]
        self.assertNotIn("skill_material", payload)
        self.assertNotIn("available_information", payload)
        self.assertEqual(runtime.trace[-1]["data"]["mode"], "direct")

    def test_placeholder_result_exposes_timeout_status(self):
        runtime = StagedReasoningRuntime(CaptureClient(), AgentConfig())
        runtime.debug_trace.append({
            "type": "model_call_error",
            "error_type": "ModelCallTimedOut",
            "content": "read timeout",
        })
        result = runtime._result("无法确定唯一答案")
        self.assertEqual(result["solve_status"], "timeout")

    def test_run_recovers_from_two_solver_timeouts_with_direct_emergency(self):
        direct = "## 详细解题步骤\n1+1=2。\n## 最终答案\n\\boxed{2}"
        client = CaptureClient([
            '{"domain":"advanced_olympiad_mathematics","answer_mode":"computation","obligations":[]}',
            '{"problem_type":"calculation","risk_level":"low"}',
            TimeoutError("primary read timeout"),
            TimeoutError("compressed read timeout"),
            direct,
        ])

        result = StagedReasoningRuntime(
            client, AgentConfig(
                staged_compact_reasoning_only=False,
                staged_strategy_retrieval_enabled=False,
                staged_strategy_model_enabled=True,
            )
        ).run("求 1+1。")

        self.assertEqual(result["final_response"], r"\boxed{2}")
        self.assertEqual(result["solve_status"], "success")
        emergency = [
            item for item in result["trace"]
            if item["type"] == "emergency_solve_started"
        ]
        self.assertEqual(emergency[0]["data"]["mode"], "direct")
        self.assertEqual(len(client.calls), 5)


if __name__ == "__main__":
    unittest.main()
