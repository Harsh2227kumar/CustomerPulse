from app.core.constants import Sentiment


NEGATIVE_TERMS = {
    "angry",
    "awful",
    "bad",
    "closed",
    "denied",
    "disappointed",
    "error",
    "failed",
    "fraud",
    "ignored",
    "incorrect",
    "late",
    "lost",
    "missing",
    "never",
    "overcharged",
    "problem",
    "refused",
    "scam",
    "terrible",
    "unauthorized",
    "unfair",
    "unresolved",
    "wrong",
}
POSITIVE_TERMS = {"resolved", "helpful", "satisfied", "thank", "thanks", "corrected"}


def predict_sentiment(text: str) -> tuple[Sentiment, float]:
    words = {word.strip(".,!?;:()[]{}\"'").lower() for word in text.split()}
    negative_hits = len(words & NEGATIVE_TERMS)
    positive_hits = len(words & POSITIVE_TERMS)
    if negative_hits > positive_hits:
        confidence = min(0.95, 0.55 + negative_hits * 0.08)
        return Sentiment.NEGATIVE, confidence
    if positive_hits > negative_hits:
        confidence = min(0.9, 0.55 + positive_hits * 0.08)
        return Sentiment.POSITIVE, confidence
    return Sentiment.NEUTRAL, 0.5
