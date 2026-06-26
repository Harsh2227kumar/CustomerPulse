from app.compliance.models import ComplaintComplianceInput, SLAComplianceReading


def interpret_sla_state(complaint: ComplaintComplianceInput) -> SLAComplianceReading:
    sla = complaint.sla
    risk = sla.breach_risk_level
    is_fraud = _has_fraud_signal(complaint)

    if sla.is_breached and is_fraud:
        interpretation = "breached_fraud_or_unauthorized_complaint"
        proactive = True
    elif sla.is_breached:
        interpretation = "breached_standard_complaint"
        proactive = True
    elif risk in {"high", "critical"} and _is_high_severity(complaint):
        interpretation = "near_breach_high_severity_complaint"
        proactive = True
    else:
        interpretation = "no_regulatory_sla_exception"
        proactive = False

    return SLAComplianceReading(
        is_breached=sla.is_breached,
        breach_risk_level=risk,
        regulatory_interpretation=interpretation,
        proactive_flag=proactive,
    )


def _has_fraud_signal(complaint: ComplaintComplianceInput) -> bool:
    text = " ".join(
        part or ""
        for part in (
            complaint.product,
            complaint.issue,
            complaint.sub_issue,
            complaint.ai_signals.key_issue,
        )
    ).lower()
    return (
        "fraud" in text
        or "unauthorized" in text
        or "identity theft" in text
        or (complaint.ai_signals.fraud_risk_score or 0) >= 75
    )


def _is_high_severity(complaint: ComplaintComplianceInput) -> bool:
    severity = (complaint.ai_signals.severity or "").lower()
    return severity in {"high", "critical"} or (complaint.ai_signals.urgency_score or 0) >= 70
