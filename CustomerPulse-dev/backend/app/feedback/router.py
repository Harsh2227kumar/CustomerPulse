from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.feedback.schemas import AgentFeedbackUpsertRequest, FeedbackAction, FeedbackListQuery, FeedbackListResponse, FeedbackRead
from app.feedback.service import ComplaintNotFoundError, FeedbackNotFoundError, FeedbackService

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback/{complaint_id}", response_model=FeedbackRead)
async def upsert_feedback(
    complaint_id: str,
    payload: AgentFeedbackUpsertRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> FeedbackRead:
    service = FeedbackService()
    try:
        result, created = await service.upsert_feedback(db, complaint_id, payload)
    except ComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found.") from exc
    response.status_code = 201 if created else 200
    return result


@router.get("/feedback/export")
async def export_feedback(
    db: AsyncSession = Depends(get_db_session),
) -> FastAPIResponse:
    service = FeedbackService()
    items = await service.export_feedback(db)
    payload = "\n".join(item.model_dump_json() for item in items)
    if payload:
        payload += "\n"
    return FastAPIResponse(content=payload, media_type="application/x-ndjson")


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    agent_id: str | None = Query(default=None),
    feedback_action: FeedbackAction | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> FeedbackListResponse:
    filters = FeedbackListQuery(
        limit=limit,
        offset=offset,
        agent_id=agent_id,
        feedback_action=feedback_action,
    )
    return await FeedbackService().list_feedback(db, filters)


@router.get("/feedback/{complaint_id}", response_model=FeedbackRead)
async def get_feedback(
    complaint_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> FeedbackRead:
    service = FeedbackService()
    try:
        return await service.get_feedback(db, complaint_id)
    except FeedbackNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Feedback not found.") from exc
