from app.schemas.ai_response import (
    DecisionSource,
    ResolutionRecommendationResult,
    ResolutionValidationResult,
)


class ResolutionRecommendationService:
    def recommend(
        self,
        validation: ResolutionValidationResult,
    ) -> ResolutionRecommendationResult:
        if validation.status == "safe_reuse":
            recommendation_type = "reuse_candidate_response"
            recommendation = "Reuse candidate response with agent visibility."
            confidence = min(0.94, max(0.80, validation.confidence))
            reason_codes = ["safe_reuse_supported", *validation.reason_codes]
        elif validation.status == "escalate":
            recommendation_type = "do_not_reuse_escalate"
            recommendation = "Do not reuse response automatically. Escalate for specialist review."
            confidence = max(0.82, validation.confidence)
            reason_codes = ["reuse_blocked_by_risk", *validation.reason_codes]
        elif validation.status == "manual_review":
            recommendation_type = "manual_review_before_reuse"
            recommendation = "Use similar case only as context after manual validation."
            confidence = max(0.70, validation.confidence)
            reason_codes = ["manual_validation_required", *validation.reason_codes]
        else:
            recommendation_type = "no_reuse"
            recommendation = "Do not reuse candidate response. Draft from current complaint evidence."
            confidence = max(0.70, validation.confidence)
            reason_codes = ["candidate_reuse_rejected", *validation.reason_codes]

        return ResolutionRecommendationResult(
            recommendation_type=recommendation_type,
            recommendation=recommendation,
            reason_codes=sorted(set(reason_codes)),
            evidence_snippets=validation.evidence_snippets,
            confidence=confidence,
            source=DecisionSource(
                provider="customerpulse",
                model="deterministic-resolution-recommendation-v1",
                version="colab-hybrid-validation-2026-06-23",
            ),
        )

