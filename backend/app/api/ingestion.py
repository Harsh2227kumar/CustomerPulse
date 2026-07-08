import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import Role
from app.core.security import Principal, require_roles
from app.db.session import get_db_session
from app.ingestion.cfpb_s3 import (
    CfpbS3IngestionService,
    S3IngestionError,
    S3QueryModeRequiredError,
    S3CredentialsMissingError,
    AthenaTimeoutError,
    AthenaTableMissingError,
    S3SourceUnavailableError,
)
from app.ingestion.models import ImportAuditLog
from app.schemas.ingestion import (
    S3ComplaintImportFilters,
    S3ImportOptionsResponse,
    S3ImportPreviewResponse,
    S3ImportResponse,
    ImportAuditLogListResponse,
    ImportAuditLogItem,
)

router = APIRouter(prefix="/api/ingestion/s3", tags=["ingestion"])
logger = logging.getLogger(__name__)


def _error_detail(exc: S3IngestionError) -> dict[str, str]:
    return {"code": exc.code, "message": str(exc)}


def _service(settings: Settings) -> CfpbS3IngestionService:
    try:
        return CfpbS3IngestionService(settings)
    except S3CredentialsMissingError as exc:
        logger.warning("S3 ingestion credentials missing or invalid: %s", exc)
        raise HTTPException(status_code=424, detail=_error_detail(exc)) from exc
    except S3IngestionError as exc:
        logger.warning("S3 ingestion is not configured: %s", exc)
        raise HTTPException(status_code=503, detail=_error_detail(exc)) from exc


def handle_ingestion_exception(exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, S3CredentialsMissingError):
        raise HTTPException(status_code=424, detail=_error_detail(exc))
    if isinstance(exc, AthenaTimeoutError):
        raise HTTPException(status_code=504, detail=_error_detail(exc))
    if isinstance(exc, AthenaTableMissingError):
        raise HTTPException(status_code=404, detail=_error_detail(exc))
    if isinstance(exc, S3SourceUnavailableError):
        raise HTTPException(status_code=503, detail=_error_detail(exc))
    if isinstance(exc, S3QueryModeRequiredError):
        raise HTTPException(
            status_code=409,
            detail=_error_detail(exc),
        )
    if isinstance(exc, S3IngestionError):
        raise HTTPException(status_code=502, detail=_error_detail(exc))
    raise exc


@router.get("/options", response_model=S3ImportOptionsResponse)
async def get_import_options(
    settings: Settings = Depends(get_settings),
) -> S3ImportOptionsResponse:
    try:
        return await asyncio.to_thread(_service(settings).load_options)
    except Exception as exc:
        handle_ingestion_exception(exc)


@router.post("/preview", response_model=S3ImportPreviewResponse)
async def preview_import(
    filters: S3ComplaintImportFilters,
    settings: Settings = Depends(get_settings),
) -> S3ImportPreviewResponse:
    try:
        return await asyncio.to_thread(_service(settings).preview, filters)
    except Exception as exc:
        handle_ingestion_exception(exc)


@router.post("/import", response_model=S3ImportResponse)
async def import_complaints(
    filters: S3ComplaintImportFilters,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> S3ImportResponse:
    service = _service(settings)
    actor = principal.actor
    execution_id = None
    try:
        selected = await asyncio.to_thread(service.select_rows_for_import, filters)
        execution_id = service.last_execution_id
        scanned, matched, skipped, rows = selected
        
        if len(rows) == 0:
            audit_log = ImportAuditLog(
                actor=actor,
                filters=filters.model_dump(),
                scanned_rows=scanned,
                matched_rows=matched,
                imported_rows=0,
                skipped_rows=skipped,
                status="failed",
                error_code="no_matching_rows",
                error_message="No matching rows found in S3/Athena for the specified filters.",
                athena_execution_id=execution_id
            )
            db.add(audit_log)
            await db.commit()
            raise HTTPException(status_code=422, detail="No matching rows found to import.")

        res = await service.import_rows(db, filters, selected)
        
        # Create timeline events
        from app.ingestion.mock_timeline import TimelineService
        for row in rows:
            await TimelineService.add_event(
                db=db,
                complaint_id=row["id"],
                event_type="cfpb_import",
                actor=actor,
                payload={
                    "source_complaint_id": row["source_complaint_id"],
                    "channel": row["channel"],
                    "date_received": row["date_received"].isoformat() if row["date_received"] else None
                }
            )
        
        audit_log = ImportAuditLog(
            actor=actor,
            filters=filters.model_dump(),
            scanned_rows=res.scanned_rows,
            matched_rows=res.matched_rows,
            imported_rows=res.imported_rows,
            skipped_rows=res.skipped_rows,
            status="success",
            athena_execution_id=execution_id
        )
        db.add(audit_log)
        await db.commit()
        return res

    except Exception as exc:
        await db.rollback()
        error_code = "source_unavailable"
        if isinstance(exc, S3CredentialsMissingError):
            error_code = "credentials_missing"
        elif isinstance(exc, AthenaTimeoutError):
            error_code = "athena_timeout"
        elif isinstance(exc, AthenaTableMissingError):
            error_code = "athena_table_missing"
        elif isinstance(exc, HTTPException) and exc.status_code == 422:
            error_code = "no_matching_rows"
            
        try:
            audit_log = ImportAuditLog(
                actor=actor,
                filters=filters.model_dump(),
                status="failed",
                error_code=error_code,
                error_message=str(exc),
                athena_execution_id=execution_id
            )
            db.add(audit_log)
            await db.commit()
        except Exception as log_exc:
            logger.exception("Failed to write import audit log: %s", log_exc)
            
        handle_ingestion_exception(exc)


@router.get("/audit-logs", response_model=ImportAuditLogListResponse)
async def get_import_audit_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    _principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> ImportAuditLogListResponse:
    try:
        # Fetch total count
        count_stmt = select(func.count()).select_from(ImportAuditLog)
        total_count = (await db.execute(count_stmt)).scalar_one()

        # Fetch page
        stmt = select(ImportAuditLog).order_by(desc(ImportAuditLog.created_at)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        items = result.scalars().all()

        return ImportAuditLogListResponse(
            items=[ImportAuditLogItem.model_validate(item) for item in items],
            count=total_count,
        )
    except Exception as exc:
        logger.exception("Failed to fetch import audit logs.")
        raise HTTPException(status_code=500, detail="Failed to fetch import audit logs.") from exc

