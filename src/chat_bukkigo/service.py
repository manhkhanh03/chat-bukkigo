from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from openai import APIError, AsyncOpenAI

from .config import Settings
from .core.agent import AgentCore
from .core.registry import ToolRegistry
from .prompt_builder import SkillLoader
from .router import Intent, ResponseMode, RoutingDecision, route
from .schemas import ChatRequest, ChatResponse


class MissingAPIKeyError(RuntimeError):
    pass


class ProviderRequestError(RuntimeError):
    def __init__(self, trace_id: str) -> None:
        super().__init__("OpenAI request failed")
        self.trace_id = trace_id


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    event: str
    data: dict[str, object]


@dataclass(frozen=True, slots=True)
class PreparedChat:
    kwargs: dict[str, object]
    intent: str
    response_mode: str
    references_used: tuple[str, ...]
    instruction_chars: int
    max_output_tokens: int


OUTPUT_TOKEN_BUDGETS = {
    ResponseMode.DIRECT: 350,
    ResponseMode.RECOMMEND: 500,
    ResponseMode.EXPLORE: 500,
    ResponseMode.COMPARE: 450,
    ResponseMode.REFINE: 350,
    ResponseMode.SAFETY: 650,
}


class ChatService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger("chat_bukkigo.service")
        self.skill_loader = SkillLoader(settings.skill_path)
        client_options: dict[str, object] = {}
        if settings.use_custom_endpoint:
            client_options["base_url"] = settings.custom_base_url
        self.client = (
            AsyncOpenAI(
                api_key=settings.api_key.get_secret_value(),
                timeout=settings.openai.timeout_seconds,
                max_retries=settings.openai.max_retries,
                **client_options,
            )
            if settings.api_key
            else None
        )
        self.tool_registry = ToolRegistry()
        self.tool_registry.discover_and_register()
        core_prompt = self.skill_loader.build_core_system_prompt()
        self.agent = (
            AgentCore(
                llm_client=self.client,
                registry=self.tool_registry,
                system_prompt=core_prompt,
                model=settings.openai.model,
            )
            if self.client
            else None
        )

    def ensure_configured(self) -> None:
        if self.client is None:
            raise MissingAPIKeyError("OPENAI_API_KEY is not configured")

    def _safety_identifier(self, user_id: str | None) -> str | None:
        if not user_id or not self.settings.safety_salt:
            return None
        salt = self.settings.safety_salt.get_secret_value()
        return hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()

    def _prepare(self, request: ChatRequest) -> PreparedChat:
        max_history = self.settings.skill.max_history_messages
        history = request.history[-max_history:] if max_history else []
        previous_user_message = next(
            (message.content for message in reversed(history) if message.role == "user"),
            None,
        )
        decision = route(request.message, context=previous_user_message)
        prompt = self.skill_loader.build(decision)
        input_messages = [message.model_dump() for message in history]
        input_messages.append({"role": "user", "content": request.message})
        max_output_tokens = self._output_token_budget(decision)

        kwargs: dict[str, object] = {
            "model": self.settings.openai.model,
            "instructions": prompt.instructions,
            "input": input_messages,
            "reasoning": {"effort": self.settings.openai.reasoning_effort},
            "text": {"verbosity": self.settings.openai.verbosity},
            "max_output_tokens": max_output_tokens,
            "store": self.settings.openai.store,
        }
        if safety_identifier := self._safety_identifier(request.user_id):
            kwargs["safety_identifier"] = safety_identifier

        return PreparedChat(
            kwargs=kwargs,
            intent=decision.intent.value,
            response_mode=decision.response_mode.value,
            references_used=prompt.references_used,
            instruction_chars=len(prompt.instructions),
            max_output_tokens=max_output_tokens,
        )

    def _output_token_budget(self, decision: RoutingDecision) -> int:
        budget = OUTPUT_TOKEN_BUDGETS[decision.response_mode]
        if decision.intent is Intent.TECHNICAL:
            budget = max(budget, 500)
        return min(budget, self.settings.openai.max_output_tokens)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.ensure_configured()

        # 1. Nếu có AgentCore và có Tools đăng ký (search_nail_knowledge, booking...), ưu tiên chạy Agent có Function Calling
        if self.agent and self.tool_registry.has_tools():
            session_id = request.user_id or "default"
            trace_id = uuid.uuid4().hex[:12]
            started = time.perf_counter()
            try:
                # Đồng bộ history nếu session chưa có nhưng request có history
                if request.history and not self.agent.sessions.get_history(session_id):
                    for msg in request.history:
                        self.agent.sessions.append(session_id, {"role": msg.role, "content": msg.content})

                agent_res = await self.agent.chat(user_input=request.message, session_id=session_id)
                total_ms = round((time.perf_counter() - started) * 1000)
                data_sources = agent_res.get("data_sources", [])
                self.logger.info(
                    "event=agent_chat_completed trace_id=%s data_sources=%s tools_used=%s total_ms=%s",
                    trace_id,
                    data_sources,
                    agent_res.get("tools_used", []),
                    total_ms,
                )
                return ChatResponse(
                    answer=agent_res["answer"],
                    response_id=f"agent-{trace_id}",
                    intent="agent_tool_calling" if agent_res.get("tools_used") else "core_references",
                    response_mode="direct",
                    references_used=data_sources,
                    trace_id=trace_id,
                )
            except Exception as e:
                self.logger.warning("AgentCore gặp lỗi (%s), chuyển sang Responses API fallback...", e)

        # 2. Fallback sang Responses API truyền thống
        prepared = self._prepare(request)
        trace_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        self._log_started(trace_id, prepared, stream=False)
        try:
            response = await self.client.responses.create(**prepared.kwargs)  # type: ignore[union-attr]
        except APIError as exc:
            self._log_provider_error(trace_id, started, exc, stream=False)
            raise ProviderRequestError(trace_id) from exc
        total_ms = round((time.perf_counter() - started) * 1000)
        answer = response.output_text
        self.logger.info(
            "event=chat_completed trace_id=%s stream=false response_id=%s "
            "output_chars=%s total_ms=%s",
            trace_id,
            response.id,
            len(answer),
            total_ms,
        )
        return ChatResponse(
            answer=answer,
            response_id=response.id,
            intent=prepared.intent,
            response_mode=prepared.response_mode,
            references_used=list(prepared.references_used),
            trace_id=trace_id,
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        self.ensure_configured()

        # 1. Nếu có AgentCore và có Tools đăng ký, ưu tiên chạy Agent có Function Calling
        if self.agent and self.tool_registry.has_tools():
            session_id = request.user_id or "default"
            trace_id = uuid.uuid4().hex[:12]
            started = time.perf_counter()
            self.logger.info(
                "event=agent_stream_started trace_id=%s model=%s session_id=%s",
                trace_id,
                self.settings.openai.model,
                session_id,
            )

            yield ChatStreamEvent(
                event="status",
                data={"phase": "thinking", "elapsed_ms": 0, "trace_id": trace_id},
            )

            try:
                # Đồng bộ history nếu session chưa có nhưng request có history
                if request.history and not self.agent.sessions.get_history(session_id):
                    for msg in request.history:
                        self.agent.sessions.append(session_id, {"role": msg.role, "content": msg.content})

                agent_res = await self.agent.chat(user_input=request.message, session_id=session_id)
                answer = agent_res.get("answer", "")
                tools_used = agent_res.get("tools_used", [])
                data_sources = agent_res.get("data_sources", [])

                yield ChatStreamEvent(
                    event="meta",
                    data={
                        "intent": "agent_tool_calling" if tools_used else "core_references",
                        "response_mode": "direct",
                        "references_used": data_sources,
                        "tools_used": tools_used,
                        "model": self.settings.openai.model,
                        "trace_id": trace_id,
                    },
                )

                first_token_at = time.perf_counter()
                ttft_ms = round((first_token_at - started) * 1000)
                self.logger.info(
                    "event=first_token trace_id=%s ttft_ms=%s",
                    trace_id,
                    ttft_ms,
                )

                # Stream các từ/cụm từ ra giao diện
                words = answer.split(" ")
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk_text = " ".join(words[i : i + chunk_size])
                    if i + chunk_size < len(words):
                        chunk_text += " "
                    yield ChatStreamEvent(event="delta", data={"text": chunk_text})
                    await asyncio.sleep(0.02)

                completed = time.perf_counter()
                total_ms = round((completed - started) * 1000)

                yield ChatStreamEvent(
                    event="done",
                    data={
                        "response_id": f"agent-{trace_id}",
                        "intent": "agent_tool_calling" if tools_used else "core_references",
                        "response_mode": "direct",
                        "references_used": data_sources,
                        "tools_used": tools_used,
                        "time_to_first_token_ms": ttft_ms,
                        "total_ms": total_ms,
                        "trace_id": trace_id,
                    },
                )
                self.logger.info(
                    "event=agent_chat_completed trace_id=%s stream=true response_id=agent-%s "
                    "output_chars=%s tools_used=%s data_sources=%s ttft_ms=%s total_ms=%s",
                    trace_id,
                    trace_id,
                    len(answer),
                    tools_used,
                    data_sources,
                    ttft_ms,
                    total_ms,
                )
                return
            except Exception as e:
                self.logger.warning("AgentCore stream gặp lỗi (%s), chuyển sang Responses API fallback...", e)

        # 2. Fallback sang Responses API truyền thống
        prepared = self._prepare(request)
        trace_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        first_token_at: float | None = None
        response_id = ""
        output_chars = 0
        stream = None
        self._log_started(trace_id, prepared, stream=True)

        yield ChatStreamEvent(
            event="status",
            data={"phase": "thinking", "elapsed_ms": 0, "trace_id": trace_id},
        )
        yield ChatStreamEvent(
            event="meta",
            data={
                "intent": prepared.intent,
                "response_mode": prepared.response_mode,
                "references_used": list(prepared.references_used),
                "model": self.settings.openai.model,
                "trace_id": trace_id,
            },
        )

        try:
            stream = await self.client.responses.create(  # type: ignore[union-attr]
                **prepared.kwargs,
                stream=True,
            )
            async for event in stream:
                event_type = event.type
                if event_type == "response.created":
                    response_id = event.response.id
                elif event_type == "response.output_text.delta":
                    now = time.perf_counter()
                    output_chars += len(event.delta)
                    if first_token_at is None:
                        first_token_at = now
                        self.logger.info(
                            "event=first_token trace_id=%s ttft_ms=%s",
                            trace_id,
                            round((now - started) * 1000),
                        )
                    yield ChatStreamEvent(event="delta", data={"text": event.delta})
                elif event_type == "response.completed":
                    response_id = event.response.id
                elif event_type in {"response.failed", "response.incomplete", "error"}:
                    raise RuntimeError(f"OpenAI stream ended with {event_type}")

            completed = time.perf_counter()
            total_ms = round((completed - started) * 1000)
            ttft_ms = round((first_token_at - started) * 1000) if first_token_at else None
            yield ChatStreamEvent(
                event="done",
                data={
                    "response_id": response_id,
                    "intent": prepared.intent,
                    "response_mode": prepared.response_mode,
                    "references_used": list(prepared.references_used),
                    "time_to_first_token_ms": ttft_ms,
                    "total_ms": total_ms,
                    "trace_id": trace_id,
                },
            )
            self.logger.info(
                "event=chat_completed trace_id=%s stream=true response_id=%s "
                "output_chars=%s ttft_ms=%s total_ms=%s",
                trace_id,
                response_id,
                output_chars,
                ttft_ms,
                total_ms,
            )
        except APIError as exc:
            self._log_provider_error(trace_id, started, exc, stream=True)
            raise ProviderRequestError(trace_id) from exc
        except Exception as exc:
            total_ms = round((time.perf_counter() - started) * 1000)
            self.logger.exception(
                "event=stream_failed trace_id=%s error_type=%s total_ms=%s",
                trace_id,
                type(exc).__name__,
                total_ms,
            )
            raise ProviderRequestError(trace_id) from exc
        finally:
            if stream is not None:
                await stream.close()

    def _log_started(
        self, trace_id: str, prepared: PreparedChat, *, stream: bool
    ) -> None:
        self.logger.info(
            "event=chat_started trace_id=%s stream=%s model=%s intent=%s "
            "response_mode=%s reference_count=%s instruction_chars=%s "
            "max_output_tokens=%s",
            trace_id,
            str(stream).lower(),
            self.settings.openai.model,
            prepared.intent,
            prepared.response_mode,
            len(prepared.references_used),
            prepared.instruction_chars,
            prepared.max_output_tokens,
        )

    def _log_provider_error(
        self, trace_id: str, started: float, exc: APIError, *, stream: bool
    ) -> None:
        status_code = getattr(exc, "status_code", None)
        request_id = getattr(exc, "request_id", None) or "-"
        total_ms = round((time.perf_counter() - started) * 1000)
        self.logger.exception(
            "event=provider_request_failed trace_id=%s stream=%s error_type=%s "
            "status_code=%s provider_request_id=%s total_ms=%s error=%r",
            trace_id,
            str(stream).lower(),
            type(exc).__name__,
            status_code,
            request_id,
            total_ms,
            str(exc)[:500],
        )
