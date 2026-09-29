from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from chat_bukkigo.core.base_tool import BaseTool
from chat_bukkigo.rag.retriever import KnowledgeRetriever

logger = logging.getLogger("chat_bukkigo.tools.search_nail_knowledge")


class SearchNailKnowledgeTool(BaseTool):
    """Tool tra cứu cơ sở tri thức nghiệp vụ Nail trên Qdrant Vector DB."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.retriever = KnowledgeRetriever()

    async def execute(
        self,
        query: str,
        category: Optional[str] = None,
        service: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        logger.info("Thực thi search_nail_knowledge với query='%s', category='%s', service='%s'", query, category, service)

        results = self.retriever.retrieve(
            query=query,
            limit=2,
            category=category,
            service=service,
        )

        if not results:
            return {
                "status": "not_found",
                "message": "Không tìm thấy tài liệu phù hợp trong cơ sở tri thức.",
            }

        retrieved_data = []
        for r in results:
            retrieved_data.append(
                {
                    "topic": r.topic,
                    "service": r.service,
                    "score": round(r.score, 4),
                    "facts": r.facts,
                    "boundary_rules": r.boundary_rules,
                    "suggested_response_de": r.sample_dialogue.get("de_CH", ""),
                    "suggested_response_vi": r.sample_dialogue.get("vi_VN", ""),
                }
            )

        return {
            "status": "success",
            "count": len(retrieved_data),
            "knowledge": retrieved_data,
            "instruction_for_agent": (
                "Sử dụng Facts trên để trả lời ngắn gọn (20-40 từ). "
                "TUYỆT ĐỐI tuân thủ Boundary Rules (không tự chẩn đoán, không khẳng định lỗi). "
                "Kết thúc bằng lời mời đặt lịch hẹn để thợ kiểm tra trực tiếp."
            ),
        }
