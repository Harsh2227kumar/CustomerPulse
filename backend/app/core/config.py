from functools import lru_cache
from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded only from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "CustomerPulse AI Backend"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    database_url: str = Field(min_length=1)
    anthropic_api_key: str = Field(min_length=1)
    anthropic_model: str = Field(default="claude-3-5-sonnet-latest")

    cors_origins: list[str] = Field(default_factory=list)
    redis_url: str | None = None
    vector_dimensions: int = Field(default=384, ge=1)
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_timeout_seconds: float = Field(default=30.0, gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL SQLAlchemy URL")
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        AnyUrl(value)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
