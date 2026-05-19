from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.schemas.ai_response import ProcessedComplaintResponse
from app.schemas.complaint import ComplaintProcessRequest
from app.services.processing_service import ProcessingService

router = APIRouter(prefix="/api", tags=["processing"])


@router.post("/process", response_model=ProcessedComplaintResponse)
async def process_complaint(
    complaint: ComplaintProcessRequest,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ProcessedComplaintResponse:
    service = ProcessingService(settings)
    return await service.process_complaint(db, complaint)
