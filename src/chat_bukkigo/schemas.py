from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    history: list[ChatMessage] = Field(default_factory=list)
    user_id: str | None = Field(default=None, max_length=256)


class ChatResponse(BaseModel):
    answer: str
    response_id: str
    intent: str
    response_mode: str
    references_used: list[str]
    trace_id: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model: str
    api_key_configured: bool
    endpoint_mode: Literal["openai", "custom"]
