from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.compliance.engine import ComplianceEngine
from app.compliance.explainability.models import ComplianceExplanation
from app.compliance.explainability.service import generate_explanation
from app.compliance.models import AISignals, ComplaintComplianceInput, SLAState
from app.db.session import get_db_session
from app.main import app


BASE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_complaint_payload(**overrides) -> ComplaintComplianceInput:
    payload = {
        "complaint_id": "complaint-explain-1",
        "source_complaint_id": "SRC-EXPLAIN-1",
        "product": "Checking account",
        "issue": "Unauthorized transaction and fraud claim",
        "date_received": BASE_DATE,
        "acknowledged_at": None,
        "resolved_at": None,
        "ai_signals": AISignals(
            severity="high",
            urgency_score=91,
            fraud_risk_score=88,
            key_issue="unauthorized transfer",
        ),
        "sla": SLAState(is_breached=True, breach_risk_level="critical", days_elapsed=35),
    }
    payload.update(overrides)
    return ComplaintComplianceInput(**payload)


def test_explanation_metadata_contains_valid_versions() -> None:
    complaint = make_complaint_payload()
    result = ComplianceEngine().evaluate(complaint)

    explanation = generate_explanation(result, complaint)

    assert explanation.audit_metadata["engine_version"] == "1.0.0"
    assert explanation.audit_metadata["rule_set_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_explain_endpoint_returns_compliance_explanation() -> None:
    async def override_get_db_session():
        yield object()

    app.dependency_overrides[get_db_session] = override_get_db_session
    payload = make_complaint_payload(
        complaint_id="complaint-explain-2",
        source_complaint_id="SRC-EXPLAIN-2",
    ).model_dump(mode="json")

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/compliance/explain", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert ComplianceExplanation.model_validate(body)
    assert body["audit_metadata"]["engine_version"] == "1.0.0"
    assert body["audit_metadata"]["rule_set_version"] == "1.0.0"
    assert body["risk_justification"]["overall_risk_level"] == "critical"