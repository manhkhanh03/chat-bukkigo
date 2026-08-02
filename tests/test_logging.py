import logging

from chat_bukkigo.config import load_settings
from chat_bukkigo.logging_config import configure_logging


def test_logging_writes_to_rotating_file_without_secret(tmp_path) -> None:
    settings = load_settings()
    settings.logging.file = tmp_path / "chat.log"
    logger = configure_logging(settings)

    logging.getLogger("chat_bukkigo.service").info(
        "event=test trace_id=abc123 model=test-model"
    )
    for handler in logger.handlers:
        handler.flush()

    content = settings.log_path.read_text(encoding="utf-8")
    assert "event=test trace_id=abc123 model=test-model" in content
    if settings.api_key:
        assert settings.api_key.get_secret_value() not in content
