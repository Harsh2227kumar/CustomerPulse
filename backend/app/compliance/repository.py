from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.storage_models import ComplianceEvidenceRecord, ComplianceRuleRecord, ReasonCodeRecord
from app.models.complaint import Complaint


class ComplianceEvidenceRepository:
    async def create_record(
        self,
        db: AsyncSession,
        values: dict,
    ) -> ComplianceEvidenceRecord:
        record = ComplianceEvidenceRecord(**values)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def get_record(
        self,
        db: AsyncSession,
        record_id: str,
    ) -> ComplianceEvidenceRecord | None:
        stmt = select(ComplianceEvidenceRecord).where(ComplianceEvidenceRecord.id == record_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_records(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        complaint_id: str | None = None,
        risk_level: str | None = None,
        regulatory_flag: bool | None = None,
        product: str | None = None,
        company: str | None = None,
        channel: str | None = None,
    ) -> tuple[Sequence[ComplianceEvidenceRecord], int]:
        join_condition = or_(
            ComplianceEvidenceRecord.complaint_id == Complaint.id,
            ComplianceEvidenceRecord.complaint_id == Complaint.source_complaint_id,
            ComplianceEvidenceRecord.source_complaint_id == Complaint.source_complaint_id,
        )
        stmt = select(ComplianceEvidenceRecord).outerjoin(Complaint, join_condition).distinct()
        count_stmt = select(func.count(func.distinct(ComplianceEvidenceRecord.id))).select_from(
            ComplianceEvidenceRecord
        ).outerjoin(Complaint, join_condition)

        if complaint_id:
            stmt = stmt.where(ComplianceEvidenceRecord.complaint_id == complaint_id)
            count_stmt = count_stmt.where(ComplianceEvidenceRecord.complaint_id == complaint_id)
        if risk_level:
            stmt = stmt.where(ComplianceEvidenceRecord.risk_level == risk_level)
            count_stmt = count_stmt.where(ComplianceEvidenceRecord.risk_level == risk_level)
        if regulatory_flag is not None:
            stmt = stmt.where(ComplianceEvidenceRecord.regulatory_flag == regulatory_flag)
            count_stmt = count_stmt.where(ComplianceEvidenceRecord.regulatory_flag == regulatory_flag)
        if product:
            stmt = stmt.where(Complaint.product == product)
            count_stmt = count_stmt.where(Complaint.product == product)
        if company:
            stmt = stmt.where(Complaint.company == company)
            count_stmt = count_stmt.where(Complaint.company == company)
        if channel:
            stmt = stmt.where(Complaint.channel == channel)
            count_stmt = count_stmt.where(Complaint.channel == channel)

        stmt = stmt.order_by(ComplianceEvidenceRecord.evaluated_at.desc()).limit(limit).offset(offset)
        records = (await db.execute(stmt)).scalars().all()
        count = (await db.execute(count_stmt)).scalar_one()
        return records, count

    async def delete_record(
        self,
        db: AsyncSession,
        record: ComplianceEvidenceRecord,
    ) -> None:
        await db.delete(record)
        await db.commit()


class ComplianceKnowledgeBaseRepository:
    async def create_rule(
        self,
        db: AsyncSession,
        values: dict,
    ) -> ComplianceRuleRecord:
        record = ComplianceRuleRecord(**values)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def get_rule(
        self,
        db: AsyncSession,
        record_id: str,
    ) -> ComplianceRuleRecord | None:
        stmt = select(ComplianceRuleRecord).where(ComplianceRuleRecord.id == record_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_rule_by_identity(
        self,
        db: AsyncSession,
        rule_id: str,
        version: str,
    ) -> ComplianceRuleRecord | None:
        stmt = select(ComplianceRuleRecord).where(
            ComplianceRuleRecord.rule_id == rule_id,
            ComplianceRuleRecord.version == version,
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_rules(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        regulator: str | None = None,
        domain: str | None = None,
        status: str | None = None,
        active_on: datetime | None = None,
    ) -> tuple[Sequence[ComplianceRuleRecord], int]:
        stmt = select(ComplianceRuleRecord)
        count_stmt = select(func.count()).select_from(ComplianceRuleRecord)

        if regulator:
            stmt = stmt.where(ComplianceRuleRecord.regulator == regulator)
            count_stmt = count_stmt.where(ComplianceRuleRecord.regulator == regulator)
        if domain:
            stmt = stmt.where(ComplianceRuleRecord.domain == domain)
            count_stmt = count_stmt.where(ComplianceRuleRecord.domain == domain)
        if status:
            stmt = stmt.where(ComplianceRuleRecord.status == status)
            count_stmt = count_stmt.where(ComplianceRuleRecord.status == status)
        if active_on:
            stmt = stmt.where(
                ComplianceRuleRecord.status == "active",
                ComplianceRuleRecord.effective_from <= active_on,
                (ComplianceRuleRecord.effective_to.is_(None) | (ComplianceRuleRecord.effective_to >= active_on)),
            )
            count_stmt = count_stmt.where(
                ComplianceRuleRecord.status == "active",
                ComplianceRuleRecord.effective_from <= active_on,
                (ComplianceRuleRecord.effective_to.is_(None) | (ComplianceRuleRecord.effective_to >= active_on)),
            )

        stmt = (
            stmt.order_by(
                ComplianceRuleRecord.regulator.asc(),
                ComplianceRuleRecord.domain.asc(),
                ComplianceRuleRecord.rule_id.asc(),
                ComplianceRuleRecord.effective_from.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        records = (await db.execute(stmt)).scalars().all()
        count = (await db.execute(count_stmt)).scalar_one()
        return records, count

    async def create_rule_version(
        self,
        db: AsyncSession,
        previous: ComplianceRuleRecord,
        values: dict,
    ) -> ComplianceRuleRecord:
        if values.get("status") == "active" and previous.status == "active":
            previous.status = "inactive"
            previous.effective_to = values.get("effective_from") or datetime.now(timezone.utc)
        record = ComplianceRuleRecord(**values, supersedes_rule_record_id=previous.id)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def create_reason_code(
        self,
        db: AsyncSession,
        values: dict,
    ) -> ReasonCodeRecord:
        record = ReasonCodeRecord(**values)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def get_reason_code(
        self,
        db: AsyncSession,
        code: str,
    ) -> ReasonCodeRecord | None:
        stmt = select(ReasonCodeRecord).where(ReasonCodeRecord.code == code)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_reason_codes(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[Sequence[ReasonCodeRecord], int]:
        stmt = select(ReasonCodeRecord)
        count_stmt = select(func.count()).select_from(ReasonCodeRecord)
        if status:
            stmt = stmt.where(ReasonCodeRecord.status == status)
            count_stmt = count_stmt.where(ReasonCodeRecord.status == status)
        stmt = stmt.order_by(ReasonCodeRecord.code.asc()).limit(limit).offset(offset)
        records = (await db.execute(stmt)).scalars().all()
        count = (await db.execute(count_stmt)).scalar_one()
        return records, count


