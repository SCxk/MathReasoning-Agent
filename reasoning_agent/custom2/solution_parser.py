import re

from reasoning_agent.custom.parsers.answer_normalizer import (
    detect_question_mode,
    normalize_objective_answer,
    objective_answer_is_usable,
)
from reasoning_agent.custom2.strategy_skills import normalize_skill_category
from reasoning_agent.custom2.text_models import (
    AnswerExtraction, Paragraph, ProblemProfile, SolutionDraft, TextCandidate,
)


_FINAL_MARKER = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?(?:\*\*)?"
    r"(?:最终答案|最终结论|final[ \t]+answer|final|answer)"
    r"(?:\*\*)?[ \t]*(?:[:：][ \t]*(?:\*\*)?|(?=\n|$))",
    re.IGNORECASE | re.MULTILINE,
)
_FOOTER = re.compile(r"^[ \t]*(?:CONFIDENCE|置信度)\s*[:：].*$", re.MULTILINE | re.IGNORECASE)
_BOX_MARKER = re.compile(r"\\boxed\s*\{")


def _fallback_domain(problem: str) -> str:
    """Conservatively route clear subject cues when model classification is unusable."""
    subject_patterns = (
        (
            "abstract_algebra",
            r"max[- ]plus|tropical algebra|componentwise (?:maximum|max)|"
            r"integer[- ]valued\s+\d+[- ]tuples?[\s\S]{0,1200}(?:addition|\bmax\b)|"
            r"逐分量取大|整数值.{0,80}元组.{0,120}(?:加法|取大)",
        ),
        (
            "advanced_olympiad_mathematics",
            r"\bn[- ]good function\b|\bexotic integer\b|"
            r"divides?\s+\w+\^|整除.{0,100}(?:函数|整数)|"
            r"数论|正整数.{0,100}函数",
        ),
        ("probability", r"\bprobabilit(?:y|ies)\b|随机变量|概率"),
        ("statistical_inference", r"\b(?:hypothesis test|confidence interval|estimator)\b|统计推断|置信区间"),
        ("linear_algebra", r"\b(?:matrix|matrices|eigenvalue|vector space)\b|矩阵|特征值|向量空间"),
        ("abstract_algebra", r"\b(?:group|ring|field)\s+(?:homomorphism|isomorphism|ideal|extension)\b|群同态|环同态|域扩张"),
        ("complex_analysis", r"\b(?:holomorphic|meromorphic|residue theorem|complex analytic)\b|全纯|亚纯|留数"),
        ("ordinary_differential_equations", r"\b(?:ordinary differential equation|initial value problem)\b|常微分方程|初值问题"),
        ("partial_differential_equations", r"\bpartial differential equation\b|偏微分方程"),
        ("topology", r"\b(?:topological space|fundamental group|homotopy|homeomorphism)\b|拓扑空间|基本群|同伦"),
        (
            "advanced_olympiad_mathematics",
            r"\b(?:triangle|angle|circle|circumcircle|incircle|polygon|collinear|convex hull|"
            r"functional equation|polynomial identity)\b|"
            r"\bfunction\b[\s\S]{0,400}\bfor all\b|\\prod(?:\s|_|\{)|"
            r"三角形|角度|圆|共线|凸包|函数方程|多项式恒等式|函数[\s\S]{0,120}(?:任意|所有)",
        ),
        (
            "combinatorics",
            r"\b(?:how many|permutations?|domino(?:es)?|til(?:e|ing)|chessboard|hamilton(?:ian)?|"
            r"graph|coloring|independent set|matching|fibonacci|lucas|difference set)\b|"
            r"排列|多米诺|棋盘|染色|哈密顿|图论|组合计数|差集|斐波那契",
        ),
    )
    for category, pattern in subject_patterns:
        if re.search(pattern, problem, re.I):
            return category
    return "unknown"


def _resolve_domain(problem: str, proposed: ProblemProfile | None) -> str:
    proposed_domain = normalize_skill_category(proposed.domain if proposed else "unknown")
    fallback_domain = _fallback_domain(problem)
    if proposed_domain == "unknown":
        return (
            fallback_domain
            if fallback_domain != "unknown"
            else "advanced_olympiad_mathematics"
        )
    # Strong structural cues override a broad model label.  These problems
    # are routinely mislabelled as combinatorics even though their operations
    # live in an algebraic structure or their core is number theory.
    if fallback_domain in {"abstract_algebra", "advanced_olympiad_mathematics"}:
        if re.search(
            r"max[- ]plus|tropical algebra|逐分量取大|整数值.{0,80}元组.{0,120}(?:加法|取大)|"
            r"integer[- ]valued\s+\d+[- ]tuples?[\s\S]{0,1200}(?:addition|\bmax\b)",
            problem,
            re.I,
        ):
            return "abstract_algebra"
        if re.search(
            r"\bn[- ]good function\b|\bexotic integer\b|数论|整除.{0,100}(?:函数|整数)",
            problem,
            re.I,
        ):
            return "advanced_olympiad_mathematics"
    # These strong cues distinguish olympiad geometry/algebra from a model's
    # overly broad combinatorics label without second-guessing specialist labels.
    if proposed_domain == "combinatorics" and fallback_domain == "advanced_olympiad_mathematics":
        return fallback_domain
    return proposed_domain


def infer_profile(problem: str, proposed: ProblemProfile | None = None) -> ProblemProfile:
    detected = detect_question_mode(problem)
    explicit_proof = bool(re.search(
        r"(?:^|[.?!。！？,，;；\n])\s*(?:\(?\d+\)?[.)、]?\s*)?(?:please\s+)?(?:prove|show|demonstrate|establish)\b|"
        r"\band\s+(?:prove|show)\b|(?:^|[。！？,，;；\n])\s*(?:请|试)?(?:证明|求证)", problem, re.I,
    ))
    if detected == "proof" and not explicit_proof:
        detected = "other"
    if detected == "other" and explicit_proof:
        detected = "proof"
    if detected == "other" and re.search(r"[（(]\s*[）)]|填空|fill\s+in", problem, re.I):
        detected = "fill_blank"
    mode = proposed.answer_mode if proposed else detected
    if mode == "choice" and detected != "choice":
        mode = "other"
    if mode == "proof" and detected != "proof":
        mode = "other"
    if detected == "other" and re.search(
        r"\b(?:compute|calculate|determine|find)\b|\bhow\s+many\b|\bwhat\s+(?:is|are)\b|求值|求所有|求最|计算|多少", problem, re.I
    ):
        mode = "computation"
    if detected in {"choice", "proof", "judgment", "fill_blank"}:
        mode = detected
    domain = _resolve_domain(problem, proposed)
    # Ignore answer choices when detecting optimization words; e.g. the
    # option "最小二乘法" is not a minimum-value problem.
    problem_stem = re.split(r"(?:^|\n)\s*[A-D][.、)]", problem, maxsplit=1)[0]
    obligations = list(proposed.obligations) if proposed else []
    # The classifier is allowed to suggest obligations, but lexical evidence
    # from the problem is authoritative.  In particular, a choice question
    # must not inherit lower-bound/construction obligations hallucinated by a
    # generic strategy prompt (which otherwise makes a simple item high-risk).
    has_minimum = bool(re.search(
        r"\b(?:minimum|minimal|smallest)\b|(?<!at )\bleast\b|最小|最少", problem_stem, re.I
    ))
    has_maximum = bool(re.search(
        r"\b(?:maximum|maximal|largest|greatest)\b|最大|最多", problem_stem, re.I
    ))
    if not has_minimum:
        obligations = [item for item in obligations if item != "lower_bound"]
    if not has_maximum:
        obligations = [item for item in obligations if item != "upper_bound"]
    if not (has_minimum or has_maximum):
        obligations = [item for item in obligations if item != "attaining_construction"]
    if mode != "proof":
        obligations = [item for item in obligations if item != "proof_complete"]
    if mode != "choice":
        obligations = [item for item in obligations if item != "option_coverage"]
    obligations.extend(["answer_supported", "domain_conditions", "requested_parts"])
    if mode == "proof":
        obligations.append("proof_complete")
    if mode == "choice":
        obligations.append("option_coverage")
    if re.search(r"\b(?:minimum|minimal|smallest)\b|(?<!at )\bleast\b|最小|最少", problem_stem, re.I):
        obligations.extend(["lower_bound", "attaining_construction"])
    if re.search(r"\b(?:maximum|maximal|largest|greatest)\b|最大|最多", problem_stem, re.I):
        obligations.extend(["upper_bound", "attaining_construction"])
    explicit_all = bool(re.search(
        r"\b(?:find|determine)\s+all\b|\ball\s+possible\b|所有可能|所有解|全部解", problem, re.I
    ))
    if explicit_all:
        obligations.append("all_cases")
    elif re.search(
        r"\b(?:how many|in how many ways|count(?: the)?|(?:compute|determine|find) the number of)\b|"
        r"(?:共有|总共|一共|求|计算).{0,12}(?:多少种|几种|个数|数量)",
        problem,
        re.I,
    ):
        obligations.append("all_cases")
    elif mode in {"choice", "judgment", "fill_blank"}:
        obligations = [item for item in obligations if item != "all_cases"]
    return ProblemProfile(domain=domain, answer_mode=mode, obligations=list(dict.fromkeys(obligations)))


def create_draft(
    text: str, version: int, *, parent_id: str | None = None,
    origin: str = "solver", truncated: bool = False,
    task_id: str | None = None,
) -> SolutionDraft:
    solution_id = f"S{version}"
    paragraphs = tuple(
        Paragraph(f"{solution_id}:P{index}", match.start(), match.end(), match.group())
        for index, match in enumerate(
            re.finditer(r"\S[\s\S]*?(?=\n[ \t]*\n|\Z)", text), start=1
        )
    )
    return SolutionDraft(solution_id, text, paragraphs, parent_id, origin, truncated, task_id)


def _boxed_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    cursor = 0
    while match := _BOX_MARKER.search(text, cursor):
        opening = match.start()
        content_start = match.end()
        depth = 1
        for position in range(content_start, len(text)):
            character = text[position]
            previous = position - 1
            while previous >= 0 and text[previous] == "\\":
                previous -= 1
            slashes = position - 1 - previous
            if slashes % 2:
                continue
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    spans.append((opening, position + 1))
                    cursor = position + 1
                    break
        else:
            break
    return spans


def _candidate(draft: SolutionDraft, start: int, end: int, source: str) -> TextCandidate | None:
    while start < end and draft.text[start].isspace():
        start += 1
    while end > start and draft.text[end - 1].isspace():
        end -= 1
    value = draft.text[start:end]
    if not answer_fragment_is_usable(value):
        return None
    if len(re.findall(r"\\boxed\s*\{", value)) != len(_boxed_spans(value)):
        return None
    return TextCandidate(f"C{draft.id[1:]}", draft.id, value, start, end, source)


def answer_fragment_is_usable(value: str) -> bool:
    if not value.strip() or "```" in value or _FINAL_MARKER.search(value):
        return False
    if re.search(
        r"\b(?:but\s+wait|let(?:'s|\s+us)|we\s+(?:have|need|consider|obtain|can)|"
        r"because|therefore|thus|hence|it\s+follows|the\s+problem\s+asks)\b|"
        r"\bthe\s+(?:total\s+)?(?:number|answer|result)\s+(?:of\b|is\b)|"
        r"因此|所以|由此|推导|证明如下|我们|但是|根据题意|由于", value, re.I,
    ):
        return False
    prose = re.sub(r"\\[a-zA-Z]+|\$[^$]*\$|\\\[[\s\S]*?\\\]", " ", value)
    for paragraph in re.split(r"\n\s*\n", prose):
        if len(re.findall(r"\b[a-zA-Z]{2,}\b", paragraph)) > 24:
            return False
    return True


def extract_candidate(draft: SolutionDraft) -> TextCandidate | None:
    if draft.truncated:
        return None
    markers = list(_FINAL_MARKER.finditer(draft.text))
    footer = _FOOTER.search(draft.text)
    end = footer.start() if footer else len(draft.text)
    if len(markers) == 1 and markers[0].end() < end:
        return _candidate(draft, markers[0].end(), end, "answer_marker")
    if markers:
        return None
    spans = _boxed_spans(draft.text[:end])
    if len(spans) == 1:
        start, finish = spans[0]
        suffix = draft.text[finish:end].strip()
        if re.fullmatch(r"[\s$。.!！]*", suffix) or suffix in {r"\]", r"\)", r"\].", r"\)。"}:
            return _candidate(draft, start, finish, "terminal_box")
    return None


def validate_extraction(draft: SolutionDraft, extraction: AnswerExtraction) -> TextCandidate:
    if extraction.solution_id != draft.id:
        raise ValueError("wrong_solution")
    paragraph = next((item for item in draft.paragraphs if item.id == extraction.paragraph_id), None)
    if paragraph is None or extraction.answer not in paragraph.text:
        raise ValueError("missing_source")
    offset = paragraph.text.index(extraction.answer)
    candidate = _candidate(
        draft, paragraph.start + offset,
        paragraph.start + offset + len(extraction.answer), "source_extractor",
    )
    if candidate is None:
        raise ValueError("empty_or_unbalanced_answer")
    markers = list(_FINAL_MARKER.finditer(draft.text))
    if len(markers) > 1 and any(
        not candidate.start <= marker.end() < candidate.end for marker in markers
    ):
        raise ValueError("extraction_drops_marked_answers")
    if len(markers) == 1:
        for start, end in _boxed_spans(draft.text[markers[0].end():]):
            start += markers[0].end()
            end += markers[0].end()
            content_start = _BOX_MARKER.match(draft.text, start).end()
            if not candidate.start <= content_start < end - 1 <= candidate.end:
                raise ValueError("extraction_drops_boxed_answers")
    return candidate


def render_solution(draft: SolutionDraft, candidate: TextCandidate | None, profile: ProblemProfile) -> str:
    if profile.answer_mode == "proof":
        return re.sub(r"```check[ \t]*\n[\s\S]*?```", "", draft.text, flags=re.I).strip()
    if candidate is None or not answer_fragment_is_usable(candidate.value):
        return "未能提取最终答案。"
    value = candidate.value.strip()
    for start, end in reversed(_boxed_spans(value)):
        content = _BOX_MARKER.sub("", value[start:end], count=1)[:-1]
        value = value[:start] + content + value[end:]
    if profile.answer_mode in {"choice", "judgment", "fill_blank"} and not (
        len(re.findall(r"(?:[（(]\d+[）)]|(?:^|\n)\s*\d+[.)、])", value)) > 1
    ):
        normalized = normalize_objective_answer(value, profile.answer_mode)
        if objective_answer_is_usable(normalized, profile.answer_mode):
            value = normalized
    value = value.strip()
    for opening, closing in (("$$", "$$"), (r"\[", r"\]"), (r"\(", r"\)"), ("$", "$")):
        if value.startswith(opening) and value.endswith(closing) and len(value) >= len(opening) + len(closing):
            value = value[len(opening):-len(closing)].strip()
            break
    return r"\boxed{" + value + "}"
