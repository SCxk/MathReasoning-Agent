"""Assemble dialogue-translated ODE Markdown parts in source order."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "skill2_en" / "ordinary_differential_equations"


def main() -> None:
    names = [f"ordinary_differential_equations_skill_part_{i:02d}.md" for i in range(1, 4)]
    (PARTS / "ordinary_differential_equations_skill.md").write_text(
        "\n\n".join((PARTS / name).read_text(encoding="utf-8").rstrip() for name in names) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
