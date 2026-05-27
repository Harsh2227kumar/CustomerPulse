from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.duplicates.schemas import (
    ChannelComparisonResponse,
    DuplicateDetectRequest,
    DuplicateDetectResponse,
    DuplicateDetectionType,
    DuplicateGroupListQuery,
    DuplicateGroupListResponse,
    DuplicateGroupRead,
    DuplicateGroupStatus,
    DuplicateMergeRequest,
    DuplicateRejectRequest,
)
from app.duplicates.service import (
    DuplicateComplaintNotFoundError,
    DuplicateComplaintNotInGroupError,
    DuplicateGroupNotFoundError,
    DuplicateService,
)

router = APIRouter(prefix="/api", tags=["duplicates"])


@router.post("/duplicates/detect", response_model=DuplicateDetectResponse)
async def detect_duplicates(
    payload: DuplicateDetectRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DuplicateDetectResponse:
    return await DuplicateService().detect_duplicates(db, payload)


@router.get("/duplicates", response_model=DuplicateGroupListResponse)
async def list_duplicate_groups(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    detection_type: DuplicateDetectionType | None = None,
    status: DuplicateGroupStatus | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> DuplicateGroupListResponse:
    filters = DuplicateGroupListQuery(
        limit=limit,
        offset=offset,
        detection_type=detection_type,
        status=status,
    )
    return await DuplicateService().list_groups(db, filters)


@router.get("/duplicates/channel-comparison", response_model=ChannelComparisonResponse)
async def get_channel_comparison(
    db: AsyncSession = Depends(get_db_session),
) -> ChannelComparisonResponse:
    return await DuplicateService().channel_comparison(db)


@router.get("/duplicates/{group_id}", response_model=DuplicateGroupRead)
async def get_duplicate_group(
    group_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> DuplicateGroupRead:
    try:
        return await DuplicateService().get_group(db, group_id)
    except DuplicateGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Duplicate group not found.") from exc


@router.post("/duplicates/{group_id}/merge", response_model=DuplicateGroupRead)
async def merge_duplicate_group(
    group_id: str,
    payload: DuplicateMergeRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DuplicateGroupRead:
    service = DuplicateService()
    try:
        return await service.merge_group(db, group_id, payload)
    except DuplicateGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Duplicate group not found.") from exc
    except DuplicateComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Canonical complaint not found.") from exc
    except DuplicateComplaintNotInGroupError as exc:
        raise HTTPException(status_code=400, detail="Canonical complaint is not part of this group.") from exc


@router.post("/duplicates/{group_id}/reject", response_model=DuplicateGroupRead)
async def reject_duplicate_group(
    group_id: str,
    payload: DuplicateRejectRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DuplicateGroupRead:
    try:
        return await DuplicateService().reject_group(db, group_id, payload)
    except DuplicateGroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Duplicate group not found.") from exc
