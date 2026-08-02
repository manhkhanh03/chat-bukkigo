from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AppConfig(BaseModel):
    name: str = "Chat Bukkigo"
    environment: str = "development"
    api_prefix: str = "/v1"


class OpenAIConfig(BaseModel):
    model: str = "gpt-5.6-terra"
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"
    verbosity: Literal["low", "medium", "high"] = "medium"
    max_output_tokens: int = Field(default=900, ge=100, le=8000)
    timeout_seconds: float = Field(default=45, gt=0, le=300)
    max_retries: int = Field(default=2, ge=0, le=5)
    store: bool = False


class SkillConfig(BaseModel):
    path: Path = Path("skills/nail-beauty-consultant")
    max_history_messages: int = Field(default=12, ge=0, le=50)


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    file: Path = Path("logs/chat-bukkigo.log")
    max_bytes: int = Field(default=5_000_000, ge=10_000)
    backup_count: int = Field(default=3, ge=1, le=20)


class Settings(BaseModel):
    app: AppConfig
    openai: OpenAIConfig
    skill: SkillConfig
    logging: LoggingConfig = LoggingConfig()
    api_key: SecretStr | None = None
    safety_salt: SecretStr | None = None
    use_custom_endpoint: bool = False
    custom_base_url: str | None = None
    project_root: Path = PROJECT_ROOT

    @model_validator(mode="after")
    def validate_custom_endpoint(self) -> Settings:
        if self.use_custom_endpoint and not self.custom_base_url:
            raise ValueError(
                "OPENAI_CUSTOM_BASE_URL is required when "
                "OPENAI_USE_CUSTOM_ENDPOINT=true"
            )
        return self

    @property
    def skill_path(self) -> Path:
        if self.skill.path.is_absolute():
            return self.skill.path
        return self.project_root / self.skill.path

    @property
    def log_path(self) -> Path:
        if self.logging.file.is_absolute():
            return self.logging.file
        return self.project_root / self.logging.file


def load_settings(config_path: str | Path | None = None) -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    selected = Path(config_path or os.getenv("APP_CONFIG_PATH", "config/app.yaml"))
    if not selected.is_absolute():
        selected = PROJECT_ROOT / selected

    with selected.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream) or {}

    openai_data = dict(raw.get("openai", {}))
    if model_override := os.getenv("OPENAI_MODEL"):
        openai_data["model"] = model_override

    return Settings(
        app=AppConfig.model_validate(raw.get("app", {})),
        openai=OpenAIConfig.model_validate(openai_data),
        skill=SkillConfig.model_validate(raw.get("skill", {})),
        logging=LoggingConfig.model_validate(
            {
                **raw.get("logging", {}),
                **({"level": value.upper()} if (value := os.getenv("LOG_LEVEL")) else {}),
                **({"file": value} if (value := os.getenv("LOG_FILE")) else {}),
            }
        ),
        api_key=SecretStr(value) if (value := os.getenv("OPENAI_API_KEY")) else None,
        safety_salt=SecretStr(value) if (value := os.getenv("APP_SAFETY_SALT")) else None,
        use_custom_endpoint=os.getenv("OPENAI_USE_CUSTOM_ENDPOINT", "false").casefold()
        in {"1", "true", "yes", "on"},
        custom_base_url=(os.getenv("OPENAI_CUSTOM_BASE_URL") or "").strip() or None,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
