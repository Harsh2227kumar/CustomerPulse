import asyncio
from contextlib import suppress
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.analytics.router import router as analytics_router
from app.api import auth, complaints, health, ingestion, jobs, process, review, websocket
from app.compliance import router as compliance_router
from app.communications.router import router as communications_router
from app.escalations.router import complaints_escalations_router, escalations_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.setup import run_startup_checks
from app.db.session import AsyncSessionLocal
from app.duplicates import router as duplicates_router
from app.exports.api import routes as export_routes
from app.feedback import router as feedback_router
from app.operations import router as operations_router
from app.services.embedding_service import EmbeddingService
from app.services.job_service import JobService, ProcessingJobWorker
from app.sla.api import routes as sla_routes


settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await run_startup_checks(settings, prompt=True, verify_bedrock=True)
    if settings.embedding_verify_on_startup:
        await EmbeddingService(
            settings.embedding_model,
            local_files_only=settings.embedding_local_files_only,
        ).ensure_ready()
    async with AsyncSessionLocal() as db:
        await JobService(settings).recover_abandoned_jobs(db)
    worker = ProcessingJobWorker(settings)
    worker_task = asyncio.create_task(worker.run())
    try:
        yield
    finally:
        worker.stop()
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(process.router)
app.include_router(complaints.router)
app.include_router(communications_router)
app.include_router(escalations_router)
app.include_router(complaints_escalations_router)
app.include_router(ingestion.router)
app.include_router(review.router)
app.include_router(jobs.router)
app.include_router(feedback_router.router)
app.include_router(duplicates_router.router)
app.include_router(analytics_router)
app.include_router(compliance_router.router)
app.include_router(export_routes.router)
app.include_router(sla_routes.router)
app.include_router(operations_router)
app.include_router(websocket.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error at %s.", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url.path)},
    )

