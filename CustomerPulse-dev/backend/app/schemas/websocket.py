from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.constants import WebSocketEvent


class WebSocketMessage(BaseModel):
    event: WebSocketEvent
    complaint_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
