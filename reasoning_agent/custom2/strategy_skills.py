from dataclasses import dataclass
from collections import Counter
from math import log, sqrt
from pathlib import Path
import re


ALLOWED_SKILL_CATEGORIES: tuple[str, ...] = (
    "probability",
    "stochastic_processes",
    "statistical_inference",
    "linear_regression",
    "linear_algebra",
    "abstract_algebra",
    "combinatorics",
    "advanced_olympiad_mathematics",
    "numerical_analysis",
    "differential_geometry",
    "measure_theory",
    "complex_analysis",
    "ordinary_differential_equations",
    "functional_analysis",
    "partial_differential_equations",
    "operations_research",
    "mathematical_analysis",
    "topology",
)

# English skill handbooks are the primary shared source for strategy planning,
# targeted retrieval, and solver injection.  Keep the legacy Chinese tree as a
# per-category fallback so a partial English migration never silently removes a
# domain from the available skill catalog.
PRIMARY_SKILL_DIRECTORY = "skill2_en"
FALLBACK_SKILL_DIRECTORY = "skill2"

# Short, reusable theorem cards are injected before long skill sections.  They
# are deliberately generic (no contest-specific constants) and give the
# solver a usable statement plus the condition it must check.
THEOREM_CARDS: dict[str, str] = {
    "combinatorics": (
        "定理卡片：\n"
        "- 双计数：同一集合按两种方式计数，先明确对象是否有序及是否重复。\n"
        "- 容斥：|∪A_i|=Σ|A_i|-Σ|A_i∩A_j|+…，交集条件必须逐项核对。\n"
        "- 图/铺砌不变量：每个局部块的奇偶、染色或度数贡献相加，必要条件不能直接当充分条件；需给构造。\n"
        "- 局部窗口铺砌：先把窗口约束写成有限状态转移；若达到极值，再证明行状态与列状态的双向编码，"
        "并用 k=1、k=2 的完整枚举检查组合数是否应为两个独立 k-子集的乘积；独立选择必须用乘法原理，"
        "不能把两种方向只做相加。"
    ),
    "advanced_olympiad_mathematics": (
        "定理卡片：\n"
        "- 整除题先用模运算/因式分解，再检查反向充分性与边界。\n"
        "- 函数方程/递推必须分别证明存在性、唯一性和完备性；有限试值不能代替一般证明。\n"
        "- 极值题闭合上界(或下界)与达到界的构造，不能只验证一个候选。\n"
        "- 整除函数计数：先分离 g(0) 与平移/反射分支，再证明候选函数族的完备性；"
        "不能把约数函数的奇偶性直接等同于题目要求的 exotic 条件。"
    ),
    "abstract_algebra": (
        "定理卡片：先确认运算闭包、单位元/逆元和定义域；将 max-plus 运算与普通加法混用前，"
        "必须逐坐标验证生成集合和不变量。"
    ),
    "linear_algebra": (
        "定理卡片：线性生成/秩下界要给独立性证明；矩阵或向量答案需代回原运算并检查维数。"
    ),
    "geometry": (
        "定理卡片：正弦定理 a/sin A=b/sin B；幂定理 PA·PB=PC·PD；相似/坐标变换需明确对应点。"
    ),
    "differential_geometry": (
        "定理卡片：先写曲线/圆的坐标方程，再由距离或极线定义代入；退化、方向和尺度必须复核。"
    ),
    "statistical_inference": (
        "定理卡片：季节调整常区分移动平均、季节分解和指数法；按题目空格数给出教材术语。"
    ),
    "linear_regression": (
        "定理卡片：最小二乘通过最小化残差平方和估计参数；极大似然依赖分布假设；Newton法是迭代求解工具。"
    ),
    "topology": (
        "定理卡片：Heine–Borel：R^n子集紧致当且仅当闭且有界，也等价于每个开覆盖有有限子覆盖。"
    ),
    "mathematical_analysis": (
        "定理卡片：在R^n中使用闭性、有界性和开覆盖定义时，必须逐项给出反例或等价证明。"
    ),
}


def theorem_cards(categories: list[str] | tuple[str, ...]) -> str:
    """Return at most two compact domain cards for targeted solver context."""
    chunks: list[str] = []
    for raw in categories:
        raw_key = str(raw or "").strip().lower()
        category = raw_key if raw_key in THEOREM_CARDS else normalize_skill_category(raw)
        card = THEOREM_CARDS.get(category)
        if card and card not in chunks:
            chunks.append(f"【{category} 定理卡片】\n{card}")
        if len(chunks) >= 2:
            break
    return "\n\n".join(chunks)


SKILL_CATEGORY_ALIASES: dict[str, str] = {
    "概率论": "probability",
    "probability_theory": "probability",
    "随机过程": "stochastic_processes",
    "stochastic_process": "stochastic_processes",
    "统计推断": "statistical_inference",
    "statistics": "statistical_inference",
    "线性回归": "linear_regression",
    "高等代数": "linear_algebra",
    "抽象代数": "abstract_algebra",
    "离散数学": "combinatorics",
    "discrete_mathematics": "combinatorics",
    "combinatorial_mathematics": "combinatorics",
    "enumerative_combinatorics": "combinatorics",
    "graph_theory": "combinatorics",
    "tiling": "combinatorics",
    "组合数学": "combinatorics",
    "图论": "combinatorics",
    # There is no standalone number-theory skill in skill2.  Route it to the
    # broad olympiad mathematics material rather than the combinatorics file;
    # divisibility/function-classification problems need different tools.
    "number_theory": "advanced_olympiad_mathematics",
    "combinatorial_game_theory": "combinatorics",
    "非基础及进阶课程": "advanced_olympiad_mathematics",
    "advanced_mathematics": "advanced_olympiad_mathematics",
    "algebra": "advanced_olympiad_mathematics",
    "olympiad_algebra": "advanced_olympiad_mathematics",
    "polynomial": "advanced_olympiad_mathematics",
    "polynomials": "advanced_olympiad_mathematics",
    "geometry": "advanced_olympiad_mathematics",
    "plane_geometry": "advanced_olympiad_mathematics",
    "euclidean_geometry": "advanced_olympiad_mathematics",
    "combinatorial_geometry": "advanced_olympiad_mathematics",
    "functional_equation": "advanced_olympiad_mathematics",
    "functional_equations": "advanced_olympiad_mathematics",
    "几何": "advanced_olympiad_mathematics",
    "函数方程": "advanced_olympiad_mathematics",
    "多项式": "advanced_olympiad_mathematics",
    "数值分析": "numerical_analysis",
    "微分几何": "differential_geometry",
    "测度积分": "measure_theory",
    "measure_and_integration": "measure_theory",
    "复分析": "complex_analysis",
    "常微分方程": "ordinary_differential_equations",
    "ode": "ordinary_differential_equations",
    "泛函分析": "functional_analysis",
    "偏微分方程": "partial_differential_equations",
    "pde": "partial_differential_equations",
    "运筹学": "operations_research",
    "数学分析": "mathematical_analysis",
    "real_analysis": "mathematical_analysis",
    "拓扑学": "topology",
}


@dataclass(frozen=True)
class SelectedStrategySkill:
    category: str
    path: str
    prompt: str

    @property
    def id(self) -> str:
        return self.category


def select_strategy_skills(
    primary_category: str,
    secondary_categories: list[str] | tuple[str, ...],
    *,
    top_k: int = 2,
    repo_root: Path | None = None,
) -> list[SelectedStrategySkill]:
    categories = _ordered_valid_categories(primary_category, secondary_categories)
    root = repo_root or Path(__file__).resolve().parents[2]
    selected: list[SelectedStrategySkill] = []
    for category in categories[:top_k]:
        skill_path = _skill_path(root, category)
        if not skill_path.is_file():
            continue
        raw_prompt = skill_path.read_text(encoding="utf-8")
        prompt = raw_prompt.strip()
        if not prompt:
            continue
        selected.append(
            SelectedStrategySkill(
                category=category,
                path=skill_path.relative_to(root).as_posix(),
                prompt=prompt,
            )
        )
    return selected


def skill_catalog(*, repo_root: Path | None = None) -> str:
    """Return a compact model-facing catalog of available skill sections."""

    root = repo_root or Path(__file__).resolve().parents[2]
    lines: list[str] = []
    for category in ALLOWED_SKILL_CATEGORIES:
        path = _skill_path(root, category)
        if not path.is_file():
            continue
        headings = [
            line.strip().lstrip("#").strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if re.match(r"^#{1,4}\s+\S", line)
        ]
        lines.append(f"[{category}] " + " | ".join(headings))
    return "\n".join(lines)


def retrieve_skill_material(
    domains: list[str] | tuple[str, ...],
    sections: list[str] | tuple[str, ...],
    *,
    fallback_category: str,
    problem: str = "",
    retrieval_query: str = "",
    repo_root: Path | None = None,
    max_chars: int = 24000,
) -> tuple[list[SelectedStrategySkill], str]:
    """Read targeted skill sections, with a safe domain fallback.

    The strategy model is allowed to return no section identifiers.  In that
    case feeding the beginning of a long handbook is usually worse than
    feeding a few sections whose headings match the problem family.  The
    fallback below is deliberately heading-based and generic: it never uses
    an item id, an answer, or a problem-specific constant.
    """

    root = repo_root or Path(__file__).resolve().parents[2]
    valid_domains = []
    for raw in domains:
        category = normalize_skill_category(raw)
        if category != "unknown" and category not in valid_domains:
            valid_domains.append(category)
    fallback = normalize_skill_category(fallback_category)
    if fallback != "unknown" and fallback not in valid_domains:
        valid_domains.append(fallback)
    valid_domains = valid_domains[:2]
    wanted = [str(item).strip().lower() for item in sections if str(item).strip()]
    selected: list[SelectedStrategySkill] = []
    chunks: list[str] = []
    remaining = max_chars
    for category in valid_domains:
        path = _skill_path(root, category)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        # A repair has more signal than the original classification: the
        # rejected draft identifies a failed model or theorem.  Let that
        # signal drive a fresh heading search instead of repeatedly injecting
        # the same (possibly irrelevant) strategy-selected sections.  The
        # query is supplied by the runtime from the current problem state;
        # it is never an item id or an answer lookup.
        if retrieval_query.strip():
            pieces = _query_matching_sections(
                text, f"{problem}\n{retrieval_query}", category,
            )
            material = "\n\n".join(pieces) if pieces else text
        elif wanted:
            pieces = _matching_sections(text, wanted)
            # A planner-selected heading is authoritative when it resolves.
            # If a handbook was reorganized and it no longer resolves, use the
            # same lexical ranking as the ordinary problem-driven path.
            material = "\n\n".join(pieces) if pieces else "\n\n".join(
                _query_matching_sections(text, f"{problem}\n{' '.join(wanted)}", category)
            )
        elif problem.strip():
            pieces = _query_matching_sections(text, problem, category)
            material = "\n\n".join(pieces) if pieces else text
        else:
            material = text
        if not material.strip():
            continue
        material = material[:remaining]
        if not material:
            break
        selected.append(SelectedStrategySkill(category, path.relative_to(root).as_posix(), material))
        chunks.append(f"【{category}】\n{material}")
        remaining -= len(material)
        if remaining <= 0:
            break
    return selected, "\n\n".join(chunks)


def _skill_path(root: Path, category: str) -> Path:
    """Resolve one category from English skills, then legacy Chinese skills."""

    filename = f"{category}_skill.md"
    english_path = root / PRIMARY_SKILL_DIRECTORY / category / filename
    if english_path.is_file():
        return english_path
    return root / FALLBACK_SKILL_DIRECTORY / category / filename


def _matching_sections(text: str, wanted: list[str]) -> list[str]:
    pieces: list[str] = []
    for _, _, heading, body in _split_markdown_sections(text):
        if not any(
            _normalized_heading(term) in _normalized_heading(heading)
            or _normalized_heading(heading) in _normalized_heading(term)
            for term in wanted
        ):
            continue
        pieces.append(body)
    return pieces


def _query_matching_sections(text: str, problem: str, category: str) -> list[str]:
    """Rank non-overlapping Markdown sections by title-weighted TF-IDF cosine."""

    del category  # Kept in the public helper signature for call-site stability.
    query_terms = Counter(_lexical_terms(problem))
    if not query_terms:
        return []
    sections = [
        (start, heading, body)
        for start, level, heading, body in _split_markdown_sections(text)
        if level > 1 and "习题索引" not in heading and "参考资源" not in heading
    ]
    if not sections:
        return []
    section_terms = [
        Counter(_lexical_terms(heading) * 3 + _lexical_terms(body))
        for _, heading, body in sections
    ]
    document_frequency: Counter[str] = Counter()
    for terms in section_terms:
        document_frequency.update(terms.keys())
    total_sections = len(section_terms)

    def weight(term: str, frequency: int) -> float:
        return frequency * (log((total_sections + 1) / (document_frequency[term] + 1)) + 1.0)

    query_norm = sqrt(sum(weight(term, count) ** 2 for term, count in query_terms.items()))
    if query_norm == 0:
        return []
    candidates: list[tuple[float, int, str]] = []
    for (start, _, body), terms in zip(sections, section_terms):
        dot = sum(
            weight(term, query_terms[term]) * weight(term, frequency)
            for term, frequency in terms.items() if term in query_terms
        )
        section_norm = sqrt(sum(weight(term, count) ** 2 for term, count in terms.items()))
        if dot and section_norm:
            candidates.append((dot / (query_norm * section_norm), start, body))

    if not candidates:
        return []
    candidates.sort(key=lambda item: (-item[0], item[1]))
    # Keep enough context for two complementary methods while preventing a
    # large handbook from consuming the solver's useful context window.
    selected: list[str] = []
    total = 0
    for _, _, body in candidates[:8]:
        if total + len(body) > 14000 and selected:
            continue
        selected.append(body)
        total += len(body)
        if total >= 10000:
            break
    return selected


def _split_markdown_sections(text: str) -> list[tuple[int, int, str, str]]:
    """Split on every Markdown heading so candidate passages never overlap."""
    lines = text.splitlines()
    starts: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,4})\s+(\S.*)$", line)
        if match:
            starts.append((index, len(match.group(1)), match.group(2).strip()))
    sections: list[tuple[int, int, str, str]] = []
    for position, (start, level, heading) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        if body:
            sections.append((start, level, heading.casefold(), body))
    return sections


def _lexical_terms(text: str) -> list[str]:
    """Tokenize English words and Chinese character bigrams without a tokenizer dependency."""
    normalized = str(text or "").casefold()
    terms = re.findall(r"[a-z][a-z0-9_-]{1,}|\d{2,}", normalized)
    for block in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
        terms.extend(block[index:index + 2] for index in range(len(block) - 1))
    return terms


def _normalized_heading(text: str) -> str:
    """Ignore incidental whitespace emitted inside a catalog heading."""
    return re.sub(r"\s+", "", str(text or "").casefold())


def _ordered_valid_categories(
    primary_category: str,
    secondary_categories: list[str] | tuple[str, ...],
) -> list[str]:
    ordered: list[str] = []
    for raw_category in (primary_category, *secondary_categories):
        category = normalize_skill_category(raw_category)
        if category == "unknown" or category in ordered:
            continue
        ordered.append(category)
    return ordered


def normalize_skill_category(raw_category: object) -> str:
    raw = str(raw_category or "").strip()
    if not raw:
        return "unknown"
    normalized = raw.lower().replace("-", " ").replace("/", " ")
    normalized = "_".join(normalized.split())
    if normalized in ALLOWED_SKILL_CATEGORIES:
        return normalized
    return SKILL_CATEGORY_ALIASES.get(raw, SKILL_CATEGORY_ALIASES.get(normalized, "unknown"))
