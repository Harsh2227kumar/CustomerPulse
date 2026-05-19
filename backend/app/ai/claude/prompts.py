from app.core.constants import ChurnRisk, Sentiment


SYSTEM_PROMPT = """You are CustomerPulse AI, an enterprise BFSI complaint intelligence engine.
Return only valid JSON. Do not include markdown, commentary, or extra keys.
Use the customer's complaint text and provided local signals.
Never invent facts that are not supported by the complaint.
If evidence is weak, lower confidence instead of guessing.
"""


def build_user_prompt(
    complaint_id: str,
    narrative: str,
    channel: str | None,
    local_sentiment: Sentiment,
    local_category: str,
    local_urgency: int,
) -> str:
    churn_values = ", ".join(risk.value for risk in ChurnRisk)
    sentiment_values = ", ".join(sentiment.value for sentiment in Sentiment)
    return f"""
Analyze this real customer complaint and return JSON matching this exact shape:
{{
  "sentiment": "{sentiment_values}",
  "category": "short category string",
  "urgency_score": 0,
  "churn_risk": "{churn_values}",
  "draft_response": "professional customer-facing response",
  "next_action": "specific operational next step",
  "confidence_scores": {{
    "sentiment": 0,
    "category": 0,
    "urgency": 0,
    "churn_risk": 0,
    "draft_response": 0
  }},
  "ai_confidence": 0.0,
  "ai_reasoning": "brief evidence-based reasoning"
}}

Rules:
- sentiment must be one of: {sentiment_values}
- churn_risk must be one of: {churn_values}
- urgency_score and confidence values must be 0 to 100
- ai_confidence must be 0.0 to 1.0
- Use the local signals as hints, not final truth

Complaint ID: {complaint_id}
Channel: {channel or "unknown"}
Local sentiment hint: {local_sentiment.value}
Local category hint: {local_category}
Local urgency hint: {local_urgency}
Complaint narrative:
{narrative}
""".strip()
