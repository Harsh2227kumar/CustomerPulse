from app.intelligence.evidence_service import EvidenceService
from app.intelligence.reason_codes import detect_reason_codes
from app.schemas.ai_response import DecisionSource, RiskSignalResult


# Calibrated from collab/customerpulse_profile/risk_signal_calibration_summary.json.
RISK_WEIGHTS = {
    "identity_theft_signal": 0.95,
    "legal_or_fraud_language": 0.90,
    "unauthorized_transaction": 0.85,
    "financial_harm": 0.75,
    "high_urgency_language": 0.70,
    "delayed_response": 0.55,
    "fee_dispute": 0.40,
    "refund_dispute": 0.35,
    "credit_reporting_issue": 0.30,
    "loan_or_mortgage_issue": 0.30,
    "account_access_issue": 0.25,
    "duplicate_charge": 0.20,
    "debt_collection_issue": 0.30,
    "payment_or_transfer_issue": 0.30,
}

FRAUD_CODES = {
    "identity_theft_signal",
    "legal_or_fraud_language",
    "unauthorized_transaction",
}

ESCALATION_CODES = {
    "identity_theft_signal",
    "legal_or_fraud_language",
    "unauthorized_transaction",
    "financial_harm",
    "high_urgency_language",
    "delayed_response",
    "low_confidence_candidate",
}


class RiskSignalService:
    def __init__(self, evidence_service: EvidenceService | None = None) -> None:
        self.evidence_service = evidence_service or EvidenceService()

    def score(
        self,
        narrative: str,
        *,
        urgency_score: int | None = None,
        ai_confidence: float | None = None,
    ) -> RiskSignalResult:
        reason_codes = detect_reason_codes(narrative)
        if urgency_score is not None and urgency_score >= 85:
            reason_codes.append("critical_severity")
        if ai_confidence is not None and ai_confidence < 0.45:
            reason_codes.append("low_confidence_candidate")

        score = self._weighted_score(reason_codes)
        if urgency_score is not None:
            score = max(score, urgency_score)
        fraud_score = self._weighted_score([code for code in reason_codes if code in FRAUD_CODES])
        escalation_score = self._weighted_score([code for code in reason_codes if code in ESCALATION_CODES])
        if urgency_score is not None:
            escalation_score = max(escalation_score, urgency_score)

        hard_blockers = self._hard_blockers(reason_codes)
        level = self._level(score)
        return RiskSignalResult(
            score=score,
            level=level,
            reason_codes=sorted(set(reason_codes)),
            evidence_snippets=self.evidence_service.snippets_for_text(narrative, max_snippets=5),
            confidence=0.86 if reason_codes else 0.58,
            recommended_action=self._recommended_action(level, hard_blockers),
            source=DecisionSource(
                provider="customerpulse",
                model="calibrated-risk-signals-v2",
                version="risk-signal-calibration-2026-06-23",
            ),
            fraud_risk_score=fraud_score,
            escalation_risk_score=escalation_score,
            hard_blockers=hard_blockers,
        )

    def _weighted_score(self, reason_codes: list[str]) -> int:
        total = sum(RISK_WEIGHTS.get(code, 0.0) for code in set(reason_codes))
        if "unauthorized_transaction" in reason_codes and "financial_harm" in reason_codes:
            total += 0.35
        if "legal_or_fraud_language" in reason_codes and "high_urgency_language" in reason_codes:
            total += 0.35
        if "identity_theft_signal" in reason_codes and "financial_harm" in reason_codes:
            total += 0.35
        if "critical_severity" in reason_codes:
            total = max(total, 2.7)
        return min(100, round(20 + total * 25))

    def _hard_blockers(self, reason_codes: list[str]) -> list[str]:
        codes = set(reason_codes)
        blockers = []
        if "identity_theft_signal" in codes:
            blockers.append("identity_theft_signal")
        if "legal_or_fraud_language" in codes:
            blockers.append("legal_or_fraud_language")
        if "critical_severity" in codes:
            blockers.append("critical_severity")
        if "high_urgency_language" in codes:
            blockers.append("high_urgency_language")
        if "low_confidence_candidate" in codes:
            blockers.append("low_confidence_candidate")
        if {"unauthorized_transaction", "financial_harm"}.issubset(codes):
            blockers.append("unauthorized_transaction_with_financial_harm")
        return sorted(set(blockers))

    def _level(self, score: int) -> str:
        if score >= 85:
            return "Critical"
        if score >= 65:
            return "High"
        if score >= 40:
            return "Medium"
        return "Low"

    def _recommended_action(self, level: str, hard_blockers: list[str]) -> str:
        if hard_blockers:
            return "Do not auto-reuse responses; route for human validation."
        if level == "Critical":
            return "Route for urgent human review before response reuse."
        if level == "High":
            return "Prioritize agent review and verify evidence before drafting."
        if level == "Medium":
            return "Review supporting evidence and continue standard handling."
        return "Continue standard processing."
