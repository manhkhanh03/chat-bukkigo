from __future__ import annotations

from typing import Any, List, Optional

from .embedding import EmbeddingEngine
from .qdrant_manager import QdrantManager
from .schema import SearchResult


class KnowledgeRetriever:
    """Truy xuất tri thức nghiệp vụ Nail Lễ tân từ Qdrant Vector DB."""

    def __init__(
        self,
        qdrant_manager: Optional[QdrantManager] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
    ) -> None:
        self.qdrant = qdrant_manager or QdrantManager()
        self.embedding = embedding_engine or EmbeddingEngine()

    def retrieve(
        self,
        query: str,
        limit: int = 3,
        category: Optional[str] = None,
        service: Optional[str] = None,
    ) -> List[SearchResult]:
        """Thực hiện tìm kiếm ngữ nghĩa theo câu hỏi của khách."""
        query_vector = self.embedding.embed_query(query)
        points = self.qdrant.search(
            query_vector=query_vector,
            limit=limit,
            category=category,
            service=service,
        )

        results: List[SearchResult] = []
        for p in points:
            payload = p.payload or {}
            results.append(
                SearchResult(
                    chunk_id=str(p.id),
                    score=float(p.score),
                    category=payload.get("category", ""),
                    service=payload.get("service", ""),
                    topic=payload.get("topic", ""),
                    facts=payload.get("facts", ""),
                    boundary_rules=payload.get("boundary_rules", ""),
                    sample_dialogue=payload.get("sample_dialogue", {}),
                    keywords=payload.get("keywords", []),
                )
            )
        return results
