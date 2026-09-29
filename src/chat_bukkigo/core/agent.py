from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from .registry import ToolRegistry
from .session_store import SessionStore

logger = logging.getLogger("chat_bukkigo.core.agent")


def sanitize_unicode(data: Any) -> Any:
    """Loại bỏ các ký tự surrogate không hợp lệ khỏi chuỗi/dict/list."""
    if isinstance(data, str):
        return re.sub(r"[\ud800-\udfff]", "", data)
    elif isinstance(data, dict):
        return {k: sanitize_unicode(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_unicode(v) for v in data]
    return data


class AgentCore:
    """Bộ điều phối Agent: Tiếp nhận input, gọi LLM, thực thi Function Calling và tổng hợp câu trả lời."""

    def __init__(
        self,
        llm_client: Any,
        registry: ToolRegistry,
        system_prompt: str = "",
        model: Optional[str] = None,
        session_store: Optional[SessionStore] = None,
        max_tool_iterations: int = 6,
    ):
        self.llm = llm_client
        self.registry = registry
        self.system_prompt = system_prompt
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.sessions = session_store or SessionStore(
            max_messages=int(os.getenv("MAX_HISTORY_MESSAGES", "30"))
        )
        self.max_tool_iterations = max_tool_iterations

    async def _call_llm(self, messages: List[Dict[str, Any]], tools_schema: Optional[List[Dict[str, Any]]]) -> Any:
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            if tools_schema:
                kwargs["tools"] = tools_schema
                kwargs["tool_choice"] = "auto"

            return await self.llm.chat.completions.create(**kwargs)
        except Exception:
            logger.exception("Lỗi khi gọi LLM chat completions")
            return None

    @staticmethod
    def _tool_message(tool_call_id: str, tool_name: str, content: str) -> Dict[str, Any]:
        return sanitize_unicode(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": content,
            }
        )

    async def _run_tool_call(self, tool_call: Any) -> Tuple[Dict[str, Any], str, List[str]]:
        tool_name = tool_call.function.name
        details: List[str] = []
        try:
            arguments = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError:
            logger.warning("Tool '%s' nhận arguments không phải JSON hợp lệ: %s", tool_name, tool_call.function.arguments)
            content = f"Tool Error: arguments gửi cho '{tool_name}' không phải JSON hợp lệ."
            return self._tool_message(tool_call.id, tool_name, content), tool_name, details

        logger.info("[TOOL_CALL] LLM yêu cầu gọi tool '%s' với arguments: %s", tool_name, arguments)
        t_start = time.perf_counter()
        tool_result = await self.registry.execute_tool(tool_name, arguments)
        elapsed = time.perf_counter() - t_start
        logger.info("[TOOL_RESULT] Tool '%s' hoàn tất sau %.2fs", tool_name, elapsed)

        # Trích xuất chi tiết topic/score từ kết quả Qdrant để log minh bạch
        try:
            parsed = json.loads(tool_result)
            if isinstance(parsed, dict) and "knowledge" in parsed:
                for k in parsed["knowledge"]:
                    topic = k.get("topic", "")
                    score = k.get("score", "")
                    details.append(f"qdrant:{topic}(score={score})")
        except Exception:
            pass

        return self._tool_message(tool_call.id, tool_name, tool_result), tool_name, details

    async def chat(
        self,
        user_input: str,
        session_id: str = "default",
        system_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Xử lý một lượt chat của người dùng.

        Returns:
            Dict chứa 'answer', 'tools_used', 'data_sources', 'iterations'.
        """
        history = self.sessions.get_history(session_id)
        effective_system = system_override or self.system_prompt

        # Nếu session chưa có system prompt, nạp vào đầu
        if not history or history[0].get("role") != "system":
            if effective_system:
                self.sessions.append(session_id, {"role": "system", "content": effective_system})

        # Nạp user message
        self.sessions.append(session_id, {"role": "user", "content": sanitize_unicode(user_input)})
        self.sessions.trim(session_id)

        tools_schema = self.registry.get_all_schemas() if self.registry.has_tools() else None
        tools_used: List[str] = []
        data_sources: List[str] = []
        iterations = 0

        while True:
            messages = self.sessions.get_history(session_id)
            response = await self._call_llm(sanitize_unicode(messages), tools_schema)

            if not response or not response.choices:
                logger.error("LLM trả về response rỗng hoặc không có choices")
                return {
                    "answer": "Rất tiếc, hệ thống tạm thời gặp sự cố khi kết nối dịch vụ.",
                    "tools_used": tools_used,
                    "data_sources": ["system:fallback"],
                    "iterations": iterations,
                }

            message = response.choices[0].message
            self.sessions.append(session_id, sanitize_unicode(message.model_dump(exclude_none=True)))

            # Nếu không có tool_calls -> Đây là câu trả lời cuối cùng
            if not message.tool_calls:
                if iterations == 0:
                    # Không gọi tool nào, trả lời trực tiếp từ Core References
                    data_sources = ["system:receptionist-core-rules.md", "system:safety-and-medical.md"]
                    logger.info("[NGUỒN DỮ LIỆU: SYSTEM_REFERENCES] Bot trả lời TRỰC TIẾP từ Core References (không dùng Tool): %s", data_sources)
                else:
                    logger.info("[NGUỒN DỮ LIỆU: QDRANT_TOOL] Bot đã TỔNG HỢP câu trả lời dựa trên Tool và Qdrant: %s", data_sources)

                return {
                    "answer": sanitize_unicode(message.content or ""),
                    "tools_used": tools_used,
                    "data_sources": data_sources,
                    "iterations": iterations,
                }

            iterations += 1
            if iterations > self.max_tool_iterations:
                logger.warning("Đã vượt quá giới hạn %d vòng gọi tool trong 1 lượt.", self.max_tool_iterations)
                cutoff_messages = [
                    self._tool_message(tc.id, tc.function.name, "Error: Đã đạt giới hạn số lần gọi tool liên tiếp.")
                    for tc in message.tool_calls
                ]
                self.sessions.extend(session_id, cutoff_messages)
                return {
                    "answer": "Yêu cầu cần quá nhiều bước tra cứu. Quý khách vui lòng cho em biết rõ nhu cầu cụ thể hơn nhé.",
                    "tools_used": tools_used,
                    "data_sources": data_sources,
                    "iterations": iterations,
                }

            # Thực thi các tool_calls song song
            tool_tasks = [self._run_tool_call(tc) for tc in message.tool_calls]
            results = await asyncio.gather(*tool_tasks)

            tool_messages = []
            for t_msg, t_name, t_details in results:
                tool_messages.append(t_msg)
                if t_name not in tools_used:
                    tools_used.append(t_name)
                    data_sources.append(f"tool:{t_name}")
                for d in t_details:
                    if d not in data_sources:
                        data_sources.append(d)

            self.sessions.extend(session_id, tool_messages)
