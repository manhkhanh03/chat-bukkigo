from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("chat_bukkigo.core.session_store")


class SessionStore:
    """Quản lý lịch sử hội thoại in-memory theo session_id với cơ chế cắt tỉa an toàn."""

    def __init__(self, max_messages: int = 30):
        self.max_messages = max_messages
        self._history: Dict[str, List[Dict[str, Any]]] = {}

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._history.get(session_id, []))

    def append(self, session_id: str, message: Dict[str, Any]) -> None:
        if session_id not in self._history:
            self._history[session_id] = []
        self._history[session_id].append(message)

    def extend(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        if session_id not in self._history:
            self._history[session_id] = []
        self._history[session_id].extend(messages)

    def reset(self, session_id: str) -> None:
        if session_id in self._history:
            self._history[session_id] = []

    def trim(self, session_id: str) -> None:
        """Cắt bớt message cũ nhất nếu vượt quá max_messages.

        Đảm bảo không cắt ngang giữa cặp message assistant(tool_calls) và tool response.
        """
        history = self._history.get(session_id)
        if not history or len(history) <= self.max_messages:
            return

        excess = len(history) - self.max_messages
        cut_idx = excess

        # Đảm bảo không cắt tại vị trí tool message hoặc giữa lượt tool_calls
        while cut_idx < len(history) and history[cut_idx].get("role") == "tool":
            cut_idx += 1

        self._history[session_id] = history[cut_idx:]
        logger.debug("Đã cắt bớt %d tin nhắn cũ cho session '%s'.", cut_idx, session_id)
