"""Generic malformed/truncated-output cases, separate from protected user tests."""

import pytest

from reasoning_agent.custom2 import staged_answer_extractor as extractor


@pytest.mark.parametrize("text", ["{", "}", "$x", r"\(x", r"\[x"])
def test_unbalanced_latex_is_not_recovered(text):
    assert not extractor._balanced_latex(text)
    assert extractor.extract_staged_answer("## 最终答案\n" + text).answer is None


def test_answer_label_only_and_unknown_choice_are_not_invented():
    assert extractor.extract_staged_answer("## 最终答案\n答案").answer is None
    assert extractor.render_staged_response("## 最终答案\nZ", "choice") == r"\boxed{Z}"
    assert extractor._objective_value("AB", "choice") == "AB"
    assert extractor._boxed_content("no group") == "no group"
    assert extractor._boxed_content("{missing close") == "{missing close"


def test_invalid_fallbacks_and_balanced_group_edges():
    assert extractor.extract_staged_answer(r"\boxed{unknown}").answer is None
    assert extractor.extract_staged_answer("Answer: unknown\nAnswer: $broken").answer is None
    assert extractor.extract_staged_answer(r"\boxed{missing").answer is None
    assert extractor._balanced_group_end("", 0) is None
    assert extractor._balanced_group_end("x}", 0) is None
    assert extractor._balanced_group_end("{{x}}", 0) == 5
    assert extractor._balanced_group_end(r"{x\}y}", 0) == 6
    assert not extractor._escaped("x", 0)
    assert extractor._has_placeholder(" \n")
    assert extractor._clean_lines(" ; \nresult\n ;") == "result"
