"""Assemble the direct English translation of the probability skill document."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARTS_DIR = ROOT / "skill2_en" / "probability"
OUTPUT = PARTS_DIR / "probability_skill.md"


def main() -> None:
    parts = [
        PARTS_DIR / f"probability_skill_part_{number:02d}.md"
        for number in range(1, 8)
    ]
    OUTPUT.write_text(
        "\n\n".join(part.read_text(encoding="utf-8").rstrip() for part in parts) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
