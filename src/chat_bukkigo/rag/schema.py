from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class SampleDialogue(BaseModel):
    de_CH: str = Field(description="Swiss German / German dialogue example")
    vi_VN: str = Field(description="Vietnamese dialogue example")


class KnowledgeChunk(BaseModel):
    id: str
    category: str
    service: str
    topic: str
    query_samples: List[str] = Field(default_factory=list)
    facts: str
    boundary_rules: str
    sample_dialogue: Union[SampleDialogue, Dict[str, str]]
    keywords: List[str] = Field(default_factory=list)

    def to_embedding_text(self) -> str:
        """Tạo chuỗi text tối ưu hóa cho embedding tìm kiếm (Query-Optimized Embedding)."""
        samples = " ".join(self.query_samples)
        kw = " ".join(self.keywords)
        return (
            f"Topic: {self.topic} | Service: {self.service} | "
            f"Queries: {samples} | Facts: {self.facts} | Keywords: {kw}"
        )


class SearchResult(BaseModel):
    chunk_id: str
    score: float
    category: str
    service: str
    topic: str
    facts: str
    boundary_rules: str
    sample_dialogue: Dict[str, str]
    keywords: List[str]
