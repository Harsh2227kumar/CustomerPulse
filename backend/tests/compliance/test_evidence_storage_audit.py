from datetime import timedelta

import pytest

from app.compliance.engine import ComplianceEngine
from app.compliance.models import AISignals, ComplianceEvidenceStoreRequest, SLAState
from app.compliance.service import ComplianceEvidenceNotFoundError, ComplianceEvidenceService

from .conftest import BASE_DATE, CapturingRepository, make_complaint


def breached_fraud_result():
    complaint = make_complaint(
        complaint_id="storage-fraud-1",
        source_complaint_id="SRC-STORAGE-1",
        issue="Unauthorized transaction and fraud claim",
        acknowledged_at=None,
        resolved_at=None,
        ai_signals=AISignals(severity="high", urgency_score=91, fraud_risk_score=88, key_issue="unauthorized transfer"),
        sla=SLAState(is_breached=True, breach_risk_level="critical", days_elapsed=35, days_to_deadline=-5),
    )
    return ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=35))


@pytest.mark.asyncio
async def test_compliance_event_creation_links_identifiers_and_reason_codes() -> None:
    repository = CapturingRepository(created_at=BASE_DATE + timedelta(days=35, minutes=1))
    service = ComplianceEvidenceService(repository)
    result = breached_fraud_result()

    stored = await service.store_request(object(), ComplianceEvidenceStoreRequest(result=result, notes=" compliance checked "))

    assert stored.id == "evidence-1"
    assert stored.complaint_id == "storage-fraud-1"
    assert stored.source_complaint_id == "SRC-STORAGE-1"
    assert stored.reason_codes == [rule.rule_id for rule in result.triggered_rules]
    assert "RBI-SLA-FRAUD-002" in stored.reason_codes
    assert stored.notes == "compliance checked"
    assert repository.records[0]["complaint_id"] == "storage-fraud-1"


@pytest.mark.asyncio
async def test_evidence_persistence_contains_thresholds_parameters_rule_versions_and_snapshot() -> None:
    repository = CapturingRepository()
    service = ComplianceEvidenceService(repository)
    result = breached_fraud_result()

    stored = await service.store_result(object(), result, notes="audit ready")
    persisted = repository.records[0]
    triggered_rule = next(rule for rule in stored.triggered_rules if rule["rule_id"] == "RBI-SLA-FRAUD-002")

    assert persisted["risk_level"] == "critical"
    assert persisted["required_action"] == "acknowledge"
    assert persisted["regulatory_flag"] is True
    assert persisted["regulatory_interpretation"] == "breached_fraud_or_unauthorized_complaint"
    assert persisted["result_payload"]["complaint_id"] == "storage-fraud-1"
    assert persisted["result_payload"]["sla_reading"]["breach_risk_level"] == "critical"
    assert triggered_rule["required_action"]["owner"] == "compliance_officer"
    assert triggered_rule["required_action"]["deadline_at"] == BASE_DATE.isoformat().replace("+00:00", "Z")
    assert any("fraud_risk_score=88" in snippet for snippet in stored.evidence_snippets)


@pytest.mark.asyncio
async def test_audit_trail_timestamps_are_preserved_and_listable() -> None:
    created_at = BASE_DATE + timedelta(days=35, minutes=1)
    repository = CapturingRepository(created_at=created_at)
    service = ComplianceEvidenceService(repository)
    result = breached_fraud_result()

    stored = await service.store_result(object(), result)
    records, count = await service.list_records(object(), limit=10, offset=0, complaint_id=result.complaint_id, risk_level="critical", regulatory_flag=True)

    assert count == 1
    assert records[0].id == stored.id
    assert records[0].evaluated_at == result.evaluated_at
    assert records[0].created_at == created_at
    assert records[0].updated_at == created_at
    assert records[0].result.evaluated_at == result.evaluated_at


@pytest.mark.asyncio
async def test_historical_evidence_is_append_only_from_service_contract() -> None:
    repository = CapturingRepository()
    service = ComplianceEvidenceService(repository)
    original = breached_fraud_result()
    later = original.model_copy(update={"evaluated_at": original.evaluated_at + timedelta(hours=1)})

    first = await service.store_result(object(), original)
    second = await service.store_result(object(), later)

    assert first.id == "evidence-1"
    assert second.id == "evidence-2"
    assert len(repository.records) == 2
    assert repository.records[0]["evaluated_at"] == original.evaluated_at
    assert repository.records[1]["evaluated_at"] == later.evaluated_at
    assert not hasattr(service, "update_record")
    assert not hasattr(service.repository, "update_record")


@pytest.mark.asyncio
async def test_missing_database_record_returns_controlled_not_found_error() -> None:
    service = ComplianceEvidenceService(CapturingRepository())

    with pytest.raises(ComplianceEvidenceNotFoundError):
        await service.get_record(object(), "evidence-99")


@pytest.mark.asyncio
async def test_product_company_channel_filters_are_forwarded_to_repository() -> None:
    class ForwardingRepository(CapturingRepository):
        def __init__(self) -> None:
            super().__init__()
            self.filters = None

        async def list_records(self, db, **kwargs):
            self.filters = kwargs
            return [], 0

    repository = ForwardingRepository()
    service = ComplianceEvidenceService(repository)

    records, count = await service.list_records(
        object(),
        limit=25,
        offset=5,
        product="Credit card",
        company="Test Bank",
        channel="Web",
    )

    assert records == []
    assert count == 0
    assert repository.filters["product"] == "Credit card"
    assert repository.filters["company"] == "Test Bank"
    assert repository.filters["channel"] == "Web"


@pytest.mark.asyncio
async def test_admin_can_delete_compliance_evidence_record() -> None:
    repository = CapturingRepository()
    service = ComplianceEvidenceService(repository)
    result = breached_fraud_result()

    evidence = await service.store_result(object(), result)
    await service.delete_record(object(), evidence.id)

    with pytest.raises(ComplianceEvidenceNotFoundError):
        await service.get_record(object(), evidence.id)
