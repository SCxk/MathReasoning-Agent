from pathlib import Path

from reasoning_agent.custom2.strategy_skills import (
    retrieve_skill_material,
    select_strategy_skills,
)


def test_english_skill_is_preferred_over_legacy_chinese_skill(tmp_path: Path) -> None:
    english_dir = tmp_path / "skill2_en" / "combinatorics"
    english_dir.mkdir(parents=True)
    (english_dir / "combinatorics_skill.md").write_text(
        "# Combinatorics\n\n## English method\nEnglish material.",
        encoding="utf-8",
    )
    legacy_dir = tmp_path / "skill2" / "combinatorics"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "combinatorics_skill.md").write_text(
        "# 组合数学\n\n## 旧方法\n中文旧内容。",
        encoding="utf-8",
    )

    selected = select_strategy_skills(
        "combinatorics", [], repo_root=tmp_path,
    )
    _, material = retrieve_skill_material(
        ["combinatorics"], [], fallback_category="combinatorics",
        problem="English method", repo_root=tmp_path,
    )

    assert selected[0].path == "skill2_en/combinatorics/combinatorics_skill.md"
    assert "English material." in material
    assert "中文旧内容。" not in material


def test_legacy_chinese_skill_is_used_when_english_skill_is_missing(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill2" / "combinatorics"
    skill_dir.mkdir(parents=True)
    (skill_dir / "combinatorics_skill.md").write_text(
        "# 组合\n\n## 回退\n中文回退内容。",
        encoding="utf-8",
    )

    selected = select_strategy_skills(
        "combinatorics", [], repo_root=tmp_path,
    )

    assert selected[0].path == "skill2/combinatorics/combinatorics_skill.md"
    assert "中文回退内容。" in selected[0].prompt


def test_repair_query_overrides_stale_strategy_sections(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill2" / "combinatorics"
    skill_dir.mkdir(parents=True)
    (skill_dir / "combinatorics_skill.md").write_text(
        "# 组合\n\n## 递推\n旧策略内容\n\n## 图论\n图的边和顶点计数。\n",
        encoding="utf-8",
    )

    _, material = retrieve_skill_material(
        ["combinatorics"],
        ["递推"],
        fallback_category="combinatorics",
        problem="给定一个对象。",
        retrieval_query="图论 graph edge vertex",
        repo_root=tmp_path,
    )

    assert "## 图论" in material
    assert "## 递推" not in material


def test_problem_terms_rank_non_overlapping_markdown_sections(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill2" / "combinatorics"
    skill_dir.mkdir(parents=True)
    (skill_dir / "combinatorics_skill.md").write_text(
        "# 组合\n\n"
        "## 通用方法\n基础内容。\n\n"
        "### 嵌套段落\n不应与父段落重叠注入。\n\n"
        "## 谱方法\nquantum lattice invariant 的状态编码。\n\n"
        "## 递推\n普通递推。\n",
        encoding="utf-8",
    )

    _, material = retrieve_skill_material(
        ["combinatorics"], [], fallback_category="combinatorics",
        problem="Use a quantum lattice invariant.", repo_root=tmp_path,
    )

    assert "## 谱方法" in material
    assert "### 嵌套段落" not in material


def test_explicit_strategy_heading_precedes_lexical_fallback(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill2" / "combinatorics"
    skill_dir.mkdir(parents=True)
    (skill_dir / "combinatorics_skill.md").write_text(
        "# 组合\n\n## 指定方法\n保留此段。\n\n## 相似方法\nquantum lattice。\n",
        encoding="utf-8",
    )

    _, material = retrieve_skill_material(
        ["combinatorics"], ["指定方法"], fallback_category="combinatorics",
        problem="quantum lattice", repo_root=tmp_path,
    )

    assert "## 指定方法" in material
    assert "## 相似方法" not in material


def test_heading_match_ignores_accidental_internal_whitespace(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill2" / "combinatorics"
    skill_dir.mkdir(parents=True)
    (skill_dir / "combinatorics_skill.md").write_text(
        "# 组合\n\n## Hamilton 路径块分解\n状态转移。\n",
        encoding="utf-8",
    )

    _, material = retrieve_skill_material(
        ["combinatorics"], ["Hamilton 路径块分 解"],
        fallback_category="combinatorics", repo_root=tmp_path,
    )

    assert "## Hamilton 路径块分解" in material
