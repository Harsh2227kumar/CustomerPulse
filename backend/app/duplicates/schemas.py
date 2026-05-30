from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Pagination


class DuplicateDetectionType(StrEnum):
    EXACT = "exact"
    NEAR = "near"


class DuplicateGroupStatus(StrEnum):
    DETECTED = "detected"
    MERGED = "merged"
    REJECTED = "rejected"


class DuplicateDetectRequest(BaseModel):
    exact_enabled: bool = True
    near_enabled: bool = True
    near_threshold: float = Field(default=0.92, ge=0.0, le=1.0)


class DuplicateDetectResponse(BaseModel):
    exact_groups_created: int
    near_groups_created: int
    total_groups_created: int


class DuplicateMemberRead(BaseModel):
    complaint_id: str
    complaint_pk: str
    channel: str | None = None
    product: str | None = None
    issue: str | None = None
    company: str | None = None
    narrative: str
    similarity_score: float | None = None
    is_primary: bool


class DuplicateGroupSummary(BaseModel):
    group_id: str
    detection_type: DuplicateDetectionType
    status: DuplicateGroupStatus
    exact_hash: str | None = None
    similarity_threshold: float | None = None
    canonical_complaint_id: str | None = None
    member_count: int
    created_at: datetime
    updated_at: datetime


class DuplicateGroupRead(DuplicateGroupSummary):
    merged_at: datetime | None = None
    rejected_at: datetime | None = None
    notes: str | None = None
    members: list[DuplicateMemberRead]


class DuplicateGroupListQuery(Pagination):
    detection_type: DuplicateDetectionType | None = None
    status: DuplicateGroupStatus | None = None


class DuplicateGroupListResponse(BaseModel):
    items: list[DuplicateGroupSummary]
    limit: int
    offset: int
    count: int


class DuplicateMergeRequest(BaseModel):
    canonical_complaint_id: str = Field(min_length=1, max_length=128)
    notes: str | None = None

    @field_validator("canonical_complaint_id")
    @classmethod
    def clean_canonical_complaint_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class DuplicateRejectRequest(BaseModel):
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class ChannelComparisonItem(BaseModel):
    channel_a: str
    channel_b: str
    group_count: int
    complaint_count: int


class ChannelComparisonResponse(BaseModel):
    items: list[ChannelComparisonItem]
