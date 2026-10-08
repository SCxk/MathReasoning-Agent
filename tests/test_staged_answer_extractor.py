import unittest

from reasoning_agent.custom2.staged_answer_extractor import (
    extract_staged_answer,
    render_staged_response,
)


class StagedAnswerExtractorTest(unittest.TestCase):
    def test_extracts_single_boxed_answer_section(self) -> None:
        result = extract_staged_answer(
            "## 问题分析\n...\n## 详细解题步骤\n...\n"
            "## 最终答案\n\\boxed{20460}\n## 关键验证点\n..."
        )
        self.assertEqual(result.answer, r"\boxed{20460}")

    def test_preserves_multiple_boxed_items(self) -> None:
        result = extract_staged_answer(
            "## 最终答案\n(1) \\boxed{a}\n(2) \\boxed{b}\n## 关键验证点\n..."
        )
        self.assertEqual(result.answer, "\\boxed{a}\n\\boxed{b}")

    def test_rejects_placeholder(self) -> None:
        result = extract_staged_answer("## 最终答案\n见上文\n## 关键验证点\n...")
        self.assertIsNone(result.answer)
        self.assertEqual(result.reason, "placeholder_final_answer")

    def test_rejects_unbalanced_latex(self) -> None:
        result = extract_staged_answer(
            "## 最终答案\n\\boxed{\\frac{1}{2}\n## 关键验证点\n..."
        )
        self.assertIsNone(result.answer)
        self.assertEqual(result.reason, "malformed_latex")

    def test_wraps_unboxed_answer_text(self) -> None:
        result = extract_staged_answer("## 最终答案\nA\n## 关键验证点\n...")
        self.assertEqual(result.answer, r"\boxed{A}")

    def test_recovers_boxed_answer_from_truncated_response(self) -> None:
        result = extract_staged_answer("推导尚未结束，但当前候选为\\boxed{2025}")
        self.assertEqual(result.answer, r"\boxed{2025}")
        self.assertEqual(result.reason, "unsectioned_answer")

    def test_recovers_explicit_answer_line_without_sections(self) -> None:
        result = extract_staged_answer("分析省略。\n最终答案：A")
        self.assertEqual(result.answer, r"\boxed{A}")

    def test_proof_renderer_keeps_proof_and_removes_internal_check_block(self) -> None:
        draft = (
            "## 问题分析\n命题。\n## 详细解题步骤\n"
            "步骤 1｜目标：证明\n由定义得出结论。\n"
            "```check\n{\"ok\": false}\n```\n"
            "## 最终答案\n命题成立。\n## 关键验证点\n边界已核对。"
        )

        rendered = render_staged_response(draft, "proof")

        self.assertIn("## 详细解题步骤", rendered)
        self.assertIn("由定义得出结论", rendered)
        self.assertIn("## 最终答案", rendered)
        self.assertIn("命题成立", rendered)
        self.assertNotIn("```check", rendered)

    def test_choice_renderer_collects_complete_option_set(self) -> None:
        draft = "## 最终答案\n(1) \\boxed{A}\n(2) \\boxed{C}\n## 关键验证点\n逐项检查。"

        self.assertEqual(render_staged_response(draft, "choice"), r"\boxed{AC}")

    def test_judgment_renderer_normalizes_final_value(self) -> None:
        draft = "## 最终答案\n结论：正确\n## 关键验证点\n代回成立。"

        self.assertEqual(render_staged_response(draft, "judgment"), r"\boxed{正确}")
