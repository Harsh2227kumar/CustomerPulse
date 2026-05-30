from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.base import Base
from app.db.session import engine
from app.models import ComplaintProcessingRun, ProcessingJob, ProcessingJobItem  # noqa: F401


async def create_extensions(db_engine: AsyncEngine = engine) -> None:
    async with db_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def init_db(db_engine: AsyncEngine = engine) -> None:
    await create_extensions(db_engine)
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection(db_engine: AsyncEngine = engine) -> bool:
    async with db_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
