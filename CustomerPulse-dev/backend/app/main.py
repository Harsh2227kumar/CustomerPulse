from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import complaints, health, ingestion, process, websocket
from app.analytics.router import router as analytics_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.feedback import router as feedback
from app.exports.api import routes as export_routes
from app.duplicates import router as duplicates
from app.sla.api import routes as sla_routes
from app.db.setup import run_startup_checks


settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await run_startup_checks(settings, prompt=True, verify_bedrock=True)
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(process.router)
app.include_router(feedback.router)
app.include_router(duplicates.router)
app.include_router(complaints.router)
app.include_router(ingestion.router)
app.include_router(analytics_router)
app.include_router(export_routes.router)
app.include_router(sla_routes.router)
app.include_router(websocket.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error at %s.", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url.path)},
    )
