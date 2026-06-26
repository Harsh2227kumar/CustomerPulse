from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.compliance.models import ComplianceResult, ComplianceRiskLevel, SLAComplianceReading
from app.core.constants import ChurnRisk, ProcessingStatus, Sentiment
from app.schemas.ai_response import AIEnrichment, ConfidenceScores
from app.services.processing_service import ProcessingService


BASE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_enrichment(**overrides) -> AIEnrichment:
    payload = {
        "sentiment": Sentiment.NEGATIVE,
        "category": "billing",
        "urgency_score": 82,
        "churn_risk": ChurnRisk.HIGH,
        "draft_response": "We reviewed the billing dispute and prepared the response.",
        "next_action": "Escalate for manager review",
        "similar_cases": [],
        "confidence_scores": ConfidenceScores(sentiment=90, category=88, urgency=86),
        "ai_confidence": 0.91,
        "ai_reasoning": "High urgency billing dispute.",
    }
    payload.update(overrides)
    return AIEnrichment(**payload)


def make_complaint(**overrides):
    payload = {
        "id": "complaint-db-1",
        "source_complaint_id": "SRC-1",
        "product": "Credit card",
        "issue": "Transaction dispute",
        "sub_issue": None,
        "narrative": "Customer says they will file an RBI complaint.",
        "channel": "Web",
        "date_received": BASE_DATE,
        "created_at": BASE_DATE,
        "processed_at": BASE_DATE,
        "ai_status": ProcessingStatus.COMPLETED.value,
        "timely_response": True,
        "approved_response": None,
        "review_resolution": "Resolved with evidence",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def empty_result(complaint_id: str = "complaint-db-1") -> ComplianceResult:
    return ComplianceResult(
        complaint_id=complaint_id,
        source_complaint_id="SRC-1",
        compliance_risk_level=ComplianceRiskLevel.LOW,
        triggered_rules=[],
        required_actions=[],
        reason_codes=[],
        sla_reading=SLAComplianceReading(
            is_breached=False,
            breach_risk_level="low",
            regulatory_interpretation="no_regulatory_sla_exception",
            proactive_flag=False,
        ),
        evaluated_at=BASE_DATE,
    )


@pytest.mark.asyncio
async def test_processing_service_auto_triggers_compliance_evaluate_and_store_result() -> None:
    service = object.__new__(ProcessingService)
    evidence_service = SimpleNamespace(list_records=AsyncMock(return_value=([], 0)), store_result=AsyncMock())
    engine = SimpleNamespace(evaluate=Mock(return_value=empty_result()))

    db = object()
    with (
        patch("app.services.processing_service.ComplianceEngine", return_value=engine),
        patch("app.services.processing_service.ComplianceEvidenceService", return_value=evidence_service),
    ):
        await service._store_compliance_evidence(db, make_complaint(), make_enrichment(), BASE_DATE)

    engine.evaluate.assert_called_once()
    evidence_service.list_records.assert_awaited_once()
    evidence_service.store_result.assert_awaited_once_with(
        db,
        engine.evaluate.return_value,
        notes="auto-triggered-from-processing",
    )


@pytest.mark.asyncio
async def test_processing_service_auto_trigger_persists_real_compliance_result() -> None:
    service = object.__new__(ProcessingService)
    evidence_service = SimpleNamespace(list_records=AsyncMock(return_value=([], 0)), store_result=AsyncMock())

    with patch("app.services.processing_service.ComplianceEvidenceService", return_value=evidence_service):
        await service._store_compliance_evidence(object(), make_complaint(), make_enrichment(), BASE_DATE)

    stored_result = evidence_service.store_result.await_args.args[1]
    assert stored_result.complaint_id == "complaint-db-1"
    assert "RBI-LEGAL-001" in stored_result.reason_codes
    assert evidence_service.store_result.await_args.kwargs["notes"] == "auto-triggered-from-processing"


@pytest.mark.asyncio
async def test_processing_service_auto_trigger_skips_duplicate_evidence() -> None:
    service = object.__new__(ProcessingService)
    evidence_service = SimpleNamespace(list_records=AsyncMock(return_value=([object()], 1)), store_result=AsyncMock())

    with patch("app.services.processing_service.ComplianceEvidenceService", return_value=evidence_service):
        await service._store_compliance_evidence(object(), make_complaint(), make_enrichment(), BASE_DATE)

    evidence_service.list_records.assert_awaited_once()
    evidence_service.store_result.assert_not_awaited()


@pytest.mark.asyncio
async def test_processing_service_auto_trigger_does_not_fail_pipeline_when_no_rules_trigger() -> None:
    service = object.__new__(ProcessingService)
    evidence_service = SimpleNamespace(list_records=AsyncMock(return_value=([], 0)), store_result=AsyncMock())
    clean_complaint = make_complaint(
        issue="General account question",
        narrative="Customer asks for routine account clarification.",
        review_resolution="Resolved with evidence",
    )

    with patch("app.services.processing_service.ComplianceEvidenceService", return_value=evidence_service):
        await service._store_compliance_evidence(object(), clean_complaint, make_enrichment(urgency_score=35), BASE_DATE)

    stored_result = evidence_service.store_result.await_args.args[1]
    assert stored_result.triggered_rules == []
    assert stored_result.compliance_risk_level == "low"


@pytest.mark.asyncio
async def test_processing_service_auto_trigger_logs_and_swallows_compliance_errors() -> None:
    service = object.__new__(ProcessingService)
    engine = SimpleNamespace(evaluate=Mock(side_effect=RuntimeError("compliance unavailable")))

    with patch("app.services.processing_service.ComplianceEngine", return_value=engine):
        await service._store_compliance_evidence(object(), make_complaint(), make_enrichment(), BASE_DATE)

    engine.evaluate.assert_called_once()


def test_processing_service_maps_enrichment_to_compliance_response_fields() -> None:
    service = object.__new__(ProcessingService)
    compliance_input = service._compliance_input(make_complaint(), make_enrichment(), BASE_DATE)

    assert compliance_input.response_fields.category == "billing"
    assert compliance_input.response_fields.urgency_score == 82
    assert compliance_input.response_fields.draft_response
    assert compliance_input.response_fields.resolution == "Resolved with evidence"
    assert compliance_input.response_fields.next_action == "Escalate for manager review"
    assert compliance_input.response_fields.ai_confidence == 0.91
