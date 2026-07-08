from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class S3ComplaintImportFilters(BaseModel):
    product: str | None = Field(default=None, max_length=255)
    sub_product: str | None = Field(default=None, max_length=255)
    issue: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    channel: str | None = Field(default=None, max_length=64)
    timely_response: bool | None = None
    date_received_min: date | None = None
    date_received_max: date | None = None
    max_records: int = Field(default=5, ge=1, le=50)

    @field_validator("product", "sub_product", "issue", "company", "channel", mode="before")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @model_validator(mode="after")
    def valid_date_range(self) -> "S3ComplaintImportFilters":
        if (
            self.date_received_min is not None
            and self.date_received_max is not None
            and self.date_received_min > self.date_received_max
        ):
            raise ValueError("date_received_min must be on or before date_received_max")
        return self


class S3SourceSummary(BaseModel):
    label: str


class S3ImportOptionsResponse(BaseModel):
    source: S3SourceSummary
    query_mode: Literal["csv", "athena"]
    available: bool = True
    unavailable_reason: str | None = None
    scanned_rows: int | None = None
    eligible_rows: int | None = None
    products: list[str]
    sub_products: list[str]
    issues: list[str]
    companies: list[str]
    channels: list[str]
    timely_responses: list[bool]
    date_received_min: date | None = None
    date_received_max: date | None = None


class S3ComplaintPreviewItem(BaseModel):
    complaint_id: str
    narrative: str
    product: str | None = None
    sub_product: str | None = None
    issue: str | None = None
    company: str | None = None
    channel: str | None = None
    timely_response: bool | None = None
    date_received: datetime | None = None


class S3ImportPreviewResponse(BaseModel):
    source: S3SourceSummary
    query_mode: Literal["csv", "athena"]
    scanned_rows: int
    matched_rows: int
    selected_rows: int
    result_limited: bool
    items: list[S3ComplaintPreviewItem]


class S3ImportLog(BaseModel):
    level: Literal["info", "success", "error"]
    message: str


class S3ImportResponse(BaseModel):
    status: Literal["success"]
    source: S3SourceSummary
    scanned_rows: int
    matched_rows: int
    imported_rows: int
    skipped_rows: int
    logs: list[S3ImportLog]


class ImportAuditLogItem(BaseModel):
    id: str
    actor: str
    filters: dict[str, Any]
    scanned_rows: int
    matched_rows: int
    imported_rows: int
    skipped_rows: int
    status: str
    error_code: str | None = None
    error_message: str | None = None
    athena_execution_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ImportAuditLogListResponse(BaseModel):
    items: list[ImportAuditLogItem]
    count: int


class EmailSyncResponse(BaseModel):
    status: str
    scanned_emails: int
    imported_emails: int
    skipped_emails: int
    failed_emails: int
    error_message: str | None = None


