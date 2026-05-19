from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.complaint import ComplaintFilters, ComplaintListResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=ComplaintListResponse)
async def search_complaints(
    q: str = Query(min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> ComplaintListResponse:
    filters = ComplaintFilters(search=q, limit=limit, offset=offset)
    return await SearchService().keyword_search(db, filters)
