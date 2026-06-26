from datetime import datetime, timezone

import pytest

from app.compliance.explainability.evidence_mapper import map_evidence
from app.compliance.explainability.models import ComplianceExplanation
from app.compliance.explainability.risk_justifier import justify_risk
from app.compliance.explainability.rule_explainer import explain_rule
from app.compliance.explainability.service import generate_explanation


NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)


def triggered_rule(rule_id: str = "RBI-FRAUD-001", severity: str = "high") -> dict:
    return {
        "rule_id": rule_id,
        "description": f"{severity} severity rule description",
        "severity": severity,
        "required_action": {"action_type": "escalate"},
        "deadline": "2026-01-11T00:00:00+00:00",
        "triggered_at": NOW,
    }


def test_evidence_mapper_complete() -> None:
    evidence = map_evidence(
        {"category": "unauthorized_transaction", "days_since_intake": 4, "fraud_risk_score": 0.87},
        "RBI-SLA-FRAUD-002",
        {"RBI-SLA-FRAUD-002": ["category", "days_since_intake", "fraud_risk_score"]},
    )

    assert evidence == [
        "category: unauthorized_transaction",
        "days_since_intake: 4",
        "fraud_risk_score: 0.87",
    ]


def test_evidence_mapper_missing_field() -> None:
    evidence = map_evidence(
        {"category": None},
        "RBI-FRAUD-001",
        {"RBI-FRAUD-001": ["category", "fraud_risk_score"]},
    )

    assert "category: not available" in evidence
    assert "fraud_risk_score: not available" in evidence


def test_rule_explainer_uses_template() -> None:
    explanation = explain_rule(
        triggered_rule("RBI-FRAUD-001"),
        ["category: unauthorized_transaction", "fraud_risk_score: 0.87"],
    )

    assert "fraud or unauthorized-transaction signals require escalation" in explanation.why_triggered


def test_confidence_high() -> None:
    explanation = explain_rule(triggered_rule(), ["category: fraud", "fraud_risk_score: 0.87"])

    assert explanation.confidence == "high"


def test_confidence_medium() -> None:
    explanation = explain_rule(triggered_rule(), ["category: fraud", "fraud_risk_score: not available"])

    assert explanation.confidence == "medium"


def test_dominant_rule_identified() -> None:
    low_rule = explain_rule(triggered_rule("RBI-ACK-001", "medium"), ["acknowledged_at: not available"])
    critical_rule = explain_rule(triggered_rule("RBI-RES-030", "critical"), ["days_since_intake: 35"])

    justification = justify_risk([low_rule, critical_rule], "critical")

    assert justification.dominant_rule_id == "RBI-RES-030"


def test_reason_summary_contains_level() -> None:
    rule = explain_rule(triggered_rule("RBI-FRAUD-001", "high"), ["category: fraud"])

    justification = justify_risk([rule], "high")

    assert "high" in justification.reason_summary


def test_service_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.compliance.explainability import service

    original_explain_rule = service.explain_rule

    def fail_one_rule(rule: dict, evidence: list[str]):
        if rule["rule_id"] == "BROKEN-RULE":
            raise ValueError("template unavailable")
        return original_explain_rule(rule, evidence)

    monkeypatch.setattr(service, "explain_rule", fail_one_rule)
    result = generate_explanation(
        {
            "complaint_id": "complaint-1",
            "compliance_risk_level": "high",
            "triggered_rules": [triggered_rule("RBI-FRAUD-001"), triggered_rule("BROKEN-RULE")],
            "evaluated_at": NOW,
            "engine_version": "1.0",
            "rule_set_version": "2026.1",
        },
        {"complaint_id": "complaint-1", "category": "fraud", "issue": "unauthorized", "fraud_risk_score": 0.9},
    )

    assert len(result.rule_explanations) == 2
    assert result.rule_explanations[0].rule_id == "RBI-FRAUD-001"
    assert result.rule_explanations[1].rule_id == "BROKEN-RULE"
    assert "Rule explanation failed" in result.rule_explanations[1].why_triggered


def test_full_pipeline() -> None:
    result = generate_explanation(
        {
            "complaint_id": "complaint-1",
            "compliance_risk_level": "critical",
            "triggered_rules": [
                triggered_rule("RBI-FRAUD-001", "high"),
                triggered_rule("RBI-SLA-FRAUD-002", "critical"),
            ],
            "evaluated_at": NOW,
            "engine_version": "1.0",
            "rule_set_version": "2026.1",
        },
        {
            "complaint_id": "complaint-1",
            "category": "unauthorized_transaction",
            "issue": "Unauthorized transfer",
            "days_since_intake": 35,
            "fraud_risk_score": 0.92,
        },
    )

    assert isinstance(result, ComplianceExplanation)
    assert result.risk_justification.overall_risk_level == "critical"
    assert result.risk_justification.dominant_rule_id == "RBI-SLA-FRAUD-002"
    assert result.audit_metadata["engine_version"] == "1.0"
