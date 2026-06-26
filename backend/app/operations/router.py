from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Role
from app.core.security import require_roles
from app.db.session import get_db_session
from app.operations.repository import OperationsRepository
from app.operations.schemas import (
    OperationsQueueItem,
    OperationsQueueQuery,
    OperationsQueueResponse,
)

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("/queue", response_model=OperationsQueueResponse)
async def get_operations_queue(
    filters: OperationsQueueQuery = Depends(),
    _principal=Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> OperationsQueueResponse:
    items, total = await OperationsRepository().get_queue(
        db, limit=filters.limit, offset=filters.offset,
    )
    return OperationsQueueResponse(
        items=[OperationsQueueItem.model_validate(item) for item in items],
        total=total,
        limit=filters.limit,
        offset=filters.offset,
    )
