from app.core.constants import (
    ChurnRisk,
    HIGH_URGENCY_REVIEW_THRESHOLD,
    MIN_AI_CONFIDENCE,
    MIN_DRAFT_RESPONSE_WORDS,
    MIN_NEXT_ACTION_WORDS,
    ReviewReason,
)
from app.schemas.ai_response import AIEnrichment


VAGUE_ACTIONS = {
    "review complaint",
    "investigate issue",
    "contact customer",
    "follow up",
    "check account",
}


def review_reason_for(enrichment: AIEnrichment) -> ReviewReason | None:
    if enrichment.ai_confidence < MIN_AI_CONFIDENCE:
        return ReviewReason.LOW_CONFIDENCE
    if len(enrichment.draft_response.split()) < MIN_DRAFT_RESPONSE_WORDS:
        return ReviewReason.WEAK_DRAFT_RESPONSE
    next_action = enrichment.next_action.strip().lower().rstrip(".")
    if (
        len(next_action.split()) < MIN_NEXT_ACTION_WORDS
        or next_action in VAGUE_ACTIONS
    ):
        return ReviewReason.VAGUE_NEXT_ACTION
    if (
        enrichment.churn_risk == ChurnRisk.HIGH
        and enrichment.urgency_score > HIGH_URGENCY_REVIEW_THRESHOLD
    ):
        return ReviewReason.HIGH_RISK_HIGH_URGENCY
    return None
