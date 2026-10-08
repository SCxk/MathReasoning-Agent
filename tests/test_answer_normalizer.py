import unittest

from reasoning_agent.custom.parsers.answer_normalizer import (
    AnswerMatcher,
    detect_question_mode,
    format_answer_for_output,
    normalize_objective_answer,
    objective_answer_is_usable,
    sanitize_boxed_answer_text,
)
from reasoning_agent.custom.parsers.final_answer_parser import normalize_final_response
from reasoning_agent.custom.prompts.system import SYSTEM_PROMPT
from reasoning_agent.custom2.prompts import (
    CANDIDATE_SET_VERIFIER_PROMPT,
    EMERGENCY_FINALIZER_PROMPT,
    FINALIZER_PROMPT,
    SOLVER_SYSTEM_PROMPT,
)


class ObjectiveAnswerNormalizerTest(unittest.TestCase):
    def test_choice_extracts_last_box_and_canonicalizes_multiple_options(self) -> None:
        answer = "分析略。最终可得 \\boxed{Ａ、C、Ａ}；依据：逐项验证"
        self.assertEqual(normalize_objective_answer(answer, "choice"), "A、C")

    def test_choice_problem_returns_short_unboxed_answer(self) -> None:
        problem = "单项选择题：\nA. 1\nB. 2\nC. 3\nD. 4"
        self.assertEqual(
            normalize_final_response("最终答案：B，因为计算可得", problem=problem),
            "B",
        )

    def test_judgment_checks_negative_phrase_before_positive_substring(self) -> None:
        self.assertEqual(normalize_objective_answer("答案：不正确", "judgment"), "错误")
        self.assertEqual(normalize_objective_answer("\\boxed{√}", "judgment"), "正确")

    def test_fill_blank_rejects_uncertain_or_thought_fragment(self) -> None:
        self.assertFalse(objective_answer_is_usable("无法判断", "fill_blank"))
        self.assertFalse(
            objective_answer_is_usable("分析 我们需要先计算", "fill_blank")
        )
        self.assertTrue(objective_answer_is_usable("\\frac{1}{2}", "fill_blank"))

    def test_mode_detection_does_not_treat_choose_verb_as_choice_question(self) -> None:
        problem = "从五个正数中选择四个不同的数，证明存在一组满足条件。"
        self.assertEqual(detect_question_mode(problem), "proof")


class ComputationAnswerMatcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matcher = AnswerMatcher()

    def test_structured_assignments_are_order_independent(self) -> None:
        result = self.matcher._match_computation_detailed(
            "a=1；b=2", "b=2；a=1"
        )
        self.assertTrue(result.matched)
        self.assertEqual(result.method, "structured")

    def test_float_and_latex_fraction_are_equivalent(self) -> None:
        self.assertTrue(self.matcher.match_answers("\\frac{1}{2}", "0.5"))

    def test_compact_constants_and_radicals_are_equivalent(self) -> None:
        self.assertTrue(self.matcher.match_answers("2π√2", "2*pi*sqrt(2)"))

    def test_free_variable_expressions_are_equivalent(self) -> None:
        self.assertTrue(self.matcher.match_answers("x+x", "2*x"))
        self.assertFalse(self.matcher.match_answers("x+x", "3*x"))

    def test_unusable_answer_does_not_match(self) -> None:
        result = self.matcher._match_computation_detailed("不确定", "2")
        self.assertFalse(result.matched)
        self.assertEqual(result.method, "unusable")


class FinalOutputFormattingTest(unittest.TestCase):
    def test_boxed_description_prefix_is_removed(self) -> None:
        answer = (
            'Therefore, \\boxed{Thus the answer is '
            'f(a)=22\\lfloor a/30\\rfloor+g(a\\bmod 30)}"'
        )
        self.assertEqual(
            sanitize_boxed_answer_text(answer),
            "Therefore, \\boxed{f(a)=22\\lfloor a/30\\rfloor+g(a\\bmod 30)}",
        )

    def test_chinese_description_inside_box_is_removed(self) -> None:
        self.assertEqual(
            sanitize_boxed_answer_text("\\boxed{最终答案为 42}"),
            "\\boxed{42}",
        )

    def test_proof_keeps_complete_reasoning_and_removes_outer_label(self) -> None:
        proof = "最终答案：先证明引理。\n再应用引理。\n故命题成立。"
        self.assertEqual(
            normalize_final_response(proof, problem="证明：命题成立", problem_type="proof"),
            "先证明引理。\n再应用引理。\n故命题成立。",
        )

    def test_computation_keeps_derivation_when_box_is_present(self) -> None:
        answer = "由等式两边相减，得到唯一解。\n\\boxed{x=2}"
        self.assertEqual(
            normalize_final_response(answer, problem="求方程的解", problem_type="equation"),
            answer,
        )

    def test_simple_computation_is_sympy_canonicalized(self) -> None:
        self.assertEqual(format_answer_for_output("2^3", "computation"), "8")

    def test_python_literal_is_made_readable(self) -> None:
        self.assertEqual(
            format_answer_for_output("{'a': 1, 'b': 2}"),
            "a=1；b=2",
        )

    def test_answer_prompts_require_value_only_boxes_and_function_x(self) -> None:
        for prompt in (
            SYSTEM_PROMPT,
            SOLVER_SYSTEM_PROMPT,
            CANDIDATE_SET_VERIFIER_PROMPT,
            FINALIZER_PROMPT,
            EMERGENCY_FINALIZER_PROMPT,
        ):
            self.assertIn("f(x)", prompt)
        self.assertIn("Thus the answer is", FINALIZER_PROMPT)
        self.assertIn("解释和推导全部放在 box 外", FINALIZER_PROMPT)


if __name__ == "__main__":
    unittest.main()
