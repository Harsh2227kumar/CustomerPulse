from datetime import datetime
from typing import Any, Literal, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field


class CommunicationEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_type: Literal["note"] = "note"
    message: str = Field(min_length=1, max_length=4000)


class CommunicationEntryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    complaint_id: str
    entry_type: str
    event_code: Optional[str] = None
    message: str
    actor: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    created_at: datetime


class TimelineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_id: str
    items: list[CommunicationEntryRead]
