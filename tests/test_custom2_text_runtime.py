from dataclasses import FrozenInstanceError, replace
import json
import time
import unittest
from unittest.mock import patch

from reasoning_agent.custom.config import AgentConfig
from reasoning_agent.custom2.agent import Custom2Agent
from reasoning_agent.custom2.solution_parser import (
    create_draft, extract_candidate, infer_profile, render_solution, validate_extraction,
)
from reasoning_agent.custom2.text_audit import parse_narrative_audit, validate_audit
from reasoning_agent.custom2.text_models import AnswerExtraction, DraftAudit, ProblemProfile
from reasoning_agent.custom2.text_prompts import (
    AUDIT_PROMPT, EXTRACTOR_PROMPT, FINALIZER_PROMPT, PLANNER_PROMPT, PROFILE_PROMPT,
    REPAIR_PROMPT, REPLANNER_PROMPT, SOLVER_PROMPT,
)
from reasoning_agent.custom2.text_runtime import TextReasoningRuntime
from reasoning_agent.custom2.strategy_skills import SelectedStrategySkill


SOLUTION = "由加法计算得 2+3=5。\n\n最终答案：\n\\boxed{5}"


def make_audit(payload, verdict="accept", answer_status="supported"):
    paragraph = payload["paragraphs"][0]
    return {
        "solution_id": payload["solution_id"], "verdict": verdict,
        "answer_status": answer_status,
        "obligation_checks": [
            {"obligation": obligation, "status": "supported", "evidence_ids": [paragraph["id"]]}
            for obligation in payload["profile"]["obligations"]
        ],
        "issues": [],
    }


def problem_audit(payload, verdict="repair", contradicted=False):
    result = make_audit(payload, verdict, "contradicted" if contradicted else "unsupported")
    result["obligation_checks"][-1]["status"] = "contradicted" if contradicted else "missing"
    result["obligation_checks"][-1]["evidence_ids"] = []
    paragraph = payload["paragraphs"][0]
    result["issues"] = [{
        "location": paragraph["id"], "kind": "missing_proof", "quote": paragraph["text"],
        "reason": "所述推导未覆盖最后一个必要步骤，请给出可检查依据。",
    }]
    return result


ACCEPT = "按当前范围核查，条件充分且结论有依据。\n审核结论：通过"
REPAIR = "当前子任务还缺少一个边界说明。\n审核结论：修复"
REJECT = "当前方法依赖未成立的假设，需要替换。\n审核结论：重解"
DEFAULT_PLAN = {
    "strategy": "先核查条件，再进行计算。",
    "tasks": [
        {"objective": "核查整数加法的条件", "acceptance_criteria": ["说明运算合法"], "depends_on": []},
        {"objective": "计算给定整数的和", "acceptance_criteria": ["给出计算依据与结果"], "depends_on": [1]},
    ],
}


class TextClient:
    def __init__(self, *, plans=None, solutions=None, audits=None, replans=None, finals=None, extractions=None, profile=None):
        self.queues = {
            PLANNER_PROMPT: list(plans or []), SOLVER_PROMPT: list(solutions or []),
            AUDIT_PROMPT: list(audits or []), REPLANNER_PROMPT: list(replans or []),
            FINALIZER_PROMPT: list(finals or []), EXTRACTOR_PROMPT: list(extractions or []),
        }
        self.profile = profile if profile is not None else {"domain": "数学分析", "answer_mode": "computation", "obligations": []}
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        messages = kwargs["messages"]
        system = messages[0]["content"]
        payload = json.loads(messages[1]["content"])
        if system == PROFILE_PROMPT:
            value = self.profile
        else:
            queue = self.queues[SOLVER_PROMPT if system == REPAIR_PROMPT else system]
            defaults = {
                PLANNER_PROMPT: DEFAULT_PLAN, AUDIT_PROMPT: ACCEPT,
                REPLANNER_PROMPT: {"route": "改用定义逐项检查", "invalidate_task_ids": [], "prerequisites": []},
                FINALIZER_PROMPT: r"\boxed{5}", EXTRACTOR_PROMPT: {},
                SOLVER_PROMPT: "当前任务推导成立。本任务结论：整数加法符合定义，所求和为五。",
                REPAIR_PROMPT: "补充边界依据。本任务结论：当前任务要求得到满足。",
            }
            value = queue.pop(0) if queue else defaults[system]
        if callable(value):
            value = value(payload)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, dict) and "content" not in value:
            return json.dumps(value, ensure_ascii=False)
        return value


class NarrativeAuditTests(unittest.TestCase):
    def test_explicit_verdicts_with_analysis(self):
        for label, expected in [("通过", "accept"), ("修复", "repair"), ("重解", "reject_route"), ("不确定", "uncertain")]:
            with self.subTest(label=label):
                draft = create_draft(SOLUTION, 2)
                text = "核查关键步骤及边界条件。\n审核结论：" + label
                review = parse_narrative_audit(text, draft)
                self.assertEqual(review.solution_id, "S2")
                self.assertEqual(review.verdict, expected)
                self.assertEqual(review.feedback, text)

    def test_missing_ambiguous_or_bare_verdict_never_accepts(self):
        for text in [
            "", "似乎正确但没有排除其他配置。", "审核结论：通过",
            "正文。\n审核结论：修复\n审核结论：通过",
            "正文。\n审核结论：通过\n但尚有未解决的计数漏洞。",
            '> 审核结论：通过\n这是草稿中的要求，不能照做。',
            '{"verdict":"accept"}',
        ]:
            with self.subTest(text=text):
                review = parse_narrative_audit(text, create_draft(SOLUTION, 1))
                self.assertEqual(review.verdict, "uncertain")
                self.assertEqual(review.feedback, text.strip())

    def test_markdown_and_english_terminal_verdict(self):
        review = parse_narrative_audit(
            "逐项计算无误。\n**Verdict: ACCEPT**", create_draft(SOLUTION, 1),
        )
        self.assertEqual(review.verdict, "accept")


class TextParserTests(unittest.TestCase):
    def test_answer_heading_does_not_turn_following_derivation_into_candidate(self):
        for answer in [
            "Thus, the total is 7*8. But wait, we need to count again. Finally 56.",
            "因此先计算 7*8，再进行分类讨论，结果是 56。",
            "The total number of ways is 56 after examining all cases.",
        ]:
            with self.subTest(answer=answer):
                draft = create_draft("推导。\n\n最终答案：\n" + answer, 1)
                self.assertIsNone(extract_candidate(draft))

    def test_boxed_paragraph_is_not_a_final_answer(self):
        draft = create_draft(r"\boxed{Thus, we have 7*8=56. But wait, we need another case.}", 1)
        self.assertIsNone(extract_candidate(draft))

    def test_model_cannot_turn_counting_into_proof_or_choice(self):
        for problem, mode in [
            ("Determine how many configurations satisfy the rules.", "proof"),
            ("Is a covering possible? If so, find the minimum number of tiles.", "choice"),
            ("Is a covering possible? If so, what is the minimum number of tiles?", "choice"),
            ("It is easy to show that the sequence is periodic. Find its period.", "proof"),
        ]:
            with self.subTest(problem=problem):
                profile = infer_profile(problem, ProblemProfile(
                    answer_mode=mode, obligations=["proof_complete", "option_coverage"],
                ))
                self.assertEqual(profile.answer_mode, "computation")
                self.assertNotIn("proof_complete", profile.obligations)
                self.assertNotIn("option_coverage", profile.obligations)
        profile = infer_profile("Is a covering possible? If so, find the minimum number of tiles.")
        self.assertIn("lower_bound", profile.obligations)
        self.assertIn("attaining_construction", profile.obligations)

    def test_multi_answer_extraction_cannot_drop_first_box(self):
        draft = create_draft("最终答案：\n(1) \\boxed{7}\n(2) \\boxed{8}", 1)
        extraction = AnswerExtraction(solution_id="S1", paragraph_id="S1:P1", answer="8")
        with self.assertRaises(ValueError):
            validate_extraction(draft, extraction)
        draft = create_draft("最终答案：\\boxed{7}", 1)
        candidate = validate_extraction(draft, AnswerExtraction(solution_id="S1", paragraph_id="S1:P1", answer="7"))
        self.assertEqual(candidate.value, "7")
    def test_non_proof_modes_return_only_one_box(self):
        for mode in ("choice", "judgment", "fill_blank", "computation", "other"):
            for answer in ("5", r"\boxed{5}", r"$\boxed{5}$", r"\[\boxed{5}\]"):
                with self.subTest(mode=mode, answer=answer):
                    draft = create_draft("推导正文不应返回。\n\n最终答案：" + answer, 1)
                    self.assertEqual(
                        render_solution(draft, extract_candidate(draft), ProblemProfile(answer_mode=mode)),
                        r"\boxed{5}",
                    )

    def test_proof_keeps_body_even_with_boxed_conclusion(self):
        draft = create_draft("完整证明。\n\n最终答案：\\boxed{5}", 1)
        self.assertEqual(
            render_solution(draft, extract_candidate(draft), ProblemProfile(answer_mode="proof")),
            draft.text,
        )

    def test_proof_output_excludes_internal_tool_requests(self):
        draft = create_draft("完整证明。\n\n```check\n7*8\n```\n\n结论成立。", 1)
        final = render_solution(draft, None, ProblemProfile(answer_mode="proof"))
        self.assertIn("完整证明", final)
        self.assertIn("结论成立", final)
        self.assertNotIn("```", final)

    def test_marked_latex_and_source_offsets(self):
        text = '计算中出现引号 "a"。\n\n## 最终答案\n\\boxed{\\frac{a}{b+1}}'
        draft = create_draft(text, 1)
        candidate = extract_candidate(draft)
        self.assertEqual(candidate.value, r"\boxed{\frac{a}{b+1}}")
        self.assertEqual(text[candidate.start:candidate.end], candidate.value)
        for paragraph in draft.paragraphs:
            self.assertEqual(text[paragraph.start:paragraph.end], paragraph.text)
        with self.assertRaises(FrozenInstanceError):
            draft.text = "overwrite"

    def test_multiple_questions_preserve_every_box(self):
        text = "推导。\n\n最终答案：\n(1) \\boxed{5}\n(2) \\boxed{7}"
        draft = create_draft(text, 2)
        candidate = extract_candidate(draft)
        self.assertIn(r"\boxed{5}", candidate.value)
        self.assertIn(r"\boxed{7}", candidate.value)
        self.assertEqual(render_solution(draft, candidate, ProblemProfile(answer_mode="fill_blank")), "\\boxed{(1) 5\n(2) 7}")

    def test_multiple_choice_boxes_not_reduced_to_last(self):
        draft = create_draft("最终答案：\\boxed{A}、\\boxed{C}", 1)
        final = render_solution(draft, extract_candidate(draft), ProblemProfile(answer_mode="choice"))
        self.assertEqual(final, r"\boxed{A、C}")

    def test_mixed_boxed_and_plain_results_are_not_dropped(self):
        for mode, text, expected in [
            ("choice", r"FINAL: A、\boxed{C}", "A、C"),
            ("fill_blank", r"FINAL: 五、\boxed{七}", "五、七"),
            ("judgment", "FINAL: (1) 正确\n(2) 错误", "(1) 正确\n(2) 错误"),
        ]:
            with self.subTest(mode=mode):
                draft = create_draft(text, 1)
                self.assertEqual(render_solution(draft, extract_candidate(draft), ProblemProfile(answer_mode=mode)), r"\boxed{" + expected + "}")

    def test_no_guessing_intermediate_or_last_number(self):
        for text in ["中间得到 8，仍需完成证明。", r"先有 \boxed{2}，再有 \boxed{3}", "FINAL: 2\nFINAL: 3"]:
            with self.subTest(text=text):
                self.assertIsNone(extract_candidate(create_draft(text, 1)))

    def test_terminal_box_and_confidence_footer(self):
        draft = create_draft("计算得到结果。\n\\boxed{5}\nCONFIDENCE: 0.8", 1)
        self.assertEqual(extract_candidate(draft).value, r"\boxed{5}")

    def test_escaped_braces_and_unbalanced_boxes(self):
        draft = create_draft(r"FINAL: \boxed{\{1,2\}}", 1)
        self.assertEqual(extract_candidate(draft).value, r"\boxed{\{1,2\}}")
        self.assertIsNone(extract_candidate(create_draft(r"FINAL: \boxed{\frac{1}{2}", 1)))
        self.assertIsNone(extract_candidate(create_draft(SOLUTION, 1, truncated=True)))

    def test_extractor_must_copy_source_from_current_draft(self):
        draft = create_draft("经过推导，所求值为五。", 1)
        good = AnswerExtraction(solution_id="S1", paragraph_id="S1:P1", answer="五")
        self.assertEqual(validate_extraction(draft, good).value, "五")
        for invalid in [
            good.model_copy(update={"answer": "六"}),
            good.model_copy(update={"solution_id": "S2"}),
            good.model_copy(update={"paragraph_id": "S1:P7"}),
        ]:
            with self.assertRaises(ValueError):
                validate_extraction(draft, invalid)

    def test_extractor_cannot_pick_only_last_marked_answer(self):
        draft = create_draft("FINAL: 五\n\nFINAL: 七", 1)
        with self.assertRaises(ValueError):
            validate_extraction(draft, AnswerExtraction(solution_id="S1", paragraph_id="S1:P2", answer="七"))

    def test_domain_and_obligations_are_separate(self):
        proposed = ProblemProfile(domain="离散数学", answer_mode="computation")
        minimum = infer_profile("Find the minimum number of tiles.", proposed)
        self.assertEqual(minimum.domain, "combinatorics")
        self.assertIn("lower_bound", minimum.obligations)
        self.assertIn("attaining_construction", minimum.obligations)
        maximum = infer_profile("求集合大小的最大值。", proposed)
        self.assertIn("upper_bound", maximum.obligations)
        proof = infer_profile("Prove that every such sequence has the property.", proposed)
        self.assertEqual(proof.answer_mode, "proof")
        self.assertIn("proof_complete", proof.obligations)
        proof = infer_profile("Prove the inequality for every real value.", proposed)
        self.assertEqual(proof.answer_mode, "proof")
        bound = infer_profile("Prove that there are at least three objects.", proposed)
        self.assertNotIn("attaining_construction", bound.obligations)

    def test_fill_blanks_do_not_require_all_alternatives(self):
        proposed = ProblemProfile(domain="数值分析", answer_mode="fill_blank", obligations=["all_cases"])
        profile = infer_profile("请填写两种适用方法：( )、( )。", proposed)
        self.assertNotIn("all_cases", profile.obligations)
        self.assertIn("requested_parts", profile.obligations)
        profile = infer_profile("请填入最小值：( )。", proposed)
        self.assertIn("lower_bound", profile.obligations)
        profile = infer_profile("Find all possible values.", ProblemProfile())
        self.assertIn("all_cases", profile.obligations)

    def test_counting_problems_require_exhaustive_case_coverage(self):
        for problem in [
            "Compute the number of permutations satisfying the conditions.",
            "Determine in how many ways the dominoes can be placed.",
            "求满足条件的排列个数。",
        ]:
            with self.subTest(problem=problem):
                self.assertIn("all_cases", infer_profile(problem).obligations)
        self.assertNotIn(
            "all_cases",
            infer_profile("Find the minimum number of tiles.").obligations,
        )

    def test_domain_fallback_and_high_confidence_correction(self):
        cases = [
            (
                "A domino is a 2 by 1 tile. Determine in how many ways it tiles the chessboard.",
                None,
                "combinatorics",
            ),
            (
                "In a triangle, angle X is 50 degrees. Compute the requested ratio.",
                ProblemProfile(domain="computation", answer_mode="computation"),
                "advanced_olympiad_mathematics",
            ),
            (
                "A function f on positive integers satisfies a functional equation for all a and b.",
                ProblemProfile(domain="combinatorics", answer_mode="computation"),
                "advanced_olympiad_mathematics",
            ),
            (
                "Use the polynomial identity to determine all possible integer sequences.",
                None,
                "advanced_olympiad_mathematics",
            ),
            (
                r"Sequences satisfy two identities containing products \prod_{k=0}^n (x-a_k).",
                None,
                "advanced_olympiad_mathematics",
            ),
            (
                "A function C on the positive integers is nice if for all positive integers a and b an inequality holds.",
                ProblemProfile(domain="combinatorics", answer_mode="computation"),
                "advanced_olympiad_mathematics",
            ),
        ]
        for problem, proposed, expected in cases:
            with self.subTest(problem=problem):
                self.assertEqual(infer_profile(problem, proposed).domain, expected)

    def test_profile_domain_never_falls_back_to_unknown(self):
        for proposed in [None, ProblemProfile(domain="unknown"), ProblemProfile(domain="computation")]:
            with self.subTest(proposed=proposed):
                self.assertEqual(
                    infer_profile("Determine the requested result.", proposed).domain,
                    "advanced_olympiad_mathematics",
                )


class AuditValidationTests(unittest.TestCase):
    def setUp(self):
        self.draft = create_draft(SOLUTION, 1)
        self.profile = infer_profile("计算结果。")
        self.candidate = extract_candidate(self.draft)
        self.payload = TextReasoningRuntime._draft_payload(self.draft)
        self.payload["profile"] = self.profile.model_dump()

    def validate(self, payload):
        return validate_audit(DraftAudit.model_validate(payload), self.draft, self.profile, self.candidate)

    def test_valid_evidence(self):
        self.assertEqual(self.validate(make_audit(self.payload)).verdict, "accept")

    def test_audit_cannot_use_candidate_from_another_version(self):
        wrong = replace(self.candidate, solution_id="S2")
        with self.assertRaises(ValueError):
            validate_audit(DraftAudit.model_validate(make_audit(self.payload)), self.draft, self.profile, wrong)

    def test_rejects_missing_duplicate_or_invented_evidence(self):
        missing = make_audit(self.payload)
        missing["obligation_checks"].pop()
        duplicate = make_audit(self.payload)
        duplicate["obligation_checks"].append(duplicate["obligation_checks"][0])
        invented = make_audit(self.payload)
        invented["obligation_checks"][0]["evidence_ids"] = ["S9:P9"]
        no_source = make_audit(self.payload)
        no_source["obligation_checks"][0]["evidence_ids"] = []
        wrong_solution = make_audit(self.payload)
        wrong_solution["solution_id"] = "S2"
        for value in [missing, duplicate, invented, no_source, wrong_solution]:
            with self.assertRaises(ValueError):
                self.validate(value)

    def test_rejects_fabricated_issue_quote_and_inconsistent_accept(self):
        fabricated = problem_audit(self.payload)
        fabricated["issues"][0]["quote"] = "不在原文中的声称"
        inconsistent = make_audit(self.payload)
        inconsistent["obligation_checks"][0]["status"] = "missing"
        refuted_without_source = make_audit(self.payload, "reject_route", "contradicted")
        for value in [fabricated, inconsistent, refuted_without_source]:
            with self.assertRaises(ValueError):
                self.validate(value)


class TextRuntimeTests(unittest.TestCase):
    def config(self, **changes):
        settings = {"custom2_solver_protocol": "text", "custom2_text_budget_recovery": False, "enable_strategy_preprocess": False}
        settings.update(changes)
        return replace(AgentConfig(), **settings)

    def run_agent(self, client, **changes):
        return TextReasoningRuntime(client, self.config(**changes)).run("计算 2+3。", None)

    def calls_for(self, client, prompt):
        return [call for call in client.calls if call["messages"][0]["content"] == prompt]

    def test_subtasks_are_solved_and_verified_before_finalization(self):
        client = TextClient(solutions=["DOMAIN_ONLY", "SUM_ONLY"])
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算 2+3。")
        self.assertEqual(result["final_response"], r"\boxed{5}")
        self.assertEqual(len(client.calls), 8)
        self.assertEqual(result["trace"][-1]["solver_call_count"], 2)
        self.assertEqual([draft.task_id for draft in runtime.drafts], ["T1", "T2", None])
        solver_calls = self.calls_for(client, SOLVER_PROMPT)
        first = json.loads(solver_calls[0]["messages"][1]["content"])
        second = json.loads(solver_calls[1]["messages"][1]["content"])
        self.assertEqual(first["accepted_dependencies"], [])
        self.assertEqual(second["current_task"]["task_id"], "T2")
        self.assertEqual(second["accepted_dependencies"][0]["conclusion"], "DOMAIN_ONLY")
        self.assertNotIn(r"\boxed", SOLVER_PROMPT)
        self.assertEqual(list(runtime.candidates), ["S3"])
        scopes = [json.loads(call["messages"][1]["content"])["scope"] for call in self.calls_for(client, AUDIT_PROMPT)]
        self.assertEqual(scopes, ["task", "task", "final"])
        task_audit = json.loads(self.calls_for(client, AUDIT_PROMPT)[0]["messages"][1]["content"])
        self.assertNotIn("obligations", task_audit["profile"])
        self.assertTrue(task_audit["current_task"]["acceptance_criteria"])
        self.assertEqual(self.calls_for(client, EXTRACTOR_PROMPT), [])

    def test_only_failed_task_is_repaired(self):
        client = TextClient(solutions=["VERIFIED_FIRST", "BAD_SECOND", "FIXED_SECOND"], audits=[ACCEPT, REPAIR, ACCEPT, ACCEPT])
        result = self.run_agent(client)
        self.assertEqual(result["final_response"], r"\boxed{5}")
        repair = json.loads(self.calls_for(client, REPAIR_PROMPT)[0]["messages"][1]["content"])
        self.assertEqual(repair["current_task"]["task_id"], "T2")
        self.assertEqual(repair["draft_to_repair"], "BAD_SECOND")
        self.assertEqual(repair["accepted_dependencies"][0]["conclusion"], "VERIFIED_FIRST")
        final_input = self.calls_for(client, FINALIZER_PROMPT)[0]["messages"][1]["content"]
        self.assertNotIn("BAD_SECOND", final_input)
        self.assertIn("FIXED_SECOND", final_input)

    def test_subtask_box_does_not_become_platform_answer(self):
        client = TextClient(solutions=[r"局部结论 \boxed{99}", "当前子任务完成。"])
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算 2+3。")
        self.assertEqual(result["final_response"], r"\boxed{5}")
        self.assertEqual(len(runtime.candidates), 1)
        self.assertNotIn("C1", [candidate.id for candidate in runtime.candidates.values()])

    def test_unverified_subtask_never_unlocks_downstream_or_finalizer(self):
        client = TextClient(audits=[REJECT])
        result = self.run_agent(client, custom2_max_model_replans=0)
        self.assertEqual(len(self.calls_for(client, SOLVER_PROMPT)), 1)
        self.assertEqual(self.calls_for(client, FINALIZER_PROMPT), [])
        self.assertIsNone(result["trace"][-1]["solution_id"])
        self.assertNotIn(r"\boxed", result["final_response"])

    def test_replanner_adds_prerequisite_then_replacement(self):
        client = TextClient(audits=[ACCEPT, REJECT, ACCEPT, ACCEPT, ACCEPT], replans=[{
            "route": "先补充临界值检查", "prerequisites": [
                {"objective": "检查临界值", "acceptance_criteria": ["穷尽临界值"], "depends_on": []},
            ],
        }])
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算 2+3。")
        tasks = [json.loads(call["messages"][1]["content"])["current_task"]["task_id"] for call in self.calls_for(client, SOLVER_PROMPT)]
        self.assertEqual(tasks, ["T1", "T2", "T3", "T4"])
        self.assertEqual(runtime.ledger.tasks["T2"].status, "superseded")
        self.assertEqual(runtime.ledger.tasks["T4"].objective, runtime.ledger.tasks["T2"].objective)
        self.assertEqual(result["final_response"], r"\boxed{5}")

    def test_downstream_error_reopens_ancestor_and_excludes_old_evidence(self):
        client = TextClient(
            solutions=["OLD_DOMAIN", "BAD_RESULT", "NEW_DOMAIN", "NEW_RESULT"],
            audits=[ACCEPT, REJECT, ACCEPT, ACCEPT, ACCEPT],
            replans=[{"route": "重新核查范围", "invalidate_task_ids": ["T1"]}],
        )
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算 2+3。")
        self.assertEqual(result["final_response"], r"\boxed{5}")
        final = json.loads(self.calls_for(client, FINALIZER_PROMPT)[0]["messages"][1]["content"])
        self.assertEqual([item["solution_id"] for item in final["accepted_results"]], ["S3", "S4"])
        self.assertNotIn("OLD_DOMAIN", json.dumps(final))
        self.assertNotIn("BAD_RESULT", json.dumps(final))
        self.assertEqual(runtime.ledger.tasks["T1"].accepted_solution_id, "S3")
        self.assertEqual(runtime.ledger.tasks["T3"].accepted_dependencies, (("T1", "S3"),))

    def test_final_audit_gap_returns_to_task_work_not_whole_problem_repair(self):
        client = TextClient(audits=[ACCEPT, ACCEPT, REPAIR, ACCEPT, ACCEPT], finals=[r"\boxed{6}", r"\boxed{5}"])
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算 2+3。")
        self.assertEqual(result["final_response"], r"\boxed{5}")
        self.assertEqual(len(self.calls_for(client, FINALIZER_PROMPT)), 2)
        replanner = json.loads(self.calls_for(client, REPLANNER_PROMPT)[0]["messages"][1]["content"])
        self.assertEqual(replanner["scope"], "final")
        self.assertEqual(replanner["target_task"]["task_id"], "T2")
        self.assertEqual(runtime.ledger.tasks["T2"].status, "superseded")

    def test_final_review_revokes_multiple_levels_of_accepted_descendants(self):
        plan = {"tasks": [
            {"objective": "确定定义域", "acceptance_criteria": ["范围完整"]},
            {"objective": "划分区间", "acceptance_criteria": ["划分完整"], "depends_on": [1]},
            {"objective": "统计结果", "acceptance_criteria": ["不重不漏"], "depends_on": [2]},
        ]}
        client = TextClient(
            plans=[plan], solutions=["OLD_DOMAIN", "OLD_INTERVALS", "OLD_COUNT", "NEW_DOMAIN", "NEW_INTERVALS", "NEW_COUNT"],
            audits=[ACCEPT, ACCEPT, ACCEPT, REJECT, ACCEPT, ACCEPT, ACCEPT, ACCEPT],
            replans=[{"route": "重新确认临界范围", "invalidate_task_ids": ["T1"]}],
        )
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算结果。")
        self.assertEqual(result["final_response"], r"\boxed{5}")
        finals = self.calls_for(client, FINALIZER_PROMPT)
        self.assertEqual(len(finals), 2)
        final = finals[-1]["messages"][1]["content"]
        for old in ["OLD_DOMAIN", "OLD_INTERVALS", "OLD_COUNT"]:
            self.assertNotIn(old, final)
        for new in ["NEW_DOMAIN", "NEW_INTERVALS", "NEW_COUNT"]:
            self.assertIn(new, final)
        invalidation = next(event for event in result["trace"] if event["type"] == "tasks_invalidated")
        self.assertEqual(invalidation["task_ids"], ["T1", "T2", "T3"])

    def test_stale_final_dependencies_prevent_submission(self):
        client = TextClient()
        runtime = TextReasoningRuntime(client, self.config(custom2_max_model_replans=0))
        original = client.chat

        def chat(**kwargs):
            response = original(**kwargs)
            payload = json.loads(kwargs["messages"][1]["content"])
            if kwargs["messages"][0]["content"] == AUDIT_PROMPT and payload["scope"] == "final":
                runtime.ledger.invalidate(["T1"])
            return response

        client.chat = chat
        result = runtime.run("计算 2+3。")
        self.assertIsNone(result["trace"][-1]["solution_id"])
        self.assertEqual(runtime.audits[-1].review.routing_status, "stale_final_dependencies")

    def test_failed_final_audit_never_returns_unverified_final_answer(self):
        client = TextClient(audits=[ACCEPT, ACCEPT, REJECT], finals=[r"\boxed{999}"])
        result = self.run_agent(client, custom2_max_model_replans=0)
        self.assertNotIn("999", result["final_response"])
        self.assertIsNone(result["trace"][-1]["solution_id"])

    def test_planning_failure_does_not_fall_back_to_solving_whole_problem(self):
        client = TextClient(plans=["not json", "not json"])
        result = self.run_agent(client)
        self.assertEqual(self.calls_for(client, SOLVER_PROMPT), [])
        self.assertEqual(self.calls_for(client, FINALIZER_PROMPT), [])
        self.assertEqual(result["trace"][-1]["stop_reason"], "plan_unavailable")

    def test_planner_rejects_forward_dependencies_and_can_retry(self):
        invalid = {"tasks": [
            {"objective": "前任务", "acceptance_criteria": ["成立"], "depends_on": [2]},
            {"objective": "后任务", "acceptance_criteria": ["成立"]},
        ]}
        client = TextClient(plans=[invalid, DEFAULT_PLAN])
        result = self.run_agent(client)
        self.assertEqual(result["final_response"], r"\boxed{5}")
        failure = next(event for event in result["trace"] if event["type"] == "control_response_invalid")
        self.assertEqual(failure["reason"], "invalid_dependency_order")

    def test_invalid_replan_cannot_mutate_accepted_tasks(self):
        invalid = {"route": "修改", "invalidate_task_ids": ["T99"]}
        client = TextClient(audits=[ACCEPT, REJECT], replans=[invalid, invalid])
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算 2+3。")
        self.assertTrue(runtime.ledger.is_current("T1"))
        self.assertEqual(list(runtime.ledger.tasks), ["T1", "T2"])
        self.assertIsNone(result["trace"][-1]["solution_id"])

    def test_strategy_preprocess_reuses_existing_skill_loader(self):
        skill = SelectedStrategySkill(
            "mathematical_analysis",
            "private/local/path",
            "STRATEGY_HINT",
        )
        client = TextClient()
        with patch("reasoning_agent.custom2.text_runtime.select_strategy_skills", return_value=[skill]) as loader:
            result = self.run_agent(client, enable_strategy_preprocess=True)
        loader.assert_called_once_with("mathematical_analysis", [], top_k=2)
        self.assertIn("STRATEGY_HINT", self.calls_for(client, PLANNER_PROMPT)[0]["messages"][1]["content"])
        self.assertNotIn("STRATEGY_HINT", json.dumps(result))
        self.assertNotIn("private/local/path", json.dumps(client.calls))

    def test_numeric_disagreement_blocks_task_acceptance(self):
        client = TextClient(solutions=["计算 $7*8=55$。", "计算 $7*8=56$。", "本任务结论：完成计算。"], finals=[r"\boxed{56}"])
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算 7*8。")
        self.assertEqual(result["final_response"], r"\boxed{56}")
        self.assertEqual(runtime.ledger.tasks["T1"].accepted_solution_id, "S2")
        first = next(event for event in result["trace"] if event["type"] == "draft_audited")
        self.assertEqual(first["routing_status"], "program_disagreement")
        self.assertNotIn("7*8", json.dumps(result))

    def test_auditor_can_request_program_check_before_accepting_task(self):
        request = "检查组合数。\n```check\ncomb(9,3)\n```"
        client = TextClient(audits=[request, ACCEPT])
        result = self.run_agent(client)
        audit_calls = self.calls_for(client, AUDIT_PROMPT)
        self.assertIn("comb(9,3) -> 84", audit_calls[1]["messages"][-1]["content"])
        self.assertEqual(result["trace"][-1]["tool_call_count"], 1)
        self.assertEqual(result["final_response"], r"\boxed{5}")

    def test_program_checks_remain_bound_to_the_task_draft(self):
        client = TextClient(solutions=["计算 $7*8=56$。", "本任务结论成立。"])
        self.run_agent(client)
        audits = self.calls_for(client, AUDIT_PROMPT)
        second = json.loads(audits[1]["messages"][1]["content"])
        self.assertIn("未执行", second["program_checks"])
        self.assertIn("7*8", second["accepted_results"][0]["program_checks"])

    def test_final_program_disagreement_cannot_bypass_verified_task_gate(self):
        client = TextClient(finals=[r"$\boxed{7*8=55}$"])
        result = self.run_agent(client, custom2_max_model_replans=0)
        self.assertIsNone(result["trace"][-1]["solution_id"])
        final_audit = [event for event in result["trace"] if event["type"] == "draft_audited"][-1]
        self.assertEqual(final_audit["routing_status"], "program_disagreement")

    def test_false_probe_does_not_automatically_refute_task(self):
        client = TextClient(solutions=["```check\nall(value%2==0 for value in range(6))\n```\n本任务结论：存在奇数。"])
        result = self.run_agent(client)
        self.assertEqual(result["trace"][-1]["review_status"], "accept")

    def test_tool_budget_and_disable_switch(self):
        for settings, count in [({"max_tool_calls": 1}, 1), ({"custom2_text_program_checks": False}, 0)]:
            with self.subTest(settings=settings):
                client = TextClient(solutions=["```check\n1+2\n2+3\n```\n本任务结论：成立。"])
                result = self.run_agent(client, **settings)
                self.assertEqual(result["trace"][-1]["tool_call_count"], count)

    def test_uncertain_review_repairs_current_task_without_format_retry(self):
        feedback = "尚缺边界讨论，但未给固定结论标记。"
        client = TextClient(audits=[feedback, ACCEPT])
        result = self.run_agent(client)
        self.assertEqual(result["final_response"], r"\boxed{5}")
        self.assertIn(feedback, self.calls_for(client, REPAIR_PROMPT)[0]["messages"][1]["content"])
        self.assertFalse(any(event["type"] == "control_response_invalid" for event in result["trace"]))

    def test_truncated_task_cannot_be_committed(self):
        client = TextClient(solutions=[{"content": "未完成的子结论", "finish_reason": "length"}])
        result = self.run_agent(client, custom2_max_repairs=0, custom2_max_model_replans=0)
        self.assertEqual(self.calls_for(client, AUDIT_PROMPT), [])
        self.assertEqual(self.calls_for(client, FINALIZER_PROMPT), [])
        self.assertIsNone(result["trace"][-1]["solution_id"])

    def test_empty_task_can_be_repaired_but_never_accepted_directly(self):
        client = TextClient(solutions=["", "已补全当前子任务。"])
        result = self.run_agent(client)
        self.assertEqual(result["trace"][-1]["repair_count"], 1)
        self.assertEqual(result["final_response"], r"\boxed{5}")

    def test_audit_transport_failure_does_not_unlock_dependencies(self):
        client = TextClient(audits=[RuntimeError("sk-secret /private/path"), ACCEPT])
        result = self.run_agent(client)
        self.assertEqual(result["trace"][-1]["repair_count"], 1)
        self.assertNotIn("sk-secret", json.dumps(result))
        self.assertNotIn("/private/path", json.dumps(result))

    def test_solver_transport_failure_keeps_accepted_work_but_does_not_finalize(self):
        client = TextClient(solutions=["FIRST_GOOD", RuntimeError("private")])
        runtime = TextReasoningRuntime(client, self.config())
        result = runtime.run("计算 2+3。")
        self.assertTrue(runtime.ledger.is_current("T1"))
        self.assertEqual(self.calls_for(client, FINALIZER_PROMPT), [])
        self.assertIsNone(result["trace"][-1]["solution_id"])

    def test_replan_local_cap_can_extend_with_global_budget(self):
        client = TextClient(audits=[REJECT, ACCEPT])
        result = self.run_agent(client, custom2_max_model_replans=0, custom2_text_budget_recovery=True)
        self.assertEqual(result["final_response"], r"\boxed{5}")
        self.assertTrue(any(event["type"] == "route_budget_extended" for event in result["trace"]))

    def test_global_solver_limit_prevents_unbounded_replanning(self):
        client = TextClient(audits=[REJECT] * 8)
        result = self.run_agent(client, custom2_max_solver_calls=2, custom2_text_budget_recovery=True)
        self.assertEqual(result["trace"][-1]["solver_call_count"], 2)
        self.assertEqual(self.calls_for(client, FINALIZER_PROMPT), [])
        self.assertEqual(result["trace"][-1]["stop_reason"], "solver_budget")

    def test_replan_extension_respects_convergence_time(self):
        client = TextClient(audits=[REJECT])
        result = self.run_agent(client, custom2_max_model_replans=0, custom2_text_budget_recovery=True, custom2_total_budget_seconds=400)
        self.assertEqual(self.calls_for(client, REPLANNER_PROMPT), [])
        self.assertEqual(result["trace"][-1]["stop_reason"], "route_budget")

    def test_model_budget_reserves_two_calls_for_finalization(self):
        client = TextClient()
        result = self.run_agent(client, max_model_calls=8)
        self.assertEqual(len(client.calls), 8)
        self.assertEqual(result["final_response"], r"\boxed{5}")
        client = TextClient()
        result = self.run_agent(client, max_model_calls=7)
        self.assertLessEqual(len(client.calls), 7)
        self.assertEqual(self.calls_for(client, FINALIZER_PROMPT), [])
        self.assertIsNone(result["trace"][-1]["solution_id"])

    def test_tiny_time_budget_starts_no_model_calls(self):
        client = TextClient()
        result = self.run_agent(client, custom2_total_budget_seconds=1)
        self.assertEqual(client.calls, [])
        self.assertTrue(result["final_response"])

    def test_finalizer_can_use_reserved_time_after_all_tasks_pass(self):
        client = TextClient()
        runtime = TextReasoningRuntime(client, self.config())
        original = client.chat

        def chat(**kwargs):
            result = original(**kwargs)
            payload = json.loads(kwargs["messages"][1]["content"])
            if kwargs["messages"][0]["content"] == AUDIT_PROMPT and payload["scope"] == "task" and payload["current_task"]["task_id"] == "T2":
                runtime.state.deadline_at = time.monotonic() + 30
            return result

        client.chat = chat
        result = runtime.run("计算 2+3。")
        self.assertEqual(result["final_response"], r"\boxed{5}")

    def test_finalizer_only_gets_current_accepted_subresults(self):
        client = TextClient(solutions=["UNAPPROVED", "APPROVED", "SECOND_APPROVED"], audits=[REPAIR, ACCEPT])
        result = self.run_agent(client)
        content = self.calls_for(client, FINALIZER_PROMPT)[0]["messages"][1]["content"]
        self.assertNotIn("UNAPPROVED", content)
        self.assertIn("APPROVED", content)
        self.assertEqual(result["final_response"], r"\boxed{5}")

    def test_complete_proof_is_assembled_only_at_final_stage(self):
        proof = "证明：由乘法定义，任意实数 x 满足 x+x=2x。"
        client = TextClient(finals=[proof])
        result = TextReasoningRuntime(client, self.config()).run("证明任意实数 x 满足 x+x=2x。", None)
        self.assertEqual(result["final_response"], proof)
        self.assertEqual(self.calls_for(client, EXTRACTOR_PROMPT), [])
        self.assertEqual(len(client.calls), 8)

    def test_verbose_final_output_uses_source_extraction(self):
        def extract(payload):
            return {"solution_id": payload["solution_id"], "paragraph_id": payload["paragraphs"][-1]["id"], "answer": "5"}

        client = TextClient(finals=["Thus, the answer needs presentation.\n\n结果为 5。"], extractions=[extract])
        result = self.run_agent(client)
        self.assertEqual(result["final_response"], r"\boxed{5}")
        self.assertEqual(len(self.calls_for(client, EXTRACTOR_PROMPT)), 1)

    def test_invalid_final_extraction_never_returns_derivation(self):
        client = TextClient(finals=["Thus, we need another argument."], extractions=[{
            "solution_id": "S3", "paragraph_id": "S3:P1", "answer": "INVENTED",
        }])
        result = self.run_agent(client, custom2_max_model_replans=0)
        self.assertNotIn("Thus", result["final_response"])
        self.assertNotIn("INVENTED", result["final_response"])
        self.assertIsNone(result["trace"][-1]["solution_id"])

    def test_bad_profile_can_fall_back_without_skipping_planning(self):
        client = TextClient(profile="not json")
        result = self.run_agent(client)
        self.assertEqual(result["final_response"], r"\boxed{5}")
        self.assertEqual(len(self.calls_for(client, PLANNER_PROMPT)), 1)

    def test_thinking_only_changes_subtask_math_calls(self):
        for mode in ["false", "true", "default"]:
            with self.subTest(mode=mode):
                client = TextClient()
                self.run_agent(client, custom2_text_thinking_mode=mode)
                for call in client.calls:
                    if call["messages"][0]["content"] == SOLVER_PROMPT:
                        if mode == "default":
                            self.assertNotIn("thinking_mode", call)
                        else:
                            self.assertEqual(call["thinking_mode"], mode == "true")
                    else:
                        self.assertFalse(call["thinking_mode"])

    def test_metadata_and_raw_feedback_never_leak_to_platform_diagnostics(self):
        client = TextClient(audits=["RAW_REVIEW_SECRET\n审核结论：修复", ACCEPT])
        result = TextReasoningRuntime(client, self.config()).run("计算 2+3。", {"answer": "HIDDEN_REFERENCE", "api_key": "sk-private"})
        for forbidden in ["RAW_REVIEW_SECRET", "HIDDEN_REFERENCE", "sk-private", "本任务结论"]:
            self.assertNotIn(forbidden, json.dumps(result))
        self.assertNotIn("HIDDEN_REFERENCE", json.dumps(client.calls))

    def test_diagnostics_remain_bounded_and_can_be_disabled(self):
        result = self.run_agent(TextClient(), max_trace_chars=900)
        for key in ["trace", "debug_trace"]:
            self.assertLessEqual(len(json.dumps(result[key], ensure_ascii=False)), 900)
        self.assertEqual(result["trace"][-1]["type"], "solution_selected")
        self.assertNotIn("debug_trace", self.run_agent(TextClient(), emit_debug_trace=False))

    def test_reused_runtime_resets_tasks_and_versions(self):
        client = TextClient()
        runtime = TextReasoningRuntime(client, self.config())
        runtime.run("计算 2+3。")
        runtime.run("计算 2+3。")
        self.assertEqual(list(runtime.ledger.tasks), ["T1", "T2"])
        self.assertEqual(len(runtime.drafts), 3)
        self.assertEqual(runtime.state.model_call_count, 8)

    def test_minimal_official_client_signature_supports_subtasks_and_checks(self):
        backing = TextClient(solutions=["计算 $7*8=56$。", "子任务结论成立。"], finals=[r"\boxed{56}"])

        class MinimalClient:
            def chat(self, messages, temperature, max_tokens):
                return backing.chat(messages=messages, temperature=temperature, max_tokens=max_tokens)

        result = self.run_agent(MinimalClient())
        self.assertEqual(result["final_response"], r"\boxed{56}")
        self.assertEqual(result["trace"][-1]["tool_call_count"], 1)

    def test_config_switches_and_legacy_default_remain_available(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(AgentConfig().custom2_solver_protocol, "json")
            self.assertTrue(AgentConfig().custom2_text_program_checks)
        with patch.dict("os.environ", {"CUSTOM2_TEXT_PROGRAM_CHECKS": "false", "CUSTOM2_TEXT_BUDGET_RECOVERY": "false"}):
            self.assertFalse(AgentConfig().custom2_text_program_checks)
            self.assertFalse(AgentConfig().custom2_text_budget_recovery)
        with self.assertRaises(ValueError):
            Custom2Agent(TextClient(), replace(AgentConfig(), custom2_solver_protocol="bad"))
        with self.assertRaises(ValueError):
            TextReasoningRuntime(TextClient(), self.config(custom2_text_thinking_mode="bad"))


if __name__ == "__main__":
    unittest.main()
