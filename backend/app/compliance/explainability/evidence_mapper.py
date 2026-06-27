DEFAULT_RULE_FIELD_DEPENDENCIES: dict[str, list[str]] = {
    "RBI-ACK-001": ["acknowledged_at", "date_received", "days_since_intake"],
    "RBI-FRAUD-001": ["category", "issue", "fraud_risk_score"],
    "RBI-LEGAL-001": ["narrative", "issue", "regulatory_keyword"],
    "RBI-RESP-001": ["draft_response", "resolution"],
    "RBI-RES-030": ["resolved_at", "date_received", "days_since_intake"],
    "RBI-HV-001": ["amount_disputed", "urgency", "category"],
    "RBI-SLA-FRAUD-002": ["category", "days_since_intake", "fraud_risk_score"],
    "RBI-NEAR-HIGH-003": ["urgency", "sentiment", "days_to_deadline"],
    "RBI-KYC-UPDATE-001": ["kyc_update_overdue"],
    "RBI-KYC-MISSING-001": ["kyc_missing_fields"],
    "RBI-KYC-VERIFY-001": ["kyc_status"],
    "RBI-CUST-NOTIFY-001": ["customer_notified_at", "date_received"],
    "RBI-CUST-UNRESOLVED-001": ["days_elapsed"],
    "RBI-CUST-SERVICE-001": ["customer_service_breached"],
    "RBI-DOC-MANDATORY-001": ["missing_documents"],
    "RBI-DOC-INCOMPLETE-001": ["is_incomplete"],
    "RBI-DOC-EVIDENCE-001": ["missing_investigation_evidence"],
}


def map_evidence(
    complaint: dict,
    rule_id: str,
    rule_field_dependencies: dict[str, list[str]],
) -> list[str]:
    fields = rule_field_dependencies.get(rule_id, [])
    evidence: list[str] = []

    for field_name in fields:
        value = complaint.get(field_name)
        if value is None:
            evidence.append(f"{field_name}: not available")
        else:
            evidence.append(f"{field_name}: {value}")

    return evidence

