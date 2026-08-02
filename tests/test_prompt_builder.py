from pathlib import Path

from chat_bukkigo.prompt_builder import SkillLoader
from chat_bukkigo.router import route

SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "nail-beauty-consultant"


def test_safety_prompt_excludes_occasion_and_style_references() -> None:
    bundle = SkillLoader(SKILL_PATH).build(route("Móng bị sưng đau và có mủ"))

    assert "# Safety Escalation" in bundle.instructions
    assert "# Occasion Guides" not in bundle.instructions
    assert "# Style Taxonomy" not in bundle.instructions


def test_occasion_prompt_excludes_safety_reference() -> None:
    bundle = SkillLoader(SKILL_PATH).build(route("Gợi ý nail Tết thanh lịch"))

    assert "# Occasion Guides" in bundle.instructions
    assert "# Safety Escalation" not in bundle.instructions
    assert "safety-escalation.md" not in bundle.references_used
