import csv
import io
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from app.compliance.reporting.field_registry import get_all_fields, get_required_fields
from app.compliance.reporting.filters import apply_filters, get_compliance_report_records
from app.compliance.reporting.models import ComplianceReportFilter, ComplianceReportRecord
from app.compliance.reporting.serialiser import get_export_headers, serialise_record, serialise_records
from app.exports.services.csv_service import CSVExportService


BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_record(**overrides) -> ComplianceReportRecord:
    payload = {
        "complaint_id": "complaint-1",
        "evaluated_at": BASE_TIME,
        "compliance_risk_level": "critical",
        "dominant_rule_id": "RBI-FRAUD-001",
        "rules_triggered": ["RBI-FRAUD-001", "RBI-TURN-003"],
        "required_actions": ["Escalate immediately", "Notify compliance officer"],
        "regulatory_breach": True,
        "sla_compliance_status": "breached",
        "evidence_summary": ["fraud_risk_score=91", "days_elapsed=35"],
        "audit_trail": {
            "engine_version": "1.0.0",
            "rule_set_version": "2026.01",
            "evaluated_at": BASE_TIME,
        },
        "export_flags": {
            "rbi_monthly": True,
            "cfpb_quarterly": False,
        },
        "category": "fraud",
    }
    payload.update(overrides)
    return ComplianceReportRecord(**payload)


def make_evidence(**overrides) -> SimpleNamespace:
    payload = {
        "complaint_id": "complaint-1",
        "source_complaint_id": "SRC-1",
        "evaluated_at": BASE_TIME,
        "risk_level": "critical",
        "regulatory_flag": True,
        "regulatory_interpretation": "breached",
        "reason_codes": ["RBI-FRAUD-001", "CFPB-DISP-002"],
        "required_action": "escalate",
        "required_actions": [{"description": "Escalate immediately"}],
        "evidence_snippets": ["fraud_risk_score=91"],
        "result_payload": {"engine_version": "1.0.0"},
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def make_complaint(**overrides) -> SimpleNamespace:
    payload = {
        "id": "complaint-1",
        "source_complaint_id": "SRC-1",
        "category": "fraud",
        "product": "Credit card",
        "company": "Test Bank",
        "channel": "Web",
        "human_review_reason": "compliance_escalation",
        "review_resolution": "resolved",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def make_feedback(**overrides) -> SimpleNamespace:
    payload = {
        "complaint_pk": "complaint-1",
        "human_review_outcome": "resolved",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class FakeComplianceResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return self._rows


class FakeComplianceDB:
    def __init__(self, rows) -> None:
        self.rows = rows
        self.statement = None

    async def execute(self, stmt):
        self.statement = stmt
        return FakeComplianceResult(self.rows)


def compile_sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}))


async def collect_async_text(iterator) -> str:
    chunks: list[str] = []
    async for chunk in iterator:
        chunks.append(chunk)
    return "".join(chunks)


def test_field_registry_required_fields():
    fields = get_required_fields()

    assert fields
    assert all(field.required_for_regulatory is True for field in fields)


def test_field_registry_all_fields_have_source():
    assert all(field.source_module for field in get_all_fields())


def test_filter_by_risk_level():
    records = [
        make_record(complaint_id="1", compliance_risk_level="critical"),
        make_record(complaint_id="2", compliance_risk_level="low"),
    ]

    filtered = apply_filters(records, ComplianceReportFilter(risk_levels=["critical"]))

    assert [record.complaint_id for record in filtered] == ["1"]


def test_filter_regulatory_breach_only():
    records = [
        make_record(complaint_id="1", regulatory_breach=True),
        make_record(complaint_id="2", regulatory_breach=False),
    ]

    filtered = apply_filters(records, ComplianceReportFilter(regulatory_breach_only=True))

    assert [record.complaint_id for record in filtered] == ["1"]


def test_filter_by_rule_id():
    records = [
        make_record(complaint_id="1"),
        make_record(complaint_id="2", rules_triggered=["RBI-ACK-001"]),
    ]

    filtered = apply_filters(records, ComplianceReportFilter(rule_ids=["RBI-FRAUD-001"]))

    assert [record.complaint_id for record in filtered] == ["1"]


def test_filter_date_range():
    records = [
        make_record(complaint_id="1", evaluated_at=BASE_TIME),
        make_record(complaint_id="2", evaluated_at=BASE_TIME + timedelta(days=10)),
    ]

    filtered = apply_filters(
        records,
        ComplianceReportFilter(date_from=BASE_TIME - timedelta(days=1), date_to=BASE_TIME + timedelta(days=1)),
    )

    assert [record.complaint_id for record in filtered] == ["1"]


def test_filter_required_action_substring():
    records = [
        make_record(complaint_id="1"),
        make_record(complaint_id="2", required_actions=["Archive complaint"]),
    ]

    filtered = apply_filters(records, ComplianceReportFilter(required_action_contains="notify compliance"))

    assert [record.complaint_id for record in filtered] == ["1"]


def test_filter_and_logic():
    records = [
        make_record(complaint_id="1", compliance_risk_level="critical", category="fraud"),
        make_record(complaint_id="2", compliance_risk_level="critical", category="servicing"),
        make_record(complaint_id="3", compliance_risk_level="low", category="fraud"),
    ]

    filtered = apply_filters(records, ComplianceReportFilter(risk_levels=["critical"], category="fraud"))

    assert [record.complaint_id for record in filtered] == ["1"]


async def test_filter_by_product_in_sql():
    db = FakeComplianceDB([(make_evidence(), make_complaint(), make_feedback())])

    records = await get_compliance_report_records(db, ComplianceReportFilter(product="Credit card"))

    assert records[0].complaint_id == "complaint-1"
    assert records[0].category == "fraud"
    assert records[0].required_actions == ["Escalate immediately"]
    assert "complaints.product" in compile_sql(db.statement)


async def test_filter_by_company_in_sql():
    db = FakeComplianceDB([(make_evidence(), make_complaint(), make_feedback())])

    await get_compliance_report_records(db, ComplianceReportFilter(company="Test Bank"))

    assert "complaints.company" in compile_sql(db.statement)


async def test_filter_by_channel_in_sql():
    db = FakeComplianceDB([(make_evidence(), make_complaint(), make_feedback())])

    await get_compliance_report_records(db, ComplianceReportFilter(channel="Web"))

    assert "complaints.channel" in compile_sql(db.statement)


async def test_filter_by_escalation_reason_in_sql():
    db = FakeComplianceDB([(make_evidence(), make_complaint(), make_feedback())])

    await get_compliance_report_records(db, ComplianceReportFilter(escalation_reason="compliance_escalation"))

    assert "complaints.human_review_reason" in compile_sql(db.statement)


async def test_filter_by_review_outcome_in_sql():
    db = FakeComplianceDB([(make_evidence(), make_complaint(), make_feedback())])

    await get_compliance_report_records(db, ComplianceReportFilter(review_outcome="resolved"))
    sql = compile_sql(db.statement)

    assert "agent_feedback.human_review_outcome" in sql
    assert "complaints.review_resolution" in sql


def test_serialiser_flattens_lists():
    output = serialise_record(make_record())

    assert output["rules_triggered"] == "RBI-FRAUD-001|RBI-TURN-003"
    assert output["required_actions"] == "1. Escalate immediately 2. Notify compliance officer"
    assert output["evidence_summary"] == "fraud_risk_score=91; days_elapsed=35"


def test_serialiser_expands_audit_trail():
    output = serialise_record(make_record())

    assert output["audit_engine_version"] == "1.0.0"
    assert output["audit_rule_set_version"] == "2026.01"
    assert output["audit_evaluated_at"] == BASE_TIME.isoformat()


def test_serialiser_no_nested_objects():
    output = serialise_record(make_record())

    assert all(not isinstance(value, (dict, list)) for value in output.values())


def test_export_headers_complete():
    output = serialise_record(make_record())
    headers = get_export_headers()

    assert set(output).issubset(headers)


async def test_compliance_report_csv_stream_uses_sql_records():
    db = FakeComplianceDB([(make_evidence(), make_complaint(), make_feedback())])

    payload = await collect_async_text(
        CSVExportService().stream_compliance_report_csv(db, ComplianceReportFilter(product="Credit card"))
    )
    rows = list(csv.DictReader(io.StringIO(payload)))

    assert rows[0]["complaint_id"] == "complaint-1"
    assert rows[0]["rules_triggered"] == "RBI-FRAUD-001|CFPB-DISP-002"
    assert rows[0]["flag_rbi_monthly"] == "Yes"


def test_full_pipeline():
    records = [
        make_record(complaint_id="1", compliance_risk_level="critical", regulatory_breach=True),
        make_record(complaint_id="2", compliance_risk_level="low", regulatory_breach=False),
    ]

    filtered = apply_filters(records, ComplianceReportFilter(risk_levels=["critical"], regulatory_breach_only=True))
    output = serialise_records(filtered)

    assert len(output) == 1
    assert output[0]["complaint_id"] == "1"
    assert output[0]["rules_triggered"] == "RBI-FRAUD-001|RBI-TURN-003"
    assert all(not isinstance(value, (dict, list)) for value in output[0].values())
