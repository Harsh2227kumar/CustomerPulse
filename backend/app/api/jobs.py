from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import JobStatus, JobType, Role
from app.core.security import Principal, require_roles
from app.db.session import get_db_session
from app.schemas.jobs import CreateProcessingJobRequest, JobListResponse, ProcessingJobResponse, ContinuousProcessingStatus
from app.services.job_service import ContinuousAIProcessor, JobNotFoundError, JobRequestError, JobService


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
    principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
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
    principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
) -> ProcessingJobResponse:
    service = JobService(settings)
    try:
        return await service.create_backfill_job(db, principal)
    except JobRequestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        service.close()


@router.post(
    "/continuous/start",
    response_model=ContinuousProcessingStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_continuous_processing(
    settings: Settings = Depends(get_settings),
    _principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
) -> ContinuousProcessingStatus:
    return await ContinuousAIProcessor.start(settings)


@router.post(
    "/continuous/stop",
    response_model=ContinuousProcessingStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def stop_continuous_processing(
    _principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
) -> ContinuousProcessingStatus:
    return await ContinuousAIProcessor.stop()


@router.get("/continuous/status", response_model=ContinuousProcessingStatus)
async def get_continuous_processing_status(
    _principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
) -> ContinuousProcessingStatus:
    return await ContinuousAIProcessor.status()


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    job_type: JobType | None = Query(default=None),
    status: JobStatus | None = Query(default=None),
    _principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> JobListResponse:
    service = JobService(settings)
    try:
        return await service.list_jobs(
            db,
            limit=limit,
            offset=offset,
            job_type=job_type,
            status=status,
        )
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
    principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
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
