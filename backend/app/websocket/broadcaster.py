from app.core.constants import WebSocketEvent
from app.schemas.websocket import WebSocketMessage
from app.websocket.manager import manager


async def broadcast_processing_event(
    event: WebSocketEvent,
    complaint_id: str | None = None,
    payload: dict | None = None,
) -> None:
    await manager.broadcast(
        WebSocketMessage(
            event=event,
            complaint_id=complaint_id,
            payload=payload or {},
        )
    )
