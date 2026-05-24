import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.ingestion.cfpb_s3 import CfpbS3IngestionService, S3IngestionError
from app.schemas.ingestion import (
    S3ComplaintImportFilters,
    S3ImportOptionsResponse,
    S3ImportPreviewResponse,
    S3ImportResponse,
)


router = APIRouter(prefix="/api/ingestion/s3", tags=["ingestion"])
logger = logging.getLogger(__name__)


def _service(settings: Settings) -> CfpbS3IngestionService:
    try:
        return CfpbS3IngestionService(settings)
    except S3IngestionError as exc:
        logger.warning("S3 ingestion is not configured: %s", exc)
        raise HTTPException(status_code=503, detail="S3 complaint import is not configured.") from exc


@router.get("/options", response_model=S3ImportOptionsResponse)
async def get_import_options(
    settings: Settings = Depends(get_settings),
) -> S3ImportOptionsResponse:
    try:
        return await asyncio.to_thread(_service(settings).load_options)
    except S3IngestionError as exc:
        logger.exception("Unable to load S3 complaint import options.")
        raise HTTPException(status_code=502, detail="Unable to read the configured complaint source.") from exc


@router.post("/preview", response_model=S3ImportPreviewResponse)
async def preview_import(
    filters: S3ComplaintImportFilters,
    settings: Settings = Depends(get_settings),
) -> S3ImportPreviewResponse:
    try:
        return await asyncio.to_thread(_service(settings).preview, filters)
    except S3IngestionError as exc:
        logger.exception("Unable to preview S3 complaint import.")
        raise HTTPException(status_code=502, detail="Unable to read the configured complaint source.") from exc


@router.post("/import", response_model=S3ImportResponse)
async def import_complaints(
    filters: S3ComplaintImportFilters,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> S3ImportResponse:
    service = _service(settings)
    try:
        selected = await asyncio.to_thread(service.select_rows_for_import, filters)
        return await service.import_rows(db, filters, selected)
    except S3IngestionError as exc:
        logger.exception("Unable to select S3 complaint rows for import.")
        raise HTTPException(status_code=502, detail="Unable to read the configured complaint source.") from exc
    except Exception as exc:
        await db.rollback()
        logger.exception("Complaint import failed.")
        raise HTTPException(status_code=500, detail="Complaint import failed.") from exc
