from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import Role
from app.core.security import Principal, require_roles
from app.db.session import get_db_session
from app.schemas.jobs import CreateProcessingJobRequest, ProcessingJobResponse
from app.services.job_service import JobNotFoundError, JobRequestError, JobService


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post(
    "/process",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_processing_job(
    request: CreateProcessingJobRequest,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> ProcessingJobResponse:
    service = JobService(settings)
    try:
        return await service.create_processing_job(
            db, request.complaint_ids, principal
        )
    except JobRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        service.close()


@router.post(
    "/embedding-backfill",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_embedding_backfill_job(
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> ProcessingJobResponse:
    service = JobService(settings)
    try:
        return await service.create_backfill_job(db, principal)
    except JobRequestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        service.close()


@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ProcessingJobResponse:
    service = JobService(settings)
    try:
        return await service.get_job(db, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    finally:
        service.close()


@router.post(
    "/{job_id}/retry",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> ProcessingJobResponse:
    service = JobService(settings)
    try:
        return await service.retry_job(db, job_id, principal)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    except JobRequestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        service.close()
