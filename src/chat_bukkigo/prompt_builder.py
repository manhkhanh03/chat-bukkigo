from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .router import RoutingDecision


@dataclass(frozen=True, slots=True)
class PromptBundle:
    instructions: str
    references_used: tuple[str, ...]


class SkillLoader:
    def __init__(self, skill_path: Path) -> None:
        self.skill_path = skill_path
        self.references_path = skill_path / "references"
        self._core = self._read(skill_path / "SKILL.md")

    @staticmethod
    def _read(path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(f"Missing skill resource: {path}")
        return path.read_text(encoding="utf-8").strip()

    @staticmethod
    def _without_frontmatter(content: str) -> str:
        return re.sub(r"\A---\s*.*?\s*---\s*", "", content, count=1, flags=re.DOTALL)

    def build(self, decision: RoutingDecision) -> PromptBundle:
        sections = [
            "<skill_core>",
            self._without_frontmatter(self._core),
            "</skill_core>",
            (
                "<runtime_contract>\n"
                f"Intent đã định tuyến: {decision.intent.value}. "
                "Dùng reference như nguyên tắc suy luận, không chép nguyên văn. "
                "Trả lời bằng ngôn ngữ của khách. Không nhắc tên file hoặc quá trình định tuyến.\n"
                "</runtime_contract>"
            ),
        ]

        for name in decision.references:
            content = self._read(self.references_path / name)
            sections.extend((f'<reference name="{name}">', content, "</reference>"))

        return PromptBundle(
            instructions="\n\n".join(sections),
            references_used=decision.references,
        )
