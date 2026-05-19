from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.complaint import ComplaintFilters, ComplaintListResponse
from app.services.complaint_service import ComplaintService


class SearchService:
    def __init__(self) -> None:
        self.complaint_service = ComplaintService()

    async def keyword_search(self, db: AsyncSession, filters: ComplaintFilters) -> ComplaintListResponse:
        return await self.complaint_service.list_complaints(db, filters)
