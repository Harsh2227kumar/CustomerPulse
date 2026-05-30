from app.schemas.ai_response import AIEnrichment


MIN_AI_CONFIDENCE = 0.35


def enforce_minimum_confidence(enrichment: AIEnrichment) -> AIEnrichment:
    if enrichment.ai_confidence < MIN_AI_CONFIDENCE:
        raise ValueError("AI confidence below minimum threshold")
    return enrichment
