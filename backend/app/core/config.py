from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Literal

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
    bedrock_verify_on_startup: bool = Field(default=True)
    s3_bucket_name: str | None = None
    cfpb_s3_key: str | None = None
    aws_region: str = Field(default="ap-south-1", min_length=1)
    cfpb_ingestion_mode: Literal["csv", "athena"] = "csv"
    athena_database: str | None = None
    athena_table: str | None = None
    athena_output_location: str | None = None
    athena_workgroup: str = Field(default="primary", min_length=1)
    athena_query_timeout_seconds: float = Field(default=90.0, gt=0, le=300)

    cors_origins: str = ""
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_timeout_seconds: float = Field(default=30.0, gt=0)
    embedding_model: str = Field(default="all-MiniLM-L6-v2", min_length=1)
    embedding_verify_on_startup: bool = Field(default=False)
    embedding_local_files_only: bool = Field(default=False)
    similarity_threshold: float = Field(default=0.60, ge=0, le=1)
    similar_case_limit: int = Field(default=3, ge=1, le=10)
    batch_process_limit: int = Field(default=50, ge=1, le=200)
    embedding_backfill_limit: int = Field(default=100, ge=1, le=500)
    job_worker_poll_seconds: float = Field(default=1.0, gt=0, le=30)
    auth_users_json: str = "[]"

    # Email Intake Configuration
    email_intake_enabled: bool = Field(default=False)
    email_intake_imap_server: str = Field(default="imap.gmail.com")
    email_intake_imap_port: int = Field(default=993, ge=1, le=65535)
    email_intake_email: str = Field(default="support.customerpulse@gmail.com")
    email_intake_password: str = Field(default="")
    email_intake_poll_interval_seconds: int = Field(default=300, ge=10, le=86400)

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def auth_principals(self) -> dict[str, dict[str, str]]:
        parsed: Any = json.loads(self.auth_users_json)
        return {
            user["api_key"]: {
                "actor": user.get("actor", user["username"]),
                "role": user["role"],
            }
            for user in parsed
        }
    @property
    def s3_import_configured(self) -> bool:
        if not self.s3_bucket_name or not self.cfpb_s3_key:
            return False
        if self.cfpb_ingestion_mode == "athena":
            return bool(self.athena_database and self.athena_table and self.athena_output_location)
        return True

    @field_validator(
        "database_admin_url",
        "bedrock_api_key",
        "bedrock_base_url",
        "s3_bucket_name",
        "cfpb_s3_key",
        "athena_database",
        "athena_table",
        "athena_output_location",
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
        try:
            users = json.loads(self.auth_users_json)
        except json.JSONDecodeError as exc:
            raise ValueError("AUTH_USERS_JSON must contain valid JSON") from exc
        if not isinstance(users, list):
            raise ValueError("AUTH_USERS_JSON must be a list of user objects")
        for user in users:
            if not isinstance(user, dict):
                raise ValueError("AUTH_USERS_JSON includes an invalid user entry")
            if user.get("role") not in {"agent", "manager", "admin"}:
                raise ValueError("AUTH_USERS_JSON roles must be agent, manager, or admin")
            for field in ("username", "password", "api_key"):
                if not isinstance(user.get(field), str) or not user[field].strip():
                    raise ValueError(f"AUTH_USERS_JSON users must include {field}")
            actor = user.get("actor", user["username"])
            if not isinstance(actor, str) or not actor.strip():
                raise ValueError("AUTH_USERS_JSON users must include a valid actor")

        if self.email_intake_enabled:
            if not self.email_intake_email or not self.email_intake_email.strip():
                raise ValueError("EMAIL_INTAKE_EMAIL must be provided when EMAIL_INTAKE_ENABLED is true")
            if not self.email_intake_password or not self.email_intake_password.strip():
                raise ValueError("EMAIL_INTAKE_PASSWORD must be provided when EMAIL_INTAKE_ENABLED is true")

        return self



@lru_cache
def get_settings() -> Settings:
    return Settings()
