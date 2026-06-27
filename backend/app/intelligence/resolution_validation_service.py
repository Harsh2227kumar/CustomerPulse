from app.intelligence.evidence_service import EvidenceService
from app.intelligence.reason_codes import detect_reason_codes
from app.intelligence.similarity_policy import (
    EVIDENCE_STRENGTH_REVIEW_MIN,
    EVIDENCE_STRENGTH_SAFE_MIN,
    REASON_CODE_OVERLAP_REVIEW_MIN,
    REASON_CODE_OVERLAP_SAFE_MIN,
    RETRIEVAL_THRESHOLD,
    SAFE_REUSE_THRESHOLD,
)
from app.schemas.ai_response import (
    DecisionSource,
    ResolutionValidationResult,
    SimilarCaseEvidence,
)


HARD_BLOCKER_CODES = {
    "fraud_risk",
    "identity_theft_signal",
    "legal_or_fraud_language",
    "critical_severity",
    "high_urgency_language",
    "low_confidence_candidate",
    "weak_evidence",
    "no_approved_response",
}

PRODUCT_FAMILIES = {
    "credit": ("credit reporting", "consumer report", "credit repair"),
    "card": ("credit card", "prepaid card", "debit card", "card"),
    "account": ("checking", "savings", "bank account", "deposit"),
    "loan": ("loan", "mortgage", "lease", "payday", "student loan", "vehicle loan"),
    "debt": ("debt collection", "debt collector"),
    "transfer": ("money transfer", "virtual currency", "money service", "wallet", "zelle", "cash app"),
}

ISSUE_FAMILIES = {
    "unauthorized": ("unauthorized", "fraud", "scam", "not authorized"),
    "fees": ("fee", "fees", "interest", "charged", "billing"),
    "account_management": ("managing", "opening", "closing", "access", "hold"),
    "credit_report": ("credit report", "information on your report", "investigation", "improper use"),
    "payment": ("payment", "transaction", "transfer", "money was not available"),
    "debt_collection": ("collect", "debt", "validation", "communication tactics"),
    "loan_servicing": ("servicing", "mortgage", "repay", "foreclosure", "escrow"),
}


class ResolutionValidationService:
    def __init__(self, evidence_service: EvidenceService | None = None) -> None:
        self.evidence_service = evidence_service or EvidenceService()

    def validate(
        self,
        narrative: str,
        *,
        current_category: str | None,
        similar_cases: list[SimilarCaseEvidence],
        risk_reason_codes: list[str],
        current_product: str | None = None,
        current_issue: str | None = None,
        current_reason_codes: list[str] | None = None,
        timely_response_no: bool = False,
    ) -> ResolutionValidationResult:
        evidence = self.evidence_service.snippets_for_text(narrative, max_snippets=3)
        evidence_strength = self._evidence_strength(
            narrative,
            evidence_count=len(evidence),
            has_exact_phrase=any(snippet.matched_phrase for snippet in evidence),
            product=current_product,
            issue=current_issue,
            reason_codes=current_reason_codes or risk_reason_codes,
        )
        current_codes = sorted(set(current_reason_codes or risk_reason_codes or detect_reason_codes(narrative)))

        if not similar_cases:
            return self._result(
                status="bad_match",
                reason_codes=["no_similar_resolution_evidence"],
                confidence=0.72,
                narrative=narrative,
                evidence_strength=evidence_strength,
                recommendation="Do not reuse response automatically. No candidate passed retrieval.",
                notes="No similar approved case evidence was available.",
            )

        best_case = max(similar_cases, key=lambda case: case.similarity_score)
        category_match = self._normalized(current_category) == self._normalized(best_case.category)
        product_match = self._normalized(current_product) == self._normalized(best_case.product)
        issue_match = self._normalized(current_issue) == self._normalized(best_case.issue)
        product_family_match = self._same_family(current_product, best_case.product, PRODUCT_FAMILIES)
        issue_family_match = self._same_family(current_issue, best_case.issue, ISSUE_FAMILIES)
        reason_overlap = self._jaccard(current_codes, best_case.reason_codes)
        hard_blockers = self._hard_blockers(
            risk_reason_codes=current_codes,
            evidence_strength=evidence_strength,
            approved_response=best_case.approved_response,
            category_match=category_match,
            product_family_match=product_family_match,
            issue_family_match=issue_family_match,
            reason_overlap=reason_overlap,
            timely_response_no=timely_response_no,
        )

        if best_case.similarity_score < RETRIEVAL_THRESHOLD:
            return self._candidate_result(
                status="bad_match",
                reason_codes=["similarity_below_retrieval_threshold"],
                confidence=0.86,
                narrative=narrative,
                best_case=best_case,
                reason_overlap=reason_overlap,
                evidence_strength=evidence_strength,
                category_match=category_match,
                product_match=product_match,
                issue_match=issue_match,
                product_family_match=product_family_match,
                issue_family_match=issue_family_match,
                hard_blockers=hard_blockers,
                recommendation="Do not reuse response automatically. Candidate did not pass retrieval threshold.",
            )

        escalate_reasons = self._escalation_reasons(current_codes, timely_response_no)
        if escalate_reasons:
            return self._candidate_result(
                status="escalate",
                reason_codes=["high_similarity_but_risky", "manual_validation_required", *escalate_reasons],
                confidence=0.88,
                narrative=narrative,
                best_case=best_case,
                reason_overlap=reason_overlap,
                evidence_strength=evidence_strength,
                category_match=category_match,
                product_match=product_match,
                issue_match=issue_match,
                product_family_match=product_family_match,
                issue_family_match=issue_family_match,
                hard_blockers=hard_blockers,
                recommendation="Do not reuse response automatically. Escalate for specialist review.",
            )

        if hard_blockers:
            return self._candidate_result(
                status="manual_review",
                reason_codes=["candidate_related_but_blocked", "manual_validation_required"],
                confidence=0.82,
                narrative=narrative,
                best_case=best_case,
                reason_overlap=reason_overlap,
                evidence_strength=evidence_strength,
                category_match=category_match,
                product_match=product_match,
                issue_match=issue_match,
                product_family_match=product_family_match,
                issue_family_match=issue_family_match,
                hard_blockers=hard_blockers,
                recommendation="Do not reuse response automatically. Route for manual validation.",
            )

        family_match = (product_match or product_family_match) and (issue_match or issue_family_match)
        if (
            best_case.similarity_score >= SAFE_REUSE_THRESHOLD
            and category_match
            and family_match
            and reason_overlap >= REASON_CODE_OVERLAP_SAFE_MIN
            and evidence_strength >= EVIDENCE_STRENGTH_SAFE_MIN
            and best_case.approved_response
        ):
            return self._candidate_result(
                status="safe_reuse",
                reason_codes=["similar_case_match", "same_issue_family", "strong_evidence"],
                confidence=min(0.96, max(0.82, best_case.similarity_score)),
                narrative=narrative,
                best_case=best_case,
                reason_overlap=reason_overlap,
                evidence_strength=evidence_strength,
                category_match=category_match,
                product_match=product_match,
                issue_match=issue_match,
                product_family_match=product_family_match,
                issue_family_match=issue_family_match,
                hard_blockers=[],
                recommendation="Reuse candidate response with agent visibility.",
            )

        if (
            best_case.similarity_score >= RETRIEVAL_THRESHOLD
            and (reason_overlap >= REASON_CODE_OVERLAP_REVIEW_MIN or product_family_match or issue_family_match)
            and evidence_strength >= EVIDENCE_STRENGTH_REVIEW_MIN
        ):
            return self._candidate_result(
                status="manual_review",
                reason_codes=["candidate_related", "soft_reuse_conditions_failed"],
                confidence=0.78,
                narrative=narrative,
                best_case=best_case,
                reason_overlap=reason_overlap,
                evidence_strength=evidence_strength,
                category_match=category_match,
                product_match=product_match,
                issue_match=issue_match,
                product_family_match=product_family_match,
                issue_family_match=issue_family_match,
                hard_blockers=[],
                recommendation="Candidate is related, but agent review is required before reuse.",
            )

        return self._candidate_result(
            status="bad_match",
            reason_codes=["category_or_family_mismatch", "low_reason_overlap"],
            confidence=0.84,
            narrative=narrative,
            best_case=best_case,
            reason_overlap=reason_overlap,
            evidence_strength=evidence_strength,
            category_match=category_match,
            product_match=product_match,
            issue_match=issue_match,
            product_family_match=product_family_match,
            issue_family_match=issue_family_match,
            hard_blockers=hard_blockers,
            recommendation="Do not reuse response automatically. Candidate failed validation gates.",
        )

    def _candidate_result(
        self,
        *,
        status: str,
        reason_codes: list[str],
        confidence: float,
        narrative: str,
        best_case: SimilarCaseEvidence,
        reason_overlap: float,
        evidence_strength: float,
        category_match: bool,
        product_match: bool,
        issue_match: bool,
        product_family_match: bool,
        issue_family_match: bool,
        hard_blockers: list[str],
        recommendation: str,
    ) -> ResolutionValidationResult:
        return ResolutionValidationResult(
            status=status,
            reason_codes=sorted(set(reason_codes)),
            evidence_snippets=self.evidence_service.snippets_for_text(narrative, max_snippets=3),
            confidence=confidence,
            source=DecisionSource(
                provider="customerpulse",
                model="hybrid-resolution-validation-v2",
                version="colab-threshold-summary-2026-06-23",
            ),
            similarity_score=best_case.similarity_score,
            reason_code_overlap=round(reason_overlap, 4),
            evidence_strength=round(evidence_strength, 4),
            category_match=category_match,
            product_match=product_match,
            issue_match=issue_match,
            product_family_match=product_family_match,
            issue_family_match=issue_family_match,
            hard_blockers=hard_blockers,
            recommendation=recommendation,
            notes="Similarity finds candidates; validation decides reuse.",
        )

    def _result(
        self,
        status: str,
        reason_codes: list[str],
        confidence: float,
        narrative: str,
        recommendation: str,
        notes: str,
        evidence_strength: float | None = None,
    ) -> ResolutionValidationResult:
        return ResolutionValidationResult(
            status=status,
            reason_codes=reason_codes,
            evidence_snippets=self.evidence_service.snippets_for_text(narrative, max_snippets=3),
            confidence=confidence,
            source=DecisionSource(
                provider="customerpulse",
                model="hybrid-resolution-validation-v2",
                version="colab-threshold-summary-2026-06-23",
            ),
            evidence_strength=evidence_strength,
            recommendation=recommendation,
            notes=notes,
        )

    def _jaccard(self, current: list[str], candidate: list[str]) -> float:
        current_set = set(current)
        candidate_set = set(candidate)
        union = current_set | candidate_set
        if not union:
            return 0.0
        return len(current_set & candidate_set) / len(union)

    def _evidence_strength(
        self,
        narrative: str,
        *,
        evidence_count: int,
        has_exact_phrase: bool,
        product: str | None,
        issue: str | None,
        reason_codes: list[str],
    ) -> float:
        score = 0.0
        if evidence_count > 0:
            score += 0.30
        if has_exact_phrase:
            score += 0.20
        if self._product_issue_supports_reason(product, issue, reason_codes):
            score += 0.20
        if len(narrative) >= 240:
            score += 0.20
        if evidence_count > 1:
            score += 0.10
        return min(1.0, score)

    def _product_issue_supports_reason(
        self,
        product: str | None,
        issue: str | None,
        reason_codes: list[str],
    ) -> bool:
        text = self._normalized(" ".join([product or "", issue or ""]))
        checks = {
            "credit_reporting_issue": ("credit", "report"),
            "loan_or_mortgage_issue": ("loan", "mortgage"),
            "unauthorized_transaction": ("unauthorized", "transaction", "charging"),
            "fee_dispute": ("fee", "interest", "charged"),
            "debt_collection_issue": ("debt", "collect"),
            "payment_or_transfer_issue": ("transfer", "transaction", "money"),
            "account_access_issue": ("account", "access", "hold"),
        }
        return any(any(term in text for term in checks.get(code, ())) for code in reason_codes)

    def _hard_blockers(
        self,
        *,
        risk_reason_codes: list[str],
        evidence_strength: float,
        approved_response: str | None,
        category_match: bool,
        product_family_match: bool,
        issue_family_match: bool,
        reason_overlap: float,
        timely_response_no: bool,
    ) -> list[str]:
        codes = set(risk_reason_codes)
        blockers = sorted(HARD_BLOCKER_CODES & codes)
        if "unauthorized_transaction" in codes and "financial_harm" in codes:
            blockers.append("unauthorized_transaction_with_financial_harm")
        if "delayed_response" in codes and timely_response_no:
            blockers.append("delayed_response_with_timely_response_no")
        if evidence_strength < EVIDENCE_STRENGTH_REVIEW_MIN:
            blockers.append("weak_evidence")
        if not approved_response:
            blockers.append("no_approved_response")
        if not category_match and not (product_family_match or issue_family_match) and reason_overlap < REASON_CODE_OVERLAP_REVIEW_MIN:
            blockers.append("category_product_issue_mismatch_low_reason_overlap")
        return sorted(set(blockers))

    def _escalation_reasons(self, reason_codes: list[str], timely_response_no: bool) -> list[str]:
        codes = set(reason_codes)
        reasons: list[str] = []
        if {"identity_theft_signal", "financial_harm"}.issubset(codes):
            reasons.append("identity_theft_plus_financial_harm")
        if {"unauthorized_transaction", "financial_harm"}.issubset(codes):
            reasons.append("unauthorized_transaction_plus_financial_harm")
        if {"legal_or_fraud_language", "high_urgency_language"}.issubset(codes):
            reasons.append("legal_or_regulatory_language_plus_high_urgency")
        if "critical_severity" in codes:
            reasons.append("critical_severity")
        if "unauthorized_transaction" in codes and ("delayed_response" in codes or timely_response_no):
            reasons.append("unauthorized_transaction_plus_unresolved_or_delayed_response")
        return reasons

    def _same_family(self, left: str | None, right: str | None, families: dict[str, tuple[str, ...]]) -> bool:
        left_family = self._family(left, families)
        right_family = self._family(right, families)
        return left_family is not None and left_family == right_family

    def _family(self, value: str | None, families: dict[str, tuple[str, ...]]) -> str | None:
        text = self._normalized(value)
        if not text:
            return None
        for family, terms in families.items():
            if any(term in text for term in terms):
                return family
        return None

    def _normalized(self, value: str | None) -> str:
        return " ".join((value or "").lower().replace("/", " ").replace(",", " ").split())
