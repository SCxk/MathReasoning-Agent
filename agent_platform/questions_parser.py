"""Conservative, deterministic question boundaries; no model or answer inference."""

import re
from pathlib import Path

from markdown_it import MarkdownIt
from pydantic import Field

from agent_platform.rag.models import MAX_TEXT
from agent_platform.rag.parser import ParseRejected
from agent_platform.safety import sanitize_text
from agent_platform.tools.schemas import DTO
from agent_platform.presentation import QUESTION_INSTRUCTION_KEY


MAX_QUESTIONS = 20
SOURCE_KEY = "_question_source"
INSTRUCTION_KEY = QUESTION_INSTRUCTION_KEY
QUESTION = re.compile(r"^(?:第\s*[0-9一二三四五六七八九十百]+\s*题|(?:题目|问题|Question|Problem|Q)\s*\d+)\s*[.、:：)）]?", re.I)
NUMBER = re.compile(r"^\s{0,3}(\d{1,3})\s*[.、:：)）]\s*(?=\S)")
ANSWER = re.compile(r"^(?:参考)?(?:答案|解答|解析)|^(?:Answer|Solution)\b", re.I)


class Question(DTO):
    number: int = Field(ge=1, le=MAX_QUESTIONS)
    label: str = Field(min_length=1, max_length=200)
    problem: str = Field(min_length=1, max_length=24000)
    page_start: int | None = Field(default=None, ge=1, le=500)
    page_end: int | None = Field(default=None, ge=1, le=500)


class QuestionDocument(DTO):
    questions: list[Question] = Field(min_length=1, max_length=MAX_QUESTIONS)
    split_method: str
    page_count: int | None = None


def split_questions(pages: list[str], *, pdf=False) -> QuestionDocument:
    if sum(map(len, pages)) > MAX_TEXT:
        raise ParseRejected("text_limit")
    lines, provenance = [], []
    for page, text in enumerate(pages, 1):
        current = text.splitlines()
        lines.extend(current + [""])
        provenance.extend([page] * (len(current) + 1))
    text = "\n".join(lines)
    if not text.strip():
        raise ParseRejected("no_extractable_text")
    if "\ufffd" in text:
        raise ParseRejected("unreliable_question_text")
    tokens = MarkdownIt().parse(text)
    protected: set[int] = set()
    headings = []
    list_items = []
    for token in tokens:
        if token.type in {"fence", "code_block", "html_block"} and token.map:
            protected.update(range(*token.map))
        if token.type == "heading_open" and token.map:
            headings.append((token.map[0], int(token.tag[1:])))
        if token.type == "list_item_open" and token.level == 1 and token.map:
            list_items.append(token.map[0])
    # Markdown's block parser protects code; display mathematics needs its own bounds.
    math_open = None
    for index, line in enumerate(lines):
        if index in protected:
            continue
        if math_open:
            protected.add(index)
            if math_open in line:
                math_open = None
        elif "$$" in line or r"\[" in line:
            protected.add(index)
            marker = "$$" if "$$" in line else r"\]"
            opening = "$$" if marker == "$$" else r"\["
            if marker not in line.split(opening, 1)[1]:
                math_open = marker
    if math_open:
        raise ParseRejected("unclosed_formula_or_fence")
    for token in tokens:
        if token.type == "fence" and token.map and not re.search(r"^\s*(```+|~~~+)\s*$", lines[token.map[1] - 1]):
            raise ParseRejected("unclosed_formula_or_fence")
    candidates = []
    labels = []
    heading_levels = dict(headings)
    for index, line in enumerate(lines):
        if index in protected:
            continue
        title = re.sub(r"^\s{0,3}#{1,6}\s+", "", line).strip()
        if (index in heading_levels and ANSWER.match(title)) or re.match(
                r"^(?:参考)?(?:答案|解答|解析)\s*[:：]|^(?:Answer|Solution)\s*:", title, re.I):
            raise ParseRejected("question_file_contains_solutions")
        match = QUESTION.match(title)
        if match:
            candidates.append((index, title[:200], heading_levels.get(index, 0)))
            labels.append(re.sub(r"\s+", "", match[0]).casefold())
    method = "question_labels"
    if candidates:
        levels = {row[2] for row in candidates}
        if len(levels) > 1 or len(set(labels)) != len(labels):
            raise ParseRejected("ambiguous_question_structure")
    else:
        method = "numbered"
        for index, line in enumerate(lines):
            if index in protected:
                continue
            # Nested ordered lists are subparts, never separate questions.
            number_match = NUMBER.match(line)
            if number_match and (index in list_items or not re.match(r"^\s*\d+\.\s", line)):
                candidates.append((index, number_match.group(0).strip()[:200], 0))
        if not candidates:
            if len(headings) > 1:
                raise ParseRejected("ambiguous_question_structure")
            candidates = [(0, "1", 0)]
            method = "single"
    if len(candidates) > MAX_QUESTIONS:
        raise ParseRejected("too_many_questions")
    if method == "numbered":
        numbers = []
        for row in candidates:
            number_match = NUMBER.match(lines[row[0]])
            assert number_match is not None
            numbers.append(int(number_match.group(1)))
        if numbers != sorted(set(numbers)):
            raise ParseRejected("ambiguous_question_structure")
    common = "\n".join(lines[:candidates[0][0]]).strip()
    questions = []
    for ordinal, (start, label, _) in enumerate(candidates, 1):
        end = candidates[ordinal][0] if ordinal < len(candidates) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        meaningful = re.sub(r"^\s{0,3}#{1,6}\s+", "", lines[start]).strip()
        tail = QUESTION.sub("", meaningful).strip() if method == "question_labels" else NUMBER.sub("", meaningful).strip()
        if not tail and not any(line.strip() for line in lines[start + 1:end]):
            raise ParseRejected("empty_question")
        problem = sanitize_text((common + "\n\n" if common else "") + body)
        if len(problem) > 24000:
            raise ParseRejected("question_too_long")
        occupied = [index for index in range(start, end) if lines[index].strip()]
        questions.append(Question(number=ordinal, label=label, problem=problem,
            page_start=provenance[occupied[0]] if pdf else None,
            page_end=provenance[occupied[-1]] if pdf else None))
    return QuestionDocument(questions=questions, split_method=method, page_count=len(pages) if pdf else None)


def parse_questions(path: Path, media_type: str) -> QuestionDocument:
    if media_type == "text/markdown":
        try:
            return split_questions([path.read_text(encoding="utf-8-sig")])
        except UnicodeError:
            raise ParseRejected("invalid_utf8") from None
    from pypdf import PdfReader
    reader = PdfReader(path, strict=True)
    if reader.is_encrypted:
        raise ParseRejected("encrypted_pdf")
    if len(reader.pages) > 500:
        raise ParseRejected("page_limit")
    pages = [page.extract_text() or "" for page in reader.pages]
    if any(not text.strip() for text in pages) and any(text.strip() for text in pages):
        raise ParseRejected("incomplete_pdf_text")
    return split_questions(pages, pdf=True)
