from fastapi.testclient import TestClient

from chat_bukkigo.config import load_settings
from chat_bukkigo.main import create_app


def client_without_api_key() -> TestClient:
    settings = load_settings()
    settings.api_key = None
    settings.openai.model = "gpt-5.6-terra"
    settings.use_custom_endpoint = False
    settings.custom_base_url = None
    return TestClient(create_app(settings))


def test_health_reports_missing_key_without_exposing_secrets() -> None:
    response = client_without_api_key().get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model": "gpt-5.6-terra",
        "api_key_configured": False,
        "endpoint_mode": "openai",
    }


def test_get_chat_returns_minimal_chat_screen() -> None:
    response = client_without_api_key().get("/v1/chat")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "id=\"composer\"" in response.text
    assert "Tổng" in response.text
    assert "/v1/chat/stream" in response.text


def test_chat_fails_cleanly_until_api_key_is_configured() -> None:
    response = client_without_api_key().post(
        "/v1/chat",
        json={"message": "Gợi ý nail Tết thanh lịch"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "OPENAI_API_KEY is not configured"}


def test_stream_fails_cleanly_until_api_key_is_configured() -> None:
    response = client_without_api_key().post(
        "/v1/chat/stream",
        json={"message": "Gợi ý nail Tết thanh lịch"},
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "OPENAI_API_KEY is not configured"}
