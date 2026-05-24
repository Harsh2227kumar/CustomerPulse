from app.schemas.ai_response import AIEnrichment


def validate_ai_enrichment(payload: dict) -> AIEnrichment:
    return AIEnrichment.model_validate(payload)
