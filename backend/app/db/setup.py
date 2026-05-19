import asyncio
import logging
import sys
from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.ai.openai.client import OpenAIClient
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.models.complaint import Complaint

logger = logging.getLogger(__name__)


class SetupError(RuntimeError):
    """Raised when automatic backend setup cannot complete."""


@dataclass(frozen=True)
class DatabaseSetupStatus:
    database_exists: bool
    vector_extension_exists: bool
    complaints_table_exists: bool
    missing_columns: tuple[str, ...]
    missing_indexes: tuple[str, ...]

    @property
    def schema_ready(self) -> bool:
        return (
            self.database_exists
            and self.vector_extension_exists
            and self.complaints_table_exists
            and not self.missing_columns
            and not self.missing_indexes
        )


def _make_engine(url: str, *, isolation_level: str | None = None) -> AsyncEngine:
    kwargs = {"pool_pre_ping": True, "future": True}
    if isolation_level:
        kwargs["isolation_level"] = isolation_level
    return create_async_engine(url, **kwargs)


def _target_database_name(database_url: str) -> str:
    database = make_url(database_url).database
    if not database:
        raise SetupError("DATABASE_URL must include a database name.")
    return database


def _admin_database_url(settings: Settings) -> str:
    if settings.database_admin_url:
        return settings.database_admin_url
    url = make_url(settings.database_url)
    return str(url.set(database="postgres"))


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


EXPECTED_COMPLAINT_COLUMNS: dict[str, str] = {
    "id": "VARCHAR(64)",
    "source_complaint_id": "VARCHAR(128)",
    "narrative": "TEXT",
    "channel": "VARCHAR(64)",
    "product": "VARCHAR(255)",
    "sub_product": "VARCHAR(255)",
    "issue": "VARCHAR(255)",
    "sub_issue": "VARCHAR(255)",
    "company": "VARCHAR(255)",
    "company_response": "VARCHAR(255)",
    "timely_response": "BOOLEAN",
    "date_received": "TIMESTAMP WITH TIME ZONE",
    "sentiment": "VARCHAR(32)",
    "category": "VARCHAR(255)",
    "urgency_score": "INTEGER",
    "churn_risk": "VARCHAR(32)",
    "draft_response": "TEXT",
    "next_action": "TEXT",
    "confidence_scores": "JSONB",
    "ai_confidence": "DOUBLE PRECISION",
    "ai_reasoning": "TEXT",
    "embedding": "VECTOR(384)",
    "processed_at": "TIMESTAMP WITH TIME ZONE",
    "ai_status": "VARCHAR(32)",
    "retry_count": "INTEGER",
    "error_message": "TEXT",
    "created_at": "TIMESTAMP WITH TIME ZONE",
    "updated_at": "TIMESTAMP WITH TIME ZONE",
}


async def _prompt_yes_no(question: str) -> bool:
    if not sys.stdin or not sys.stdin.isatty():
        raise SetupError(f"{question} Cannot prompt because terminal input is unavailable.")
    answer = await asyncio.to_thread(input, f"{question} [y/N] ")
    return answer.strip().lower() in {"y", "yes"}


async def database_exists(settings: Settings) -> bool:
    admin_engine = _make_engine(_admin_database_url(settings))
    database_name = _target_database_name(settings.database_url)
    try:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name},
            )
            return result.scalar_one_or_none() == 1
    finally:
        await admin_engine.dispose()


async def create_database(settings: Settings) -> None:
    admin_engine = _make_engine(_admin_database_url(settings), isolation_level="AUTOCOMMIT")
    database_name = _target_database_name(settings.database_url)
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(text(f"CREATE DATABASE {_quote_identifier(database_name)}"))
    finally:
        await admin_engine.dispose()


async def inspect_database(settings: Settings) -> DatabaseSetupStatus:
    if not await database_exists(settings):
        return DatabaseSetupStatus(
            database_exists=False,
            vector_extension_exists=False,
            complaints_table_exists=False,
            missing_columns=tuple(EXPECTED_COMPLAINT_COLUMNS),
            missing_indexes=tuple(index.name or "" for index in Complaint.__table__.indexes),
        )

    engine = _make_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            vector_result = await conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            table_result = await conn.execute(text("SELECT to_regclass('public.complaints')"))
            complaints_table_exists = table_result.scalar_one_or_none() is not None
            existing_index_names: set[str] = set()
            existing_column_names: set[str] = set()
            if complaints_table_exists:
                existing_indexes = await conn.run_sync(
                    lambda sync_conn: inspect(sync_conn).get_indexes("complaints")
                )
                existing_index_names = {index["name"] for index in existing_indexes}
                existing_columns = await conn.run_sync(
                    lambda sync_conn: inspect(sync_conn).get_columns("complaints")
                )
                existing_column_names = {column["name"] for column in existing_columns}
            expected_index_names = {
                index.name for index in Complaint.__table__.indexes if index.name
            }
            missing_columns = tuple(
                column_name
                for column_name in EXPECTED_COMPLAINT_COLUMNS
                if column_name not in existing_column_names
            )
            missing_indexes = tuple(sorted(expected_index_names - existing_index_names))
            return DatabaseSetupStatus(
                database_exists=True,
                vector_extension_exists=vector_result.scalar_one_or_none() == 1,
                complaints_table_exists=complaints_table_exists,
                missing_columns=missing_columns,
                missing_indexes=missing_indexes,
            )
    except (OperationalError, ProgrammingError) as exc:
        raise SetupError(f"Unable to inspect database schema: {exc}") from exc
    finally:
        await engine.dispose()


async def create_schema(settings: Settings) -> None:
    engine = _make_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
            await _reconcile_existing_complaints_table(conn)

        # create_all skips indexes when a pre-existing table was created manually.
        async with engine.begin() as conn:
            for index in Complaint.__table__.indexes:
                await conn.run_sync(index.create, checkfirst=True)
    finally:
        await engine.dispose()


async def _reconcile_existing_complaints_table(conn) -> None:
    table_exists = (
        await conn.execute(text("SELECT to_regclass('public.complaints')"))
    ).scalar_one_or_none()
    if table_exists is None:
        return

    row_count = (await conn.execute(text("SELECT count(*) FROM complaints"))).scalar_one()
    existing_columns = await conn.run_sync(
        lambda sync_conn: inspect(sync_conn).get_columns("complaints")
    )
    column_types = {column["name"]: str(column["type"]).lower() for column in existing_columns}

    if row_count:
        incompatible = []
        if "id" in column_types and "char" not in column_types["id"]:
            incompatible.append("id")
        if "timely_response" in column_types and "bool" not in column_types["timely_response"]:
            incompatible.append("timely_response")
        if incompatible:
            raise SetupError(
                "Existing complaints table has incompatible populated columns: "
                + ", ".join(incompatible)
                + ". Migrate or back up the table before running automatic setup."
            )

    if "id" in column_types and "char" not in column_types["id"]:
        await conn.execute(text("ALTER TABLE complaints ALTER COLUMN id DROP DEFAULT"))
        await conn.execute(
            text("ALTER TABLE complaints ALTER COLUMN id TYPE VARCHAR(64) USING id::text")
        )

    if "timely_response" in column_types and "bool" not in column_types["timely_response"]:
        await conn.execute(
            text(
                """
                ALTER TABLE complaints
                ALTER COLUMN timely_response TYPE BOOLEAN
                USING CASE
                    WHEN lower(timely_response::text) IN ('yes', 'true', '1') THEN true
                    WHEN lower(timely_response::text) IN ('no', 'false', '0') THEN false
                    ELSE NULL
                END
                """
            )
        )

    if "date_received" in column_types and "timestamp" not in column_types["date_received"]:
        await conn.execute(
            text(
                "ALTER TABLE complaints ALTER COLUMN date_received "
                "TYPE TIMESTAMP WITH TIME ZONE USING date_received::timestamptz"
            )
        )

    for column_name, column_type in EXPECTED_COMPLAINT_COLUMNS.items():
        await conn.execute(
            text(
                f"ALTER TABLE complaints ADD COLUMN IF NOT EXISTS "
                f"{_quote_identifier(column_name)} {column_type}"
            )
        )

    nullable_columns = set(EXPECTED_COMPLAINT_COLUMNS) - {
        "id",
        "narrative",
        "ai_status",
        "retry_count",
        "created_at",
        "updated_at",
    }
    for column_name in nullable_columns:
        await conn.execute(
            text(f"ALTER TABLE complaints ALTER COLUMN {_quote_identifier(column_name)} DROP NOT NULL")
        )

    if "complaint_id" in column_types:
        await conn.execute(text("ALTER TABLE complaints ALTER COLUMN complaint_id DROP NOT NULL"))
        await conn.execute(
            text(
                """
                UPDATE complaints
                SET source_complaint_id = complaint_id
                WHERE source_complaint_id IS NULL AND complaint_id IS NOT NULL
                """
            )
        )

    await conn.execute(text("UPDATE complaints SET ai_status = 'pending' WHERE ai_status IS NULL"))
    await conn.execute(text("UPDATE complaints SET retry_count = 0 WHERE retry_count IS NULL"))
    await conn.execute(text("UPDATE complaints SET created_at = now() WHERE created_at IS NULL"))
    await conn.execute(text("UPDATE complaints SET updated_at = now() WHERE updated_at IS NULL"))


async def verify_permissions(settings: Settings) -> None:
    engine = _make_engine(settings.database_url)
    test_id = "__customerpulse_permission_check__"
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM complaints WHERE id = :id"), {"id": test_id})
            await conn.execute(
                text(
                    """
                    INSERT INTO complaints (id, source_complaint_id, narrative, ai_status)
                    VALUES (:id, :source_complaint_id, :narrative, 'pending')
                    """
                ),
                {
                    "id": test_id,
                    "source_complaint_id": test_id,
                    "narrative": "CustomerPulse database permission check.",
                },
            )
            await conn.execute(
                text("UPDATE complaints SET ai_status = 'processing' WHERE id = :id"),
                {"id": test_id},
            )
            selected = await conn.execute(
                text("SELECT ai_status FROM complaints WHERE id = :id"),
                {"id": test_id},
            )
            if selected.scalar_one() != "processing":
                raise SetupError("Permission check failed to read updated complaint row.")
            await conn.execute(text("DELETE FROM complaints WHERE id = :id"), {"id": test_id})
    except Exception as exc:
        raise SetupError(f"Database permission check failed: {exc}") from exc
    finally:
        await engine.dispose()


async def ensure_database_ready(settings: Settings, *, prompt: bool = True) -> DatabaseSetupStatus:
    status = await inspect_database(settings)
    database_name = _target_database_name(settings.database_url)

    if not status.database_exists:
        if not prompt or not await _prompt_yes_no(
            f"Database {database_name} does not exist. Create it?"
        ):
            raise SetupError(f"Database {database_name} is missing.")
        await create_database(settings)
        status = await inspect_database(settings)

    if not status.schema_ready:
        missing = []
        if not status.vector_extension_exists:
            missing.append("pgvector extension")
        if not status.complaints_table_exists:
            missing.append("complaints table")
        if status.missing_columns:
            missing.append(f"columns: {', '.join(status.missing_columns)}")
        if status.missing_indexes:
            missing.append(f"indexes: {', '.join(status.missing_indexes)}")
        if not prompt or not await _prompt_yes_no(
            f"Database schema is missing {', '.join(missing)}. Create/update schema?"
        ):
            raise SetupError("Database schema is incomplete.")
        await create_schema(settings)
        status = await inspect_database(settings)

    if not status.schema_ready:
        raise SetupError(f"Database schema is still incomplete after setup: {status}")

    await verify_permissions(settings)
    return status


async def verify_openai_ready(settings: Settings) -> None:
    try:
        await OpenAIClient(settings).check_connection()
    except Exception as exc:
        raise SetupError(f"OpenAI connection check failed: {exc}") from exc


async def run_startup_checks(
    settings: Settings | None = None,
    *,
    prompt: bool = True,
    verify_openai: bool = True,
) -> None:
    resolved_settings = settings or get_settings()
    status = await ensure_database_ready(resolved_settings, prompt=prompt)
    logger.info("Database startup check passed: %s", status)
    if verify_openai:
        await verify_openai_ready(resolved_settings)
        logger.info("OpenAI startup check passed.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    await run_startup_checks(get_settings(), prompt=True, verify_openai=True)
    print("CustomerPulse backend setup completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
