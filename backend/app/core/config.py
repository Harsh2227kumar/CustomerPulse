from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator, model_validator
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
    ai_provider: str = Field(default="bedrock", pattern="^bedrock$")
    bedrock_api_key: str | None = None
    bedrock_region: str = Field(default="us-east-1", min_length=1)
    bedrock_model: str = Field(default="global.anthropic.claude-sonnet-4-6", min_length=1)
    bedrock_base_url: str | None = None
    s3_bucket_name: str | None = None
    cfpb_s3_key: str | None = None
    aws_region: str = Field(default="ap-south-1", min_length=1)

    cors_origins: str = ""
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_timeout_seconds: float = Field(default=30.0, gt=0)

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def s3_import_configured(self) -> bool:
        return bool(self.s3_bucket_name and self.cfpb_s3_key)

    @field_validator(
        "database_admin_url",
        "bedrock_api_key",
        "bedrock_base_url",
        "s3_bucket_name",
        "cfpb_s3_key",
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

    @model_validator(mode="after")
    def validate_service_settings(self) -> "Settings":
        if not self.bedrock_api_key:
            raise ValueError("BEDROCK_API_KEY is required when AI_PROVIDER=bedrock")
        if bool(self.s3_bucket_name) != bool(self.cfpb_s3_key):
            raise ValueError("S3_BUCKET_NAME and CFPB_S3_KEY must be configured together")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
