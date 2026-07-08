from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.reporting.models import ComplianceReportFilter, ComplianceReportRecord
from app.compliance.storage_models import ComplianceEvidenceRecord
from app.feedback.models import AgentFeedback
from app.models.complaint import Complaint


async def get_compliance_report_records(
    db: AsyncSession,
    filters: ComplianceReportFilter,
) -> list[ComplianceReportRecord]:
    stmt = (
        select(ComplianceEvidenceRecord, Complaint, AgentFeedback)
        .outerjoin(
            Complaint,
            or_(
                ComplianceEvidenceRecord.complaint_id == Complaint.id,
                ComplianceEvidenceRecord.complaint_id == Complaint.source_complaint_id,
                ComplianceEvidenceRecord.source_complaint_id == Complaint.source_complaint_id,
            ),
        )
        .outerjoin(
            AgentFeedback,
            Complaint.id == AgentFeedback.complaint_pk,
        )
    )

    stmt = _apply_sql_filters(stmt, filters)
    result = await db.execute(stmt)
    return [_build_report_record(evidence, complaint) for evidence, complaint, _feedback in result.all()]


# Kept for callers that already pass in report-ready records. New report retrieval
# should use get_compliance_report_records so filtering happens in PostgreSQL.
def apply_filters(
    records: list[ComplianceReportRecord],
    filters: ComplianceReportFilter,
) -> list[ComplianceReportRecord]:
    return [record for record in records if _record_matches(record, filters)]


def _apply_sql_filters(stmt, filters: ComplianceReportFilter):
    if filters.risk_levels:
        stmt = stmt.where(ComplianceEvidenceRecord.risk_level.in_(filters.risk_levels))

    if filters.regulatory_breach_only:
        stmt = stmt.where(ComplianceEvidenceRecord.regulatory_flag.is_(True))

    if filters.rule_ids:
        stmt = stmt.where(func.jsonb_exists_any(ComplianceEvidenceRecord.reason_codes, array(filters.rule_ids)))

    if filters.sla_statuses:
        stmt = stmt.where(ComplianceEvidenceRecord.regulatory_interpretation.in_(filters.sla_statuses))

    if filters.date_from:
        stmt = stmt.where(ComplianceEvidenceRecord.evaluated_at >= filters.date_from)

    if filters.date_to:
        stmt = stmt.where(ComplianceEvidenceRecord.evaluated_at <= filters.date_to)

    if filters.category:
        stmt = stmt.where(Complaint.category == filters.category)

    if filters.required_action_contains:
        pattern = f"%{filters.required_action_contains}%"
        stmt = stmt.where(
            or_(
                ComplianceEvidenceRecord.required_action.ilike(pattern),
                cast(ComplianceEvidenceRecord.required_actions, String).ilike(pattern),
            )
        )

    if filters.product:
        stmt = stmt.where(Complaint.product == filters.product)

    if filters.company:
        stmt = stmt.where(Complaint.company == filters.company)

    if filters.channel:
        stmt = stmt.where(Complaint.channel == filters.channel)

    if filters.escalation_reason:
        stmt = stmt.where(Complaint.human_review_reason == filters.escalation_reason)

    if filters.review_outcome:
        stmt = stmt.where(
            or_(
                AgentFeedback.human_review_outcome == filters.review_outcome,
                Complaint.review_resolution == filters.review_outcome,
            )
        )

    return stmt


def _build_report_record(
    evidence: ComplianceEvidenceRecord,
    complaint: Complaint | None,
) -> ComplianceReportRecord:
    reason_codes = evidence.reason_codes or []
    return ComplianceReportRecord(
        complaint_id=evidence.complaint_id,
        evaluated_at=evidence.evaluated_at,
        compliance_risk_level=evidence.risk_level,
        dominant_rule_id=reason_codes[0] if reason_codes else "unknown",
        rules_triggered=reason_codes,
        required_actions=_extract_required_action_descriptions(evidence.required_actions),
        regulatory_breach=evidence.regulatory_flag,
        sla_compliance_status=evidence.regulatory_interpretation,
        evidence_summary=evidence.evidence_snippets or [],
        audit_trail=evidence.result_payload or {},
        export_flags=_build_export_flags(reason_codes),
        category=complaint.category if complaint else None,
    )


def _extract_required_action_descriptions(actions: Any) -> list[str]:
    if not isinstance(actions, list):
        return []

    descriptions: list[str] = []
    for action in actions:
        if isinstance(action, dict):
            description = action.get("description")
            if description:
                descriptions.append(str(description))
        elif isinstance(action, str):
            descriptions.append(action)
    return descriptions


def _build_export_flags(reason_codes: list[str]) -> dict[str, bool]:
    return {
        "rbi_monthly": any("RBI" in reason_code for reason_code in reason_codes),
        "cfpb_quarterly": any("CFPB" in reason_code for reason_code in reason_codes),
    }


def _record_matches(record: ComplianceReportRecord, filters: ComplianceReportFilter) -> bool:
    if filters.risk_levels and record.compliance_risk_level not in filters.risk_levels:
        return False

    if filters.regulatory_breach_only and not record.regulatory_breach:
        return False

    if filters.rule_ids and not set(filters.rule_ids).intersection(record.rules_triggered):
        return False

    if filters.sla_statuses and record.sla_compliance_status not in filters.sla_statuses:
        return False

    if filters.date_from and record.evaluated_at < filters.date_from:
        return False

    if filters.date_to and record.evaluated_at > filters.date_to:
        return False

    if filters.category is not None and record.category != filters.category:
        return False

    if filters.required_action_contains:
        needle = filters.required_action_contains.lower()
        if not any(needle in action.lower() for action in record.required_actions):
            return False

    return True
