from app.schemas.ai_response import AIEnrichment


def guard_against_empty_operational_output(enrichment: AIEnrichment) -> AIEnrichment:
    if len(enrichment.next_action.split()) < 3:
        raise ValueError("next_action is too vague")
    if len(enrichment.draft_response.split()) < 8:
        raise ValueError("draft_response is too short for customer response use")
    return enrichment
