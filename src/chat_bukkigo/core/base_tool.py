from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Chuẩn giao tiếp BaseTool cho mọi tool trong hệ sinh thái Bukkigo.

    Tất cả thông số (name, description, parameters, timeout, requires_confirmation)
    được đọc từ file tool.yaml cạnh nó.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name: str = config["name"]
        self.description: str = config["description"]
        self.parameters: Dict[str, Any] = config.get(
            "parameters", {"type": "object", "properties": {}}
        )
        self.timeout: float = config.get("timeout", 15.0)
        self.requires_confirmation: bool = bool(config.get("requires_confirmation", False))

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Hộp đen logic nghiệp vụ của tool (tìm kiếm Qdrant, DB, API, Calendar...)."""
        raise NotImplementedError

    def get_tool_schema(self) -> Dict[str, Any]:
        """Sinh schema chuẩn OpenAI Function Calling từ cấu hình trong tool.yaml."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
