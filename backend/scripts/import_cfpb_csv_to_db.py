from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from io import TextIOWrapper
from pathlib import Path
from typing import TextIO

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.ingestion.cfpb_s3 import map_cfpb_csv_row  # noqa: E402
from app.models.complaint import Complaint  # noqa: E402


@contextmanager
def open_dataset(path: Path) -> Iterator[TextIO]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield handle
        return
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"{path} does not contain a CSV file.")
            with archive.open(csv_names[0]) as member:
                with TextIOWrapper(member, encoding="utf-8-sig", newline="") as handle:
                    yield handle
        return
    raise ValueError("Dataset path must be a .csv or .zip file.")


def iter_mapped_rows(path: Path) -> Iterator[dict]:
    with open_dataset(path) as handle:
        for raw_row in csv.DictReader(handle):
            mapped = map_cfpb_csv_row(raw_row)
            if mapped is not None:
                yield mapped


async def count_imported_complaints(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Complaint).where(Complaint.source_complaint_id.is_not(None))
    return int((await session.execute(stmt)).scalar_one())


async def existing_source_ids(session: AsyncSession, source_ids: list[str]) -> set[str]:
    if not source_ids:
        return set()
    stmt = select(Complaint.source_complaint_id).where(Complaint.source_complaint_id.in_(source_ids))
    return {row[0] for row in await session.execute(stmt) if row[0] is not None}


async def insert_batch(session: AsyncSession, rows: list[dict], *, update_existing: bool) -> int:
    if not rows:
        return 0
    stmt = insert(Complaint).values(rows)
    if update_existing:
        stmt = stmt.on_conflict_do_update(
            index_elements=[Complaint.source_complaint_id],
            set_={
                "narrative": stmt.excluded.narrative,
                "channel": stmt.excluded.channel,
                "product": stmt.excluded.product,
                "sub_product": stmt.excluded.sub_product,
                "issue": stmt.excluded.issue,
                "sub_issue": stmt.excluded.sub_issue,
                "company": stmt.excluded.company,
                "company_response": stmt.excluded.company_response,
                "timely_response": stmt.excluded.timely_response,
                "date_received": stmt.excluded.date_received,
                "updated_at": func.now(),
            },
        )
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=[Complaint.source_complaint_id])
    result = await session.execute(stmt)
    return result.rowcount if result.rowcount is not None and result.rowcount >= 0 else len(rows)


async def import_dataset(args: argparse.Namespace) -> None:
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url), pool_pre_ping=True, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, class_=AsyncSession)

    async with session_factory() as session:
        current_total = await count_imported_complaints(session)
        remaining_target = None
        if args.target_total is not None:
            remaining_target = max(args.target_total - current_total, 0)
            print(f"Current CFPB-style imported rows: {current_total}")
            print(f"Target total: {args.target_total}; new rows needed: {remaining_target}")
            if remaining_target == 0:
                await engine.dispose()
                return

        scanned = 0
        valid = 0
        written = 0
        skipped_existing = 0
        pending: dict[str, dict] = {}

        async def flush_pending() -> None:
            nonlocal written, skipped_existing, pending
            if not pending:
                return
            rows = list(pending.values())
            pending = {}
            if not args.update_existing:
                existing = await existing_source_ids(session, [row["source_complaint_id"] for row in rows])
                if existing:
                    skipped_existing += len(existing)
                    rows = [row for row in rows if row["source_complaint_id"] not in existing]
            if remaining_target is not None:
                rows = rows[: max(remaining_target - written, 0)]
            if rows and not args.dry_run:
                written += await insert_batch(session, rows, update_existing=args.update_existing)
                await session.commit()
            elif rows:
                written += len(rows)
            if scanned and scanned % args.log_every == 0:
                print(f"Scanned={scanned} valid={valid} written={written} skipped_existing={skipped_existing}")

        for row in iter_mapped_rows(args.dataset):
            scanned += 1
            valid += 1
            pending[row["source_complaint_id"]] = row
            if len(pending) >= args.batch_size:
                await flush_pending()
            if args.limit is not None and valid >= args.limit:
                break
            if remaining_target is not None and written >= remaining_target:
                break

        await flush_pending()
        final_total = current_total + written if args.dry_run else await count_imported_complaints(session)
        print("Import finished.")
        print(f"Scanned valid rows: {valid}")
        print(f"Inserted/updated rows this run: {written}")
        print(f"Skipped existing rows: {skipped_existing}")
        print(f"Final CFPB-style imported rows: {final_total}")

    await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream a local CFPB CSV/ZIP dataset directly into the complaints table."
    )
    parser.add_argument("dataset", type=Path, help="Path to CFPB .csv or .zip dataset.")
    parser.add_argument("--target-total", type=int, help="Stop after DB reaches this many imported CFPB rows.")
    parser.add_argument("--limit", type=int, help="Stop after reading this many valid rows from the dataset.")
    parser.add_argument("--batch-size", type=int, default=5000, help="Rows to collect before each DB write.")
    parser.add_argument("--log-every", type=int, default=50000, help="Progress log interval by valid rows scanned.")
    parser.add_argument("--update-existing", action="store_true", help="Update existing complaints instead of skipping them.")
    parser.add_argument("--dry-run", action="store_true", help="Read and count rows without writing to DB.")
    args = parser.parse_args()
    if args.target_total is None and args.limit is None:
        parser.error("Provide --target-total or --limit.")
    if args.target_total is not None and args.target_total < 1:
        parser.error("--target-total must be at least 1.")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1.")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1.")
    if args.log_every < 1:
        parser.error("--log-every must be at least 1.")
    if not args.dataset.exists():
        parser.error(f"Dataset not found: {args.dataset}")
    return args


if __name__ == "__main__":
    asyncio.run(import_dataset(parse_args()))
