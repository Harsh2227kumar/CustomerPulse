import asyncio
from datetime import UTC, datetime
import logging

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import (
    JobItemStatus,
    JobStatus,
    JobType,
    ProcessingStatus,
    ProcessingTrigger,
)
from app.core.security import Principal
from app.db.session import AsyncSessionLocal
from app.models.complaint import Complaint
from app.models.processing import ProcessingJob, ProcessingJobItem
from app.schemas.jobs import (
    JobCounts,
    JobItemResponse,
    ProcessingJobResponse,
)
from app.services.processing_service import ComplaintNotFoundError, ProcessingService


logger = logging.getLogger(__name__)


class JobNotFoundError(LookupError):
    pass


class JobRequestError(ValueError):
    pass


class JobService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.processing = ProcessingService(settings)

    async def create_processing_job(
        self, db: AsyncSession, complaint_ids: list[str], principal: Principal
    ) -> ProcessingJobResponse:
        identifiers = list(dict.fromkeys(value.strip() for value in complaint_ids if value.strip()))
        if not identifiers:
            raise JobRequestError("At least one complaint identifier is required.")
        if len(identifiers) > self.settings.batch_process_limit:
            raise JobRequestError(
                f"Processing jobs are limited to {self.settings.batch_process_limit} complaints."
            )
        existing = (
            await db.execute(
                select(Complaint).where(
                    or_(
                        Complaint.id.in_(identifiers),
                        Complaint.source_complaint_id.in_(identifiers),
                    )
                )
            )
        ).scalars().all()
        existing_ids = {
            value
            for complaint in existing
            for value in (complaint.id, complaint.source_complaint_id)
            if value
        }
        missing = [identifier for identifier in identifiers if identifier not in existing_ids]
        if missing:
            raise JobRequestError(
                "Unknown complaint identifiers: " + ", ".join(missing[:10])
            )
        return await self._create_job(
            db, JobType.PROCESS_COMPLAINTS, identifiers, principal.actor
        )

    async def create_backfill_job(
        self, db: AsyncSession, principal: Principal
    ) -> ProcessingJobResponse:
        complaints = (
            await db.execute(
                select(Complaint)
                .where(
                    Complaint.embedding.is_(None),
                    Complaint.ai_status.in_(
                        [
                            ProcessingStatus.PENDING.value,
                            ProcessingStatus.COMPLETED.value,
                            ProcessingStatus.HUMAN_REVIEW.value,
                        ]
                    ),
                )
                .order_by(Complaint.created_at.asc())
                .limit(self.settings.embedding_backfill_limit)
            )
        ).scalars().all()
        identifiers = [complaint.source_complaint_id or complaint.id for complaint in complaints]
        if not identifiers:
            raise JobRequestError("No complaints are eligible for embedding backfill.")
        return await self._create_job(
            db, JobType.EMBEDDING_BACKFILL, identifiers, principal.actor
        )

    async def get_job(self, db: AsyncSession, job_id: str) -> ProcessingJobResponse:
        job = await db.get(ProcessingJob, job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        items = (
            await db.execute(
                select(ProcessingJobItem)
                .where(ProcessingJobItem.job_id == job.id)
                .order_by(ProcessingJobItem.id.asc())
            )
        ).scalars().all()
        return self._response(job, items)

    async def retry_job(
        self, db: AsyncSession, job_id: str, principal: Principal
    ) -> ProcessingJobResponse:
        job = await db.get(ProcessingJob, job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        failed_items = (
            await db.execute(
                select(ProcessingJobItem).where(
                    ProcessingJobItem.job_id == job.id,
                    ProcessingJobItem.status == JobItemStatus.FAILED.value,
                )
            )
        ).scalars().all()
        if not failed_items:
            raise JobRequestError("This job has no failed items to retry.")
        for item in failed_items:
            item.attempt_history = (item.attempt_history or []) + [
                {
                    "attempt_count": item.attempt_count,
                    "status": item.status,
                    "error_message": item.error_message,
                    "result_payload": item.result_payload,
                    "finished_at": item.finished_at.isoformat() if item.finished_at else None,
                    "retried_by": principal.actor,
                }
            ]
            item.status = JobItemStatus.QUEUED.value
            item.error_message = None
            item.result_payload = None
            item.started_at = None
            item.finished_at = None
        job.status = JobStatus.QUEUED.value
        job.finished_at = None
        await db.commit()
        return await self.get_job(db, job.id)

    async def recover_abandoned_jobs(self, db: AsyncSession) -> None:
        await db.execute(
            update(ProcessingJobItem)
            .where(ProcessingJobItem.status == JobItemStatus.RUNNING.value)
            .values(
                status=JobItemStatus.FAILED.value,
                error_message="Worker restarted while item was running; retry is available.",
                finished_at=datetime.now(UTC),
            )
        )
        await db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.status == JobStatus.RUNNING.value)
            .values(status=JobStatus.COMPLETED_WITH_ERRORS.value, finished_at=datetime.now(UTC))
        )
        await db.commit()

    async def process_next_queued_job(self, db: AsyncSession) -> bool:
        job = (
            await db.execute(
                select(ProcessingJob)
                .where(ProcessingJob.status == JobStatus.QUEUED.value)
                .order_by(ProcessingJob.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
        ).scalar_one_or_none()
        if job is None:
            return False
        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.now(UTC)
        await db.commit()
        items = (
            await db.execute(
                select(ProcessingJobItem).where(
                    ProcessingJobItem.job_id == job.id,
                    ProcessingJobItem.status == JobItemStatus.QUEUED.value,
                )
            )
        ).scalars().all()
        for item in items:
            await self._execute_item(db, job, item)
        await self._finish_job(db, job.id)
        return True

    async def _execute_item(
        self, db: AsyncSession, job: ProcessingJob, item: ProcessingJobItem
    ) -> None:
        item.status = JobItemStatus.RUNNING.value
        item.attempt_count += 1
        item.started_at = datetime.now(UTC)
        await db.commit()
        try:
            if job.job_type == JobType.PROCESS_COMPLAINTS.value:
                response = await self.processing.process_imported_complaint(
                    db,
                    item.complaint_id,
                    trigger=ProcessingTrigger.BATCH_PROCESSING,
                    initiated_by=job.created_by,
                )
                item.status = (
                    JobItemStatus.HUMAN_REVIEW.value
                    if response.ai_status == ProcessingStatus.HUMAN_REVIEW.value
                    else JobItemStatus.COMPLETED.value
                )
                item.result_payload = response.model_dump(mode="json")
            else:
                complaint = await self.processing.embed_complaint(db, item.complaint_id)
                item.status = JobItemStatus.COMPLETED.value
                item.result_payload = {
                    "complaint_id": complaint.source_complaint_id or complaint.id,
                    "embedding_model": complaint.embedding_model,
                    "embedded_at": (
                        complaint.embedded_at.isoformat() if complaint.embedded_at else None
                    ),
                }
            item.error_message = None
        except ComplaintNotFoundError:
            item.status = JobItemStatus.FAILED.value
            item.error_message = "Complaint not found."
        except Exception:
            logger.exception("Job item failed for %s.", item.complaint_id)
            item.status = JobItemStatus.FAILED.value
            item.error_message = "Job item execution failed."
        item.finished_at = datetime.now(UTC)
        await db.commit()

    async def _finish_job(self, db: AsyncSession, job_id: str) -> None:
        job = await db.get(ProcessingJob, job_id)
        if job is None:
            return
        counts = await self._counts(db, job_id)
        if counts.failed == job.total_items:
            job.status = JobStatus.FAILED.value
        elif counts.failed:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value
        else:
            job.status = JobStatus.COMPLETED.value
        job.finished_at = datetime.now(UTC)
        await db.commit()

    async def _create_job(
        self, db: AsyncSession, job_type: JobType, identifiers: list[str], actor: str
    ) -> ProcessingJobResponse:
        job = ProcessingJob(
            job_type=job_type.value,
            status=JobStatus.QUEUED.value,
            created_by=actor,
            total_items=len(identifiers),
        )
        db.add(job)
        await db.flush()
        db.add_all(
            [
                ProcessingJobItem(job_id=job.id, complaint_id=identifier)
                for identifier in identifiers
            ]
        )
        await db.commit()
        return await self.get_job(db, job.id)

    async def _counts(self, db: AsyncSession, job_id: str) -> JobCounts:
        results = (
            await db.execute(
                select(ProcessingJobItem.status, func.count())
                .where(ProcessingJobItem.job_id == job_id)
                .group_by(ProcessingJobItem.status)
            )
        ).all()
        counts = {status: count for status, count in results}
        return JobCounts(
            queued=counts.get(JobItemStatus.QUEUED.value, 0),
            running=counts.get(JobItemStatus.RUNNING.value, 0),
            completed=counts.get(JobItemStatus.COMPLETED.value, 0),
            human_review=counts.get(JobItemStatus.HUMAN_REVIEW.value, 0),
            failed=counts.get(JobItemStatus.FAILED.value, 0),
        )

    def _response(
        self, job: ProcessingJob, items: list[ProcessingJobItem]
    ) -> ProcessingJobResponse:
        counts = JobCounts()
        for item in items:
            if hasattr(counts, item.status):
                setattr(counts, item.status, getattr(counts, item.status) + 1)
        return ProcessingJobResponse(
            job_id=job.id,
            job_type=job.job_type,
            status=job.status,
            total_items=job.total_items,
            counts=counts,
            created_by=job.created_by,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            items=[
                JobItemResponse(
                    complaint_id=item.complaint_id,
                    status=item.status,
                    attempt_count=item.attempt_count,
                    error_message=item.error_message,
                    attempt_history=item.attempt_history or [],
                )
                for item in items
            ],
        )


class ProcessingJobWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        while not self._stopped.is_set():
            try:
                async with AsyncSessionLocal() as db:
                    handled = await JobService(self.settings).process_next_queued_job(db)
            except Exception:
                logger.exception("Background processing job worker failed.")
                handled = False
            if not handled:
                try:
                    await asyncio.wait_for(
                        self._stopped.wait(), timeout=self.settings.job_worker_poll_seconds
                    )
                except TimeoutError:
                    pass

    def stop(self) -> None:
        self._stopped.set()
