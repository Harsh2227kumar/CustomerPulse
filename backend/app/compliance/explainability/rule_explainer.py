from datetime import datetime, timezone

from app.compliance.explainability.models import RuleExplanation


RULE_EXPLANATION_TEMPLATES: dict[str, str] = {
    "RBI-ACK-001": "This rule triggered because the complaint acknowledgement timing requires compliance review. Evidence considered: {evidence}.",
    "RBI-FRAUD-001": "This rule triggered because fraud or unauthorized-transaction signals require escalation. Evidence considered: {evidence}.",
    "RBI-LEGAL-001": "This rule triggered because legal or regulatory language requires compliance officer review. Evidence considered: {evidence}.",
    "RBI-RESP-001": "This rule triggered because required resolution response fields are missing. Evidence considered: {evidence}.",
    "RBI-RES-030": "This rule triggered because the complaint remains unresolved beyond the regulatory review threshold. Evidence considered: {evidence}.",
    "RBI-HV-001": "This rule triggered because a high-value urgent dispute requires stricter SLA handling. Evidence considered: {evidence}.",
    "RBI-SLA-FRAUD-002": "This rule triggered because an SLA breach on a fraud or unauthorized complaint is a critical compliance event. Evidence considered: {evidence}.",
    "RBI-NEAR-HIGH-003": "This rule triggered because a high-severity complaint is close to breaching its SLA. Evidence considered: {evidence}.",
    "RBI-KYC-UPDATE-001": "Periodic KYC update is overdue for this customer record. Evidence: {evidence}.",
    "RBI-KYC-MISSING-001": "Mandatory KYC fields are missing from this account. Evidence: {evidence}.",
    "RBI-KYC-VERIFY-001": "KYC verification checks failed for this record. Evidence: {evidence}.",
    "RBI-CUST-NOTIFY-001": "Notification of complaint receipt or resolution was delayed. Evidence: {evidence}.",
    "RBI-CUST-UNRESOLVED-001": "Complaint is unresolved beyond customer protection threshold. Evidence: {evidence}.",
    "RBI-CUST-SERVICE-001": "Breach of customer service obligations on protected workflow. Evidence: {evidence}.",
    "RBI-DOC-MANDATORY-001": "Mandatory supporting documents are missing from complaint dossier. Evidence: {evidence}.",
    "RBI-DOC-INCOMPLETE-001": "Complaint record is incomplete and not audit ready. Evidence: {evidence}.",
    "RBI-DOC-EVIDENCE-001": "Investigation dossier is missing critical evidentiary backing. Evidence: {evidence}.",
    "acknowledgement": "This acknowledgement rule triggered based on complaint intake and acknowledgement evidence. Evidence considered: {evidence}.",
    "fraud": "This fraud rule triggered based on category, issue, and risk signal evidence. Evidence considered: {evidence}.",
    "sla": "This SLA rule triggered based on deadline and complaint lifecycle evidence. Evidence considered: {evidence}.",
}


def explain_rule(
    triggered_rule: dict,
    evidence: list[str],
) -> RuleExplanation:
    rule_id = str(triggered_rule["rule_id"])
    rule_category = triggered_rule.get("rule_category") or triggered_rule.get("category")
    template = RULE_EXPLANATION_TEMPLATES.get(rule_id)
    if template is None and rule_category is not None:
        template = RULE_EXPLANATION_TEMPLATES.get(str(rule_category))
    if template is None:
        template = "This rule triggered based on the compliance engine result. Evidence considered: {evidence}."

    missing_count = sum(item.endswith(": not available") for item in evidence)
    if missing_count == 0:
        confidence = "high"
    elif missing_count == 1:
        confidence = "medium"
    else:
        confidence = "low"

    triggered_at = triggered_rule.get("triggered_at")
    if triggered_at is None:
        triggered_at = datetime.now(timezone.utc)
    elif isinstance(triggered_at, str):
        triggered_at = datetime.fromisoformat(triggered_at.replace("Z", "+00:00"))

    fields_used = [item.split(":", 1)[0] for item in evidence]
    evidence_text = "; ".join(evidence) if evidence else "no mapped evidence"

    why_triggered = template.format(evidence=evidence_text)
    if triggered_rule.get("severity") is not None:
        why_triggered = f"{why_triggered} Compliance severity: {triggered_rule['severity']}."

    return RuleExplanation(
        rule_id=rule_id,
        rule_description=str(
            triggered_rule.get("rule_description")
            or triggered_rule.get("description")
            or "Rule description unavailable"
        ),
        why_triggered=why_triggered,
        complaint_fields_used=fields_used,
        evidence_snippets=evidence,
        confidence=confidence,
        triggered_at=triggered_at,
    )

