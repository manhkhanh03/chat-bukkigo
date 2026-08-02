from __future__ import annotations

import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from .config import Settings, get_settings
from .logging_config import configure_logging
from .schemas import ChatRequest, ChatResponse, HealthResponse
from .service import ChatService, MissingAPIKeyError, ProviderRequestError

STATIC_DIR = Path(__file__).resolve().parent / "static"


def encode_sse(event: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def create_app(settings_override: Settings | None = None) -> FastAPI:
    settings = settings_override or get_settings()
    logger = configure_logging(settings)
    service = ChatService(settings)
    app = FastAPI(title=settings.app.name, version="0.1.0")
    logger.info(
        "event=application_started environment=%s model=%s endpoint_mode=%s "
        "base_url=%s log_file=%s",
        settings.app.environment,
        settings.openai.model,
        "custom" if settings.use_custom_endpoint else "openai",
        settings.custom_base_url if settings.use_custom_endpoint else "default",
        settings.log_path,
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            model=settings.openai.model,
            api_key_configured=settings.api_key is not None,
            endpoint_mode="custom" if settings.use_custom_endpoint else "openai",
        )

    @app.get(f"{settings.app.api_prefix}/chat", include_in_schema=False)
    async def chat_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "chat.html", media_type="text/html; charset=utf-8")

    @app.post(f"{settings.app.api_prefix}/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        try:
            return await service.chat(request)
        except MissingAPIKeyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ProviderRequestError as exc:
            raise HTTPException(
                status_code=502,
                detail={"message": str(exc), "trace_id": exc.trace_id},
            ) from exc

    @app.post(f"{settings.app.api_prefix}/chat/stream")
    async def chat_stream(request: ChatRequest) -> StreamingResponse:
        try:
            service.ensure_configured()
        except MissingAPIKeyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        async def events():
            try:
                async for item in service.stream_chat(request):
                    yield encode_sse(item.event, item.data)
            except ProviderRequestError as exc:
                yield encode_sse(
                    "error", {"message": str(exc), "trace_id": exc.trace_id}
                )
            except Exception:
                logger.exception("event=unhandled_stream_error")
                yield encode_sse("error", {"message": "Stream interrupted"})

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return app


app = create_app()


def run() -> None:
    uvicorn.run("chat_bukkigo.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
