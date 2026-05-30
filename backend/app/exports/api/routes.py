from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Role
from app.core.security import require_roles
from app.db.session import get_db_session
from app.exports.schemas.export_schemas import (
    AnalyticsCSVExportQuery,
    ComplaintCSVExportQuery,
    ComplaintPDFExportQuery,
    FeedbackCSVExportQuery,
)
from app.exports.services.csv_service import CSVExportService
from app.exports.services.pdf_service import PDFExportService

router = APIRouter(prefix="/api/exports", tags=["Exports"])


@router.get("/complaints/csv")
async def export_complaints_csv(
    filters: Annotated[ComplaintCSVExportQuery, Depends()],
    _principal=Depends(require_roles(Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    timestamp = _build_timestamp()
    headers = {
        "Content-Disposition": f'attachment; filename="complaints_{timestamp}.csv"',
    }
    return StreamingResponse(
        CSVExportService().stream_complaints_csv(db, filters),
        media_type="text/csv",
        headers=headers,
    )


@router.get("/complaints/pdf")
async def export_complaints_pdf(
    filters: Annotated[ComplaintPDFExportQuery, Depends()],
    _principal=Depends(require_roles(Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    timestamp = _build_timestamp()
    headers = {
        "Content-Disposition": f'attachment; filename="CustomerPulse_Report_{timestamp}.pdf"',
    }
    pdf_bytes = await PDFExportService().build_complaints_report_pdf(db, filters)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers=headers,
    )


@router.get("/analytics/csv")
async def export_analytics_csv(
    filters: Annotated[AnalyticsCSVExportQuery, Depends()],
    _principal=Depends(require_roles(Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    timestamp = _build_timestamp()
    headers = {
        "Content-Disposition": f'attachment; filename="analytics_{timestamp}.csv"',
    }
    return StreamingResponse(
        CSVExportService().stream_analytics_csv(db, filters),
        media_type="text/csv",
        headers=headers,
    )


@router.get("/feedback/csv")
async def export_feedback_csv(
    filters: Annotated[FeedbackCSVExportQuery, Depends()],
    _principal=Depends(require_roles(Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    timestamp = _build_timestamp()
    headers = {
        "Content-Disposition": f'attachment; filename="feedback_{timestamp}.csv"',
    }
    return StreamingResponse(
        CSVExportService().stream_feedback_csv(db, filters),
        media_type="text/csv",
        headers=headers,
    )


def _build_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
