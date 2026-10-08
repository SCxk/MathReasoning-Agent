"""Assemble the direct English translation of the linear-algebra skill."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "skill2_en" / "linear_algebra"


def main() -> None:
    source = DIR / "linear_algebra_skill_part_01.md"
    (DIR / "linear_algebra_skill.md").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    main()
