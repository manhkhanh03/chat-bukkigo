import pytest
from pydantic import ValidationError

from chat_bukkigo.config import Settings, load_settings


def test_custom_endpoint_is_loaded_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_USE_CUSTOM_ENDPOINT", "true")
    monkeypatch.setenv("OPENAI_CUSTOM_BASE_URL", "http://localhost:20128/v1")

    settings = load_settings()

    assert settings.use_custom_endpoint is True
    assert settings.custom_base_url == "http://localhost:20128/v1"


def test_default_endpoint_does_not_require_custom_url(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_USE_CUSTOM_ENDPOINT", "false")
    monkeypatch.setenv("OPENAI_CUSTOM_BASE_URL", "")

    settings = load_settings()

    assert settings.use_custom_endpoint is False
    assert settings.custom_base_url is None


def test_enabled_custom_endpoint_requires_url() -> None:
    with pytest.raises(ValidationError, match="OPENAI_CUSTOM_BASE_URL"):
        Settings.model_validate(
            {
                "app": {},
                "openai": {},
                "skill": {},
                "use_custom_endpoint": True,
            }
        )


def test_logging_environment_overrides(monkeypatch, tmp_path) -> None:
    target = tmp_path / "diagnostics.log"
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_FILE", str(target))

    settings = load_settings()

    assert settings.logging.level == "DEBUG"
    assert settings.log_path == target
