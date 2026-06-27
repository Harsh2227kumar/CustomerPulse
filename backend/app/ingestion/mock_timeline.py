import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

try:
    from app.communications.services import TimelineService as RealTimelineService  # type: ignore
except ImportError:
    RealTimelineService = None


class TimelineService:
    @staticmethod
    async def add_event(
        db: AsyncSession,
        complaint_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any] | None = None
    ) -> None:
        if RealTimelineService is not None:
            try:
                await RealTimelineService.add_event(db, complaint_id, event_type, actor, payload)
                return
            except Exception as exc:
                logger.error("Failed to write to real TimelineService: %s", exc)

        logger.info(
            "[MockTimelineService] Logged event - Complaint: %s, Event: %s, Actor: %s, Payload: %s",
            complaint_id,
            event_type,
            actor,
            payload
        )
