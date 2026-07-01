import asyncio
from datetime import UTC, datetime
import logging

from sqlalchemy import desc, func, nullslast, or_, select, update
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
    JobListResponse,
    ProcessingJobResponse,
    ContinuousProcessingStatus,
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

    def close(self) -> None:
        self.processing.close()

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

    async def list_jobs(
        self,
        db: AsyncSession,
        *,
        limit: int,
        offset: int,
        job_type: JobType | None = None,
        status: JobStatus | None = None,
    ) -> JobListResponse:
        filters = []
        if job_type is not None:
            filters.append(ProcessingJob.job_type == job_type.value)
        if status is not None:
            filters.append(ProcessingJob.status == status.value)

        total_count = (
            await db.execute(select(func.count(ProcessingJob.id)).where(*filters))
        ).scalar_one()
        jobs = (
            await db.execute(
                select(ProcessingJob)
                .where(*filters)
                .order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        responses: list[ProcessingJobResponse] = []
        for job in jobs:
            items = (
                await db.execute(
                    select(ProcessingJobItem)
                    .where(ProcessingJobItem.job_id == job.id)
                    .order_by(ProcessingJobItem.id.asc())
                )
            ).scalars().all()
            responses.append(self._response(job, items))

        return JobListResponse(
            items=responses,
            total_count=total_count,
            limit=limit,
            offset=offset,
        )

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
                    job_id=item.job_id,
                    complaint_id=item.complaint_id,
                    status=item.status,
                    attempt_count=item.attempt_count,
                    error_message=item.error_message,
                    attempt_history=item.attempt_history or [],
                    started_at=item.started_at,
                    finished_at=item.finished_at,
                )
                for item in items
            ],
        )


class ContinuousAIProcessor:
    _task: asyncio.Task[None] | None = None
    _stop_requested = False
    _current_job_id: str | None = None
    _current_complaint_id: str | None = None
    _processed_count = 0
    _last_message: str | None = "Continuous AI processor is stopped."
    _actor = "continuous_ai_processor"

    @classmethod
    async def start(cls, settings: Settings) -> ContinuousProcessingStatus:
        if cls._task is not None and not cls._task.done():
            return await cls.status()
        cls._stop_requested = False
        cls._processed_count = 0
        cls._last_message = "Continuous AI processor started."
        cls._task = asyncio.create_task(cls._run(settings))
        return await cls.status()

    @classmethod
    async def stop(cls) -> ContinuousProcessingStatus:
        cls._stop_requested = True
        if cls._task is None or cls._task.done():
            cls._last_message = "Continuous AI processor is stopped."
        else:
            cls._last_message = "Stop requested. Current complaint will finish before the processor stops."
        return await cls.status()

    @classmethod
    async def status(cls) -> ContinuousProcessingStatus:
        running = cls._task is not None and not cls._task.done()
        async with AsyncSessionLocal() as db:
            history = await cls._history(db)
        return ContinuousProcessingStatus(
            running=running,
            stopping=cls._stop_requested and running,
            current_job_id=cls._current_job_id if running else None,
            current_complaint_id=cls._current_complaint_id if running else None,
            processed_count=cls._processed_count,
            last_message=cls._last_message,
            history=history,
        )

    @classmethod
    async def _run(cls, settings: Settings) -> None:
        while not cls._stop_requested:
            service = JobService(settings)
            try:
                async with AsyncSessionLocal() as db:
                    complaint = await cls._next_important_complaint(db)
                    if complaint is None:
                        cls._last_message = "No important pending complaints are available."
                        break
                    identifier = complaint.source_complaint_id or complaint.id
                    cls._current_complaint_id = identifier
                    job = await service._create_job(
                        db,
                        JobType.PROCESS_COMPLAINTS,
                        [identifier],
                        cls._actor,
                    )
                    cls._current_job_id = job.job_id
                    cls._last_message = f"Processing important complaint {identifier}."
                await cls._wait_for_job(settings, cls._current_job_id)
                cls._processed_count += 1
            except Exception:
                logger.exception("Continuous AI processor failed.")
                cls._last_message = "Continuous AI processor failed; restart is available."
                break
            finally:
                service.close()
                cls._current_job_id = None
                cls._current_complaint_id = None
        if cls._stop_requested:
            cls._last_message = "Continuous AI processor stopped."
        cls._stop_requested = False

    @classmethod
    async def _next_important_complaint(cls, db: AsyncSession) -> Complaint | None:
        active_identifiers = (
            await db.execute(
                select(ProcessingJobItem.complaint_id)
                .join(ProcessingJob, ProcessingJob.id == ProcessingJobItem.job_id)
                .where(
                    ProcessingJob.job_type == JobType.PROCESS_COMPLAINTS.value,
                    ProcessingJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
                )
            )
        ).scalars().all()
        active = set(active_identifiers)
        stmt = (
            select(Complaint)
            .where(Complaint.ai_status.in_([ProcessingStatus.PENDING.value, ProcessingStatus.FAILED.value]))
            .order_by(nullslast(desc(Complaint.urgency_score)), desc(Complaint.created_at))
            .limit(25)
        )
        candidates = (await db.execute(stmt)).scalars().all()
        for complaint in candidates:
            identifiers = {complaint.id}
            if complaint.source_complaint_id:
                identifiers.add(complaint.source_complaint_id)
            if not identifiers.intersection(active):
                return complaint
        return None

    @classmethod
    async def _wait_for_job(cls, settings: Settings, job_id: str | None) -> None:
        if job_id is None:
            return
        terminal = {
            JobStatus.COMPLETED.value,
            JobStatus.COMPLETED_WITH_ERRORS.value,
            JobStatus.FAILED.value,
        }
        while True:
            async with AsyncSessionLocal() as db:
                job = await db.get(ProcessingJob, job_id)
                if job is None or job.status in terminal:
                    return
            await asyncio.sleep(settings.job_worker_poll_seconds)

    @classmethod
    async def _history(cls, db: AsyncSession) -> list[JobItemResponse]:
        items = (
            await db.execute(
                select(ProcessingJobItem)
                .join(ProcessingJob, ProcessingJob.id == ProcessingJobItem.job_id)
                .where(ProcessingJob.created_by == cls._actor)
                .order_by(desc(ProcessingJob.created_at), desc(ProcessingJobItem.started_at), desc(ProcessingJobItem.id))
                .limit(50)
            )
        ).scalars().all()
        return [
            JobItemResponse(
                job_id=item.job_id,
                complaint_id=item.complaint_id,
                status=item.status,
                attempt_count=item.attempt_count,
                error_message=item.error_message,
                attempt_history=item.attempt_history or [],
                started_at=item.started_at,
                finished_at=item.finished_at,
            )
            for item in items
        ]


class ProcessingJobWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        while not self._stopped.is_set():
            try:
                async with AsyncSessionLocal() as db:
                    service = JobService(self.settings)
                    try:
                        handled = await service.process_next_queued_job(db)
                    finally:
                        service.close()
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

