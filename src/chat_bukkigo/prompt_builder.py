from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .router import RoutingDecision


@dataclass(frozen=True, slots=True)
class PromptBundle:
    instructions: str
    references_used: tuple[str, ...]


RESPONSE_CONTRACTS = {
    "direct": (
        "Trả lời ngay trong 1–3 câu nếu câu hỏi không đòi hỏi giải thích dài. "
        "Không mở bài, không tiêu đề, không biến câu trả lời thành danh sách."
    ),
    "recommend": (
        "Đưa một hướng bạn nghiêng về trước, kèm một lý do gắn với khách. "
        "Chỉ thêm một phương án khác khi nó tạo ra lựa chọn có ý nghĩa. "
        "Hỏi một câu tinh chỉnh duy nhất nếu câu trả lời có thể làm hướng tư vấn đổi đáng kể."
    ),
    "explore": (
        "Khách chưa có mỏ neo rõ. Đưa tối đa ba hướng thật khác nhau về cảm giác, "
        "mỗi hướng một dòng ngắn, rồi hỏi một câu giúp chọn giữa các hướng."
    ),
    "compare": (
        "Nói kết luận hoặc hướng bạn nghiêng về ở câu đầu. Sau đó chỉ nêu tối đa hai "
        "khác biệt có tác động tới quyết định. Không dùng bảng trừ khi khách yêu cầu."
    ),
    "refine": (
        "Đây là lượt chỉnh tiếp từ hội thoại trước. Chỉ nói phần cần đổi và hiệu ứng của "
        "thay đổi đó trong 1–3 câu; không lặp lại toàn bộ đề xuất cũ."
    ),
    "safety": (
        "Ưu tiên sự rõ ràng và hành động an toàn hơn độ ngắn. Nói bình tĩnh: việc nên làm "
        "ngay, dấu hiệu nào cần người có chuyên môn, và giới hạn của nhận định qua chat."
    ),
}


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
        response_contract = RESPONSE_CONTRACTS[decision.response_mode.value]
        sections = [
            "<skill_core>",
            self._without_frontmatter(self._core),
            "</skill_core>",
            (
                "<runtime_contract>\n"
                f"Intent: {decision.intent.value}. "
                f"Kiểu phản hồi: {decision.response_mode.value}.\n"
                f"{response_contract}\n"
                "Độ dài là trần mềm, không phải mục tiêu phải lấp đầy: khi đã đủ để khách "
                "hiểu hoặc chọn thì dừng. Dùng reference để suy luận có chọn lọc, không kể "
                "lại toàn bộ kiến thức và không chép nguyên văn. Trả lời bằng ngôn ngữ của "
                "khách. Không nhắc tên file, intent, kiểu phản hồi hoặc quá trình định tuyến.\n"
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
