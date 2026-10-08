"""Assemble the direct English translation of the operations-research skill."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARTS_DIR = ROOT / "skill2_en" / "operations_research"
OUTPUT = PARTS_DIR / "operations_research_skill.md"


def main() -> None:
    parts = [PARTS_DIR / f"operations_research_skill_part_{i:02d}.md" for i in range(1, 4)]
    OUTPUT.write_text("\n\n".join(p.read_text(encoding="utf-8").rstrip() for p in parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
