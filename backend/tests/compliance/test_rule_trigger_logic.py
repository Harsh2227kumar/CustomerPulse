from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.compliance.engine import ComplianceEngine
from app.compliance.explainability.service import generate_explanation
from app.compliance.models import AIResponseFields, AISignals, SLAState
from app.compliance.risk_aggregator import aggregate_risk
from app.compliance.rule_registry import load_rule_registry

from .conftest import BASE_DATE, make_complaint


def rule_ids(result) -> list[str]:
    return [rule.rule_id for rule in result.triggered_rules]


@pytest.mark.parametrize(
    ("resolved_days", "expected_rules", "expected_risk"),
    [
        (29, [], "low"),
        (30, [], "low"),
    ],
)
def test_sla_resolution_at_or_before_30_day_boundary_passes(resolved_days: int, expected_rules: list[str], expected_risk: str) -> None:
    complaint = make_complaint(
        complaint_id=f"sla-pass-{resolved_days}",
        resolved_at=BASE_DATE + timedelta(days=resolved_days),
        sla=SLAState(is_breached=False, breach_risk_level="low", days_elapsed=resolved_days, days_to_deadline=30 - resolved_days),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=resolved_days))

    assert result.compliance_risk_level == expected_risk
    assert rule_ids(result) == expected_rules
    assert result.reason_codes == expected_rules
    assert result.sla_reading.regulatory_interpretation == "no_regulatory_sla_exception"


def test_unresolved_after_30_days_fails_with_regulatory_reporting_rule() -> None:
    complaint = make_complaint(
        complaint_id="sla-fail-31",
        resolved_at=None,
        sla=SLAState(is_breached=True, breach_risk_level="critical", days_elapsed=31, days_to_deadline=-1),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=31))
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "critical"
    assert "RBI-RES-030" in triggered
    assert result.reason_codes == rule_ids(result)
    assert triggered["RBI-RES-030"].severity == "critical"
    assert triggered["RBI-RES-030"].required_action.action_type == "notify_regulator"
    assert triggered["RBI-RES-030"].evidence == ["complaint unresolved after 31 days"]
    assert result.sla_reading.regulatory_interpretation == "breached_standard_complaint"


def test_missing_resolution_timestamp_at_sla_limit_triggers_customer_protection_review() -> None:
    complaint = make_complaint(
        complaint_id="sla-review-30",
        resolved_at=None,
        sla=SLAState(is_breached=False, breach_risk_level="high", days_elapsed=30, days_to_deadline=0),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=30))

    assert "RBI-RES-030" not in rule_ids(result)
    assert "RBI-CUST-UNRESOLVED-001" in rule_ids(result)
    assert result.compliance_risk_level == "high"
    assert result.sla_reading.proactive_flag is False
    assert result.sla_reading.regulatory_interpretation == "no_regulatory_sla_exception"


def test_missing_acknowledgement_triggers_medium_risk_with_audit_evidence() -> None:
    complaint = make_complaint(complaint_id="ack-missing", acknowledged_at=None)

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=4))
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "medium"
    assert "RBI-ACK-001" in triggered
    assert triggered["RBI-ACK-001"].mandatory_action is True
    assert triggered["RBI-ACK-001"].required_action.deadline_at == BASE_DATE + timedelta(days=3)
    assert "acknowledgement missing" in triggered["RBI-ACK-001"].evidence[0]


def test_fraud_signal_and_delayed_fraud_sla_reporting_fail_deterministically() -> None:
    complaint = make_complaint(
        complaint_id="fraud-delayed",
        issue="Unauthorized transaction and fraud claim",
        resolved_at=None,
        ai_signals=AISignals(severity="high", urgency_score=91, fraud_risk_score=88, key_issue="identity theft unauthorized debit"),
        sla=SLAState(is_breached=True, breach_risk_level="critical", days_elapsed=35, days_to_deadline=-5),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=35))
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "critical"
    assert {"RBI-FRAUD-001", "RBI-SLA-FRAUD-002", "RBI-RES-030"}.issubset(triggered)
    assert triggered["RBI-FRAUD-001"].severity == "high"
    assert triggered["RBI-SLA-FRAUD-002"].severity == "critical"
    assert any("fraud_risk_score=88" in item for item in triggered["RBI-FRAUD-001"].evidence)
    assert "SLA state is breached" in triggered["RBI-SLA-FRAUD-002"].evidence


def test_missing_fraud_report_information_remains_controlled_under_review() -> None:
    complaint = make_complaint(
        complaint_id="fraud-missing-info",
        issue="Customer reports an account problem",
        ai_signals=AISignals(severity=None, urgency_score=None, fraud_risk_score=None, key_issue=None),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE)

    assert result.triggered_rules == []
    assert result.reason_codes == []
    assert result.compliance_risk_level == "low"


def test_high_value_high_urgency_dispute_requires_proactive_review() -> None:
    complaint = make_complaint(
        complaint_id="high-value-dispute",
        issue="Transaction dispute",
        amount_disputed=100000,
        ai_signals=AISignals(severity="high", urgency_score=70),
        sla=SLAState(is_breached=False, breach_risk_level="high", days_elapsed=2, days_to_deadline=1),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=2))
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "high"
    assert triggered["RBI-HV-001"].required_action.action_type == "proactive_review"
    assert triggered["RBI-HV-001"].required_action.deadline_at == BASE_DATE + timedelta(days=2)
    assert "amount_disputed=100000.00" in triggered["RBI-HV-001"].evidence[0]
    assert "RBI-NEAR-HIGH-003" in triggered


@pytest.mark.parametrize(
    "keyword",
    [
        "court",
        "ombudsman",
        "RBI complaint",
        "legal action",
        "consumer court",
        "regulator",
        "legal notice",
    ],
)
def test_legal_or_regulatory_keywords_trigger_compliance_officer_escalation(keyword: str) -> None:
    complaint = make_complaint(
        complaint_id=f"legal-keyword-{keyword.replace(' ', '-')}",
        issue=f"Customer mentions {keyword}",
        narrative=f"Customer says they will pursue {keyword} if this is not handled.",
        ai_signals=AISignals(severity="high", urgency_score=76, key_issue=keyword),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE)
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "high"
    assert "RBI-LEGAL-001" in triggered
    assert triggered["RBI-LEGAL-001"].severity == "high"
    assert triggered["RBI-LEGAL-001"].required_action.owner == "compliance_officer"
    assert triggered["RBI-LEGAL-001"].required_action.action_type == "escalate"
    assert triggered["RBI-LEGAL-001"].required_action.deadline_at == BASE_DATE + timedelta(days=1)
    assert triggered["RBI-LEGAL-001"].evidence
    assert any(keyword.lower() in item for item in triggered["RBI-LEGAL-001"].evidence)


def test_legal_keyword_explainability_text_is_generated() -> None:
    complaint = make_complaint(
        complaint_id="legal-explainability",
        issue="Customer sent legal notice",
        narrative="Customer says they will file an RBI complaint with the ombudsman.",
        ai_signals=AISignals(severity="high", urgency_score=80, key_issue="legal notice"),
    )
    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE)

    explanation = generate_explanation(
        result.model_dump(mode="json"),
        {
            "complaint_id": complaint.complaint_id,
            "narrative": complaint.narrative,
            "issue": complaint.issue,
            "regulatory_keyword": "legal notice",
        },
    )
    legal_rule = next(rule for rule in explanation.rule_explanations if rule.rule_id == "RBI-LEGAL-001")

    assert legal_rule.why_triggered
    assert "legal or regulatory language" in legal_rule.why_triggered
    assert legal_rule.evidence_snippets == [
        f"narrative: {complaint.narrative}",
        f"issue: {complaint.issue}",
        "regulatory_keyword: legal notice",
    ]


@pytest.mark.parametrize(
    ("response_fields", "expected_evidence"),
    [
        (
            AIResponseFields(draft_response=None, resolution="Resolved with evidence"),
            "missing_required_response_fields=draft_response",
        ),
        (
            AIResponseFields(draft_response="Customer response ready", resolution=None),
            "missing_required_response_fields=resolution",
        ),
        (
            AIResponseFields(draft_response=None, resolution=None),
            "missing_required_response_fields=draft_response,resolution",
        ),
    ],
)
def test_missing_required_response_fields_rule_triggers_for_resolved_complaints(response_fields: AIResponseFields, expected_evidence: str) -> None:
    complaint = make_complaint(
        complaint_id="missing-response-fields",
        resolved_at=BASE_DATE + timedelta(days=1),
        response_fields=response_fields,
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=1))
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "medium"
    assert "RBI-RESP-001" in triggered
    assert triggered["RBI-RESP-001"].severity == "medium"
    assert triggered["RBI-RESP-001"].required_action.action_type == "close_with_evidence"
    assert triggered["RBI-RESP-001"].required_action.deadline_at == BASE_DATE
    assert triggered["RBI-RESP-001"].evidence == [expected_evidence]


def test_missing_required_response_fields_rule_does_not_trigger_when_draft_and_resolution_present() -> None:
    complaint = make_complaint(
        complaint_id="complete-response-fields",
        resolved_at=BASE_DATE + timedelta(days=1),
        response_fields=AIResponseFields(
            draft_response="Customer response ready",
            resolution="Resolved with evidence",
        ),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=1))

    assert "RBI-RESP-001" not in rule_ids(result)



def test_kyc_rules_trigger_from_configured_compliance_fields() -> None:
    complaint = make_complaint(
        complaint_id="kyc-failure",
        kyc_status="failed",
        kyc_update_overdue=True,
        kyc_missing_fields=["pan", "address_proof"],
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE)
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "critical"
    assert {"RBI-KYC-UPDATE-001", "RBI-KYC-MISSING-001", "RBI-KYC-VERIFY-001"}.issubset(triggered)
    assert triggered["RBI-KYC-UPDATE-001"].evidence == ["periodic customer KYC update is overdue"]
    assert triggered["RBI-KYC-MISSING-001"].evidence == ["missing mandatory KYC fields: pan, address_proof"]
    assert triggered["RBI-KYC-VERIFY-001"].evidence == ["customer identity/KYC verification check failed"]


def test_customer_protection_rules_trigger_for_notification_delay_and_service_breach() -> None:
    complaint = make_complaint(
        complaint_id="customer-protection-breach",
        resolved_at=None,
        customer_notified_at=BASE_DATE + timedelta(days=8),
        customer_service_breached=True,
        sla=SLAState(is_breached=False, breach_risk_level="high", days_elapsed=16, days_to_deadline=14),
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=16))
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "critical"
    assert {"RBI-CUST-NOTIFY-001", "RBI-CUST-UNRESOLVED-001", "RBI-CUST-SERVICE-001"}.issubset(triggered)
    assert triggered["RBI-CUST-NOTIFY-001"].evidence == ["customer notification delayed by 8 days (max 7 days allowed)"]
    assert triggered["RBI-CUST-UNRESOLVED-001"].evidence == ["complaint remains unresolved beyond the 15-day customer protection threshold"]
    assert triggered["RBI-CUST-SERVICE-001"].evidence == ["breached configured customer service obligations for protected workflows"]


def test_documentation_rules_trigger_for_missing_documents_and_evidence() -> None:
    complaint = make_complaint(
        complaint_id="documentation-failure",
        missing_documents=["signed_complaint", "identity_proof"],
        is_incomplete=True,
        missing_investigation_evidence=True,
    )

    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE)
    triggered = {rule.rule_id: rule for rule in result.triggered_rules}

    assert result.compliance_risk_level == "high"
    assert {"RBI-DOC-MANDATORY-001", "RBI-DOC-INCOMPLETE-001", "RBI-DOC-EVIDENCE-001"}.issubset(triggered)
    assert triggered["RBI-DOC-MANDATORY-001"].evidence == ["missing mandatory supporting documents: signed_complaint, identity_proof"]
    assert triggered["RBI-DOC-INCOMPLETE-001"].evidence == ["complaint record is incomplete and not audit ready"]
    assert triggered["RBI-DOC-EVIDENCE-001"].evidence == ["complaint investigation contains missing or insufficient evidence"]


def test_new_rule_explainability_templates_are_used_for_kyc_and_documentation() -> None:
    complaint = make_complaint(
        complaint_id="kyc-doc-explainability",
        kyc_update_overdue=True,
        missing_documents=["signed_complaint"],
    )
    result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE)

    explanation = generate_explanation(
        result.model_dump(mode="json"),
        {
            "kyc_update_overdue": complaint.kyc_update_overdue,
            "missing_documents": complaint.missing_documents,
        },
    )
    explanations = {rule.rule_id: rule for rule in explanation.rule_explanations}

    assert "Periodic KYC update is overdue" in explanations["RBI-KYC-UPDATE-001"].why_triggered
    assert "Mandatory supporting documents are missing" in explanations["RBI-DOC-MANDATORY-001"].why_triggered

def test_invalid_negative_amount_is_rejected_as_controlled_input_error() -> None:
    with pytest.raises(ValidationError, match="amount_disputed"):
        make_complaint(amount_disputed=-1)


def test_reason_code_mapping_and_risk_assignment_cover_loaded_rules() -> None:
    rules = load_rule_registry()
    severities = {rule.rule_id: rule.severity for rule in rules}

    assert severities == {
        "RBI-ACK-001": "medium",
        "RBI-FRAUD-001": "high",
        "RBI-LEGAL-001": "high",
        "RBI-RESP-001": "medium",
        "RBI-RES-030": "critical",
        "RBI-HV-001": "high",
        "RBI-SLA-FRAUD-002": "critical",
        "RBI-NEAR-HIGH-003": "medium",
        "RBI-KYC-UPDATE-001": "high",
        "RBI-KYC-MISSING-001": "high",
        "RBI-KYC-VERIFY-001": "critical",
        "RBI-CUST-NOTIFY-001": "medium",
        "RBI-CUST-UNRESOLVED-001": "high",
        "RBI-CUST-SERVICE-001": "critical",
        "RBI-DOC-MANDATORY-001": "high",
        "RBI-DOC-INCOMPLETE-001": "medium",
        "RBI-DOC-EVIDENCE-001": "high",
    }
    assert aggregate_risk([]) == "low"


def test_mock_fixture_documents_active_and_future_rule_domains(compliance_mock_data: dict) -> None:
    assert {case["expected_result"] for case in compliance_mock_data["sla_cases"]} == {"PASS", "FAIL", "UNDER_REVIEW"}
    assert {case["expected_result"] for case in compliance_mock_data["fraud_cases"]} == {"PASS", "FAIL", "UNDER_REVIEW"}
    assert all(case["implementation_status"] == "implemented_in_current_rule_registry" for case in compliance_mock_data["kyc_cases"])
    assert all(case["implementation_status"] == "implemented_in_current_rule_registry" for case in compliance_mock_data["documentation_cases"])

