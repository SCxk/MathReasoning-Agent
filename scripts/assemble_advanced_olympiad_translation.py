"""Assemble dialogue-translated Advanced Olympiad Markdown parts in source order."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "skill2_en" / "advanced_olympiad_mathematics"
ORDER = [
    "advanced_olympiad_mathematics_part_01.md",
    "advanced_olympiad_mathematics_part_05.md",
    "advanced_olympiad_mathematics_part_06.md",
    "advanced_olympiad_mathematics_part_02.md",
    "advanced_olympiad_mathematics_part_03.md",
    "advanced_olympiad_mathematics_part_04.md",
]


def main() -> None:
    destination = PARTS / "advanced_olympiad_mathematics_skill.md"
    destination.write_text(
        "\n\n".join((PARTS / name).read_text(encoding="utf-8").rstrip() for name in ORDER) + "\n",
        encoding="utf-8",
    )
    print(destination)


if __name__ == "__main__":
    main()
