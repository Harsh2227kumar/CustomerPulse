from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime settings loaded only from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "CustomerPulse AI Backend"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    database_url: str = Field(min_length=1)
    database_admin_url: str | None = None
    ai_provider: Literal["openai"] = Field(default="openai")
    openai_api_key: str = Field(min_length=1)
    openai_model: str = Field(default="gpt-4o-mini", min_length=1)
    openai_base_url: str | None = None
    s3_bucket_name: str | None = None

    cors_origins: str = ""
    redis_url: str | None = None
    vector_dimensions: int = Field(default=384, ge=1)
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_timeout_seconds: float = Field(default=30.0, gt=0)

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator(
        "database_admin_url",
        "openai_base_url",
        "s3_bucket_name",
        mode="before",
    )
    @classmethod
    def blank_string_to_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL SQLAlchemy URL")
        return cls._ensure_asyncpg_url(value)

    @field_validator("database_admin_url")
    @classmethod
    def validate_database_admin_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_ADMIN_URL must be a PostgreSQL SQLAlchemy URL")
        return cls._ensure_asyncpg_url(value)

    @staticmethod
    def _ensure_asyncpg_url(value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        AnyUrl(value)
        return value

    @model_validator(mode="after")
    def validate_ai_provider_settings(self) -> "Settings":
        if self.ai_provider != "openai":
            raise ValueError("Only OpenAI is supported for AI_PROVIDER")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
