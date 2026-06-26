from datetime import datetime, timezone

from app.compliance.explainability.evidence_mapper import (
    DEFAULT_RULE_FIELD_DEPENDENCIES,
    map_evidence,
)
from app.compliance.explainability.models import ComplianceExplanation, RuleExplanation
from app.compliance.explainability.risk_justifier import justify_risk
from app.compliance.explainability.rule_explainer import explain_rule


def _coerce_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Expected dict-compatible value, got {type(value).__name__}")


def _normalize_complaint_payload(complaint: dict) -> dict:
    normalized = dict(complaint)
    ai_signals = normalized.get("ai_signals") or {}
    response_fields = normalized.get("response_fields") or {}
    confidence_scores = normalized.get("confidence_scores") or {}

    if isinstance(ai_signals, dict):
        normalized.setdefault("fraud_risk_score", ai_signals.get("fraud_risk_score"))
        normalized.setdefault("urgency", ai_signals.get("severity") or ai_signals.get("urgency_score"))

    if isinstance(response_fields, dict):
        normalized.setdefault("category", response_fields.get("category"))
        normalized.setdefault("urgency", response_fields.get("urgency_score"))
        normalized.setdefault("draft_response", response_fields.get("draft_response"))
        normalized.setdefault("resolution", response_fields.get("resolution"))
        normalized.setdefault("next_action", response_fields.get("next_action"))

    if isinstance(confidence_scores, dict):
        normalized.setdefault("fraud_risk_score", confidence_scores.get("fraud_risk_score"))

    sla = normalized.get("sla") or {}
    if isinstance(sla, dict):
        normalized.setdefault("days_since_intake", sla.get("days_elapsed"))
        normalized.setdefault("days_to_deadline", sla.get("days_to_deadline"))

    return normalized


def _coerce_datetime(value: object | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Expected datetime-compatible value, got {type(value).__name__}")


def _error_explanation(rule: dict, error: Exception, evaluated_at: datetime) -> RuleExplanation:
    rule_id = str(rule.get("rule_id", "unknown_rule"))
    return RuleExplanation(
        rule_id=rule_id,
        rule_description=str(
            rule.get("rule_description")
            or rule.get("description")
            or "Rule explanation failed"
        ),
        why_triggered=f"Rule explanation failed: {type(error).__name__}: {error}",
        complaint_fields_used=[],
        evidence_snippets=[f"error: {type(error).__name__}: {error}"],
        confidence="low",
        triggered_at=_coerce_datetime(rule.get("triggered_at", evaluated_at)),
    )


def generate_explanation(
    compliance_result: dict,
    complaint: dict,
) -> ComplianceExplanation:
    result = _coerce_dict(compliance_result)
    complaint_payload = _normalize_complaint_payload(_coerce_dict(complaint))
    evaluated_at = _coerce_datetime(result.get("evaluated_at"))

    rule_explanations: list[RuleExplanation] = []
    for raw_rule in result.get("triggered_rules", []):
        try:
            rule = _coerce_dict(raw_rule)
            evidence = map_evidence(
                complaint_payload,
                str(rule["rule_id"]),
                DEFAULT_RULE_FIELD_DEPENDENCIES,
            )
            rule_explanations.append(explain_rule(rule, evidence))
        except Exception as error:
            rule_explanations.append(_error_explanation(_coerce_dict(raw_rule), error, evaluated_at))

    risk_level = str(
        result.get("compliance_risk_level")
        or result.get("risk_level")
        or "low"
    )
    risk_justification = justify_risk(rule_explanations, risk_level)

    return ComplianceExplanation(
        complaint_id=str(result.get("complaint_id") or complaint_payload["complaint_id"]),
        evaluated_at=evaluated_at,
        rule_explanations=rule_explanations,
        risk_justification=risk_justification,
        audit_metadata={
            "engine_version": result.get("engine_version", "unknown"),
            "rule_set_version": result.get("rule_set_version", "unknown"),
            "evaluated_at": evaluated_at,
        },
    )
