from app.ai.preprocessing.extractor import ComplaintSignals


def estimate_urgency(text: str, signals: ComplaintSignals) -> tuple[int, float]:
    score = 30
    lowered = text.lower()
    if signals.has_financial_harm_terms:
        score += 20
    if signals.has_legal_terms:
        score += 20
    if signals.has_escalation_terms:
        score += 10
    if signals.has_waiting_terms:
        score += 10
    if any(term in lowered for term in ("foreclosure", "identity theft", "bankruptcy")):
        score += 15
    score = max(0, min(100, score))
    confidence = 0.55 if score < 60 else 0.7
    return score, confidence
