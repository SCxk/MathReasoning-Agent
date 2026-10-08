"""Assemble the direct English translation of the topology skill document."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARTS_DIR = ROOT / "skill2_en" / "topology"
OUTPUT = PARTS_DIR / "topology_skill.md"


def main() -> None:
    parts = [
        PARTS_DIR / "topology_skill_part_01.md",
        PARTS_DIR / "topology_skill_part_02.md",
        PARTS_DIR / "topology_skill_part_03.md",
    ]
    OUTPUT.write_text(
        "\n\n".join(part.read_text(encoding="utf-8").rstrip() for part in parts) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
