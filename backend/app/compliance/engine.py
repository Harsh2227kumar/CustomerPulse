from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.compliance.models import (
    COMPLIANCE_ENGINE_VERSION,
    COMPLIANCE_RULE_SET_VERSION,
    ComplaintComplianceInput,
    ComplianceResult,
    ComplianceRule,
    RequiredAction,
    TriggeredRule,
)
from app.compliance.risk_aggregator import aggregate_risk
from app.compliance.rule_registry import load_rule_registry
from app.compliance.sla_interpreter import interpret_sla_state


RuleEvaluator = Callable[[ComplaintComplianceInput], list[str]]
LEGAL_REGULATORY_KEYWORDS = (
    "court",
    "ombudsman",
    "rbi complaint",
    "rbi grievance",
    "legal action",
    "consumer court",
    "regulator",
    "legal notice",
)
REQUIRED_RESPONSE_FIELDS = ("draft_response", "resolution")


class ComplianceEngine:
    def __init__(self, rules: tuple[ComplianceRule, ...] | None = None) -> None:
        self.rules = rules or load_rule_registry()
        self._evaluators: dict[str, RuleEvaluator] = {
            "acknowledgement_overdue": self._acknowledgement_overdue,
            "fraud_or_unauthorized_signal": self._fraud_or_unauthorized_signal,
            "legal_or_regulatory_keyword": self._legal_or_regulatory_keyword,
            "missing_required_response_fields": self._missing_required_response_fields,
            "unresolved_over_30_days": self._unresolved_over_30_days,
            "high_value_high_urgency_dispute": self._high_value_high_urgency_dispute,
            "fraud_sla_breach": self._fraud_sla_breach,
            "near_breach_high_severity": self._near_breach_high_severity,
            "kyc_update_overdue": self._kyc_update_overdue,
            "kyc_missing_information": self._kyc_missing_information,
            "kyc_verification_failure": self._kyc_verification_failure,
            "customer_notification_delay": self._customer_notification_delay,
            "customer_unresolved_beyond_threshold": self._customer_unresolved_beyond_threshold,
            "customer_service_obligation_breach": self._customer_service_obligation_breach,
            "missing_mandatory_documents": self._missing_mandatory_documents,
            "incomplete_complaint_record": self._incomplete_complaint_record,
            "missing_investigation_evidence": self._missing_investigation_evidence,
        }

    def evaluate(self, complaint: ComplaintComplianceInput, evaluated_at: datetime | None = None) -> ComplianceResult:
        evaluated_at = evaluated_at or datetime.now(UTC)
        triggered_rules: list[TriggeredRule] = []

        for rule in self.rules:
            evaluator = self._evaluators.get(rule.condition_type)
            if evaluator is None:
                continue
            evidence = evaluator(complaint)
            if not evidence:
                continue
            triggered_rules.append(
                TriggeredRule(
                    rule_id=rule.rule_id,
                    description=rule.description,
                    severity=rule.severity,
                    mandatory_action=rule.mandatory_action,
                    evidence=evidence,
                    triggered_at=evaluated_at,
                    required_action=RequiredAction(
                        action_type=rule.action.action_type,
                        owner=rule.action.owner,
                        description=rule.action.description,
                        deadline_at=complaint.date_received + timedelta(days=rule.action.deadline_days),
                    ),
                )
            )

        return ComplianceResult(
            complaint_id=complaint.complaint_id,
            source_complaint_id=complaint.source_complaint_id,
            compliance_risk_level=aggregate_risk(triggered_rules),
            triggered_rules=triggered_rules,
            required_actions=[rule.required_action for rule in triggered_rules],
            reason_codes=[rule.rule_id for rule in triggered_rules],
            sla_reading=interpret_sla_state(complaint),
            evaluated_at=evaluated_at,
            engine_version=COMPLIANCE_ENGINE_VERSION,
            rule_set_version=COMPLIANCE_RULE_SET_VERSION,
        )

    def _acknowledgement_overdue(self, complaint: ComplaintComplianceInput) -> list[str]:
        deadline = complaint.date_received + timedelta(days=3)
        if complaint.acknowledged_at is None:
            return [f"acknowledgement missing; required by {deadline.isoformat()}"]
        if complaint.acknowledged_at > deadline:
            return [f"acknowledged at {complaint.acknowledged_at.isoformat()}, after {deadline.isoformat()}"]
        return []

    def _fraud_or_unauthorized_signal(self, complaint: ComplaintComplianceInput) -> list[str]:
        return self._fraud_evidence(complaint)

    def _legal_or_regulatory_keyword(self, complaint: ComplaintComplianceInput) -> list[str]:
        text = self._combined_text(complaint)
        return [f"legal_regulatory_keyword={keyword}" for keyword in LEGAL_REGULATORY_KEYWORDS if keyword in text]

    def _missing_required_response_fields(self, complaint: ComplaintComplianceInput) -> list[str]:
        response = complaint.response_fields
        missing = [
            field
            for field in REQUIRED_RESPONSE_FIELDS
            if getattr(response, field) is None or getattr(response, field) == ""
        ]
        if not missing:
            return []
        return [f"missing_required_response_fields={','.join(missing)}"]

    def _unresolved_over_30_days(self, complaint: ComplaintComplianceInput) -> list[str]:
        if complaint.resolved_at is not None:
            return []
        days_elapsed = complaint.sla.days_elapsed
        if days_elapsed is not None and days_elapsed > 30:
            return [f"complaint unresolved after {days_elapsed} days"]
        return []

    def _high_value_high_urgency_dispute(self, complaint: ComplaintComplianceInput) -> list[str]:
        amount = complaint.amount_disputed or 0
        urgency = complaint.ai_signals.urgency_score or 0
        text = self._combined_text(complaint)
        if amount >= 100000 and urgency >= 70 and any(term in text for term in ("dispute", "transaction", "charge")):
            return [f"amount_disputed={amount:.2f}; urgency_score={urgency}"]
        return []

    def _fraud_sla_breach(self, complaint: ComplaintComplianceInput) -> list[str]:
        if not complaint.sla.is_breached:
            return []
        fraud_evidence = self._fraud_evidence(complaint)
        if fraud_evidence:
            return [*fraud_evidence, "SLA state is breached"]
        return []

    def _near_breach_high_severity(self, complaint: ComplaintComplianceInput) -> list[str]:
        risk = complaint.sla.breach_risk_level
        severity = (complaint.ai_signals.severity or "").lower()
        urgency = complaint.ai_signals.urgency_score or 0
        if not complaint.sla.is_breached and risk in {"high", "critical"} and (severity in {"high", "critical"} or urgency >= 70):
            return [f"SLA breach risk is {risk}; severity={severity or 'unknown'}; urgency_score={urgency}"]
        return []

    def _kyc_update_overdue(self, complaint: ComplaintComplianceInput) -> list[str]:
        if complaint.kyc_update_overdue:
            return ["periodic customer KYC update is overdue"]
        return []

    def _kyc_missing_information(self, complaint: ComplaintComplianceInput) -> list[str]:
        if complaint.kyc_missing_fields:
            return [f"missing mandatory KYC fields: {', '.join(complaint.kyc_missing_fields)}"]
        return []

    def _kyc_verification_failure(self, complaint: ComplaintComplianceInput) -> list[str]:
        if (complaint.kyc_status or "").lower() == "failed":
            return ["customer identity/KYC verification check failed"]
        return []

    def _customer_notification_delay(self, complaint: ComplaintComplianceInput) -> list[str]:
        if complaint.customer_notified_at is None:
            return []
        delay_days = (complaint.customer_notified_at - complaint.date_received).days
        if delay_days > 7:
            return [f"customer notification delayed by {delay_days} days (max 7 days allowed)"]
        return []

    def _customer_unresolved_beyond_threshold(self, complaint: ComplaintComplianceInput) -> list[str]:
        days_elapsed = complaint.sla.days_elapsed or 0
        protected_workflow = complaint.customer_notified_at is not None or complaint.customer_service_breached
        unresolved_at_sla_limit = days_elapsed >= 30
        protected_workflow_breach = protected_workflow and days_elapsed > 15
        if complaint.resolved_at is None and (unresolved_at_sla_limit or protected_workflow_breach):
            return ["complaint remains unresolved beyond the 15-day customer protection threshold"]
        return []

    def _customer_service_obligation_breach(self, complaint: ComplaintComplianceInput) -> list[str]:
        if complaint.customer_service_breached:
            return ["breached configured customer service obligations for protected workflows"]
        return []

    def _missing_mandatory_documents(self, complaint: ComplaintComplianceInput) -> list[str]:
        if complaint.missing_documents:
            return [f"missing mandatory supporting documents: {', '.join(complaint.missing_documents)}"]
        return []

    def _incomplete_complaint_record(self, complaint: ComplaintComplianceInput) -> list[str]:
        if complaint.is_incomplete:
            return ["complaint record is incomplete and not audit ready"]
        return []

    def _missing_investigation_evidence(self, complaint: ComplaintComplianceInput) -> list[str]:
        if complaint.missing_investigation_evidence:
            return ["complaint investigation contains missing or insufficient evidence"]
        return []

    def _fraud_evidence(self, complaint: ComplaintComplianceInput) -> list[str]:
        evidence: list[str] = []
        text = self._combined_text(complaint)
        for term in ("fraud", "unauthorized", "identity theft"):
            if term in text:
                evidence.append(f"{term} signal present in complaint metadata")
        fraud_score = complaint.ai_signals.fraud_risk_score
        if fraud_score is not None and fraud_score >= 75:
            evidence.append(f"fraud_risk_score={fraud_score}")
        return evidence

    def _combined_text(self, complaint: ComplaintComplianceInput) -> str:
        return " ".join(
            part or ""
            for part in (
                complaint.product,
                complaint.issue,
                complaint.sub_issue,
                complaint.narrative,
                complaint.ai_signals.key_issue,
                complaint.response_fields.category,
                complaint.response_fields.draft_response,
                complaint.response_fields.next_action,
            )
        ).lower()

