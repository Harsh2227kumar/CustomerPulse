import json

from app.core.constants import (
    ChurnRisk,
    MAX_PROMPT_EVIDENCE_TEXT_CHARS,
    MAX_PROMPT_NARRATIVE_CHARS,
    Sentiment,
)
from app.schemas.ai_response import SimilarCaseEvidence


SYSTEM_PROMPT = """You are CustomerPulse AI, an enterprise BFSI complaint intelligence engine.
Return only valid JSON that matches the requested schema.
Use the customer's complaint text and provided local signals.
Never invent facts that are not supported by the complaint.
If evidence is weak, lower confidence instead of guessing.
Historical cases may guide a proposed action, but cannot establish what happened
or what resolution applies to the present complaint.
"""


def build_user_prompt(
    complaint_id: str,
    narrative: str,
    channel: str | None,
    local_sentiment: Sentiment,
    local_category: str,
    local_urgency: int,
    similar_cases: list[SimilarCaseEvidence],
) -> str:
    churn_values = ", ".join(risk.value for risk in ChurnRisk)
    sentiment_values = ", ".join(sentiment.value for sentiment in Sentiment)
    evidence_payload = [
        {
            **case.model_dump(mode="json"),
            "next_action": _bounded(case.next_action),
            "approved_response": _bounded(case.approved_response),
        }
        for case in similar_cases
    ]
    evidence = json.dumps(
        evidence_payload,
        separators=(",", ":"),
    )
    complaint_payload = json.dumps(
        {
            "complaint_id": complaint_id,
            "channel": channel or "unknown",
            "narrative": narrative[:MAX_PROMPT_NARRATIVE_CHARS],
        },
        separators=(",", ":"),
    )
    return f"""
Analyze this real customer complaint and return JSON matching this exact shape:
{{
  "sentiment": "{sentiment_values}",
  "category": "short category string",
  "urgency_score": 0,
  "churn_risk": "{churn_values}",
  "draft_response": "professional customer-facing response",
  "next_action": "specific operational next step",
  "similar_cases": [],
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
- similar_cases must contain only the supplied historical evidence records; do not invent cases
- Similar historical actions are context only and do not prove resolution of this complaint
- Never repeat personal data or unsupported facts from historical evidence in the draft response

Local sentiment hint: {local_sentiment.value}
Local category hint: {local_category}
Local urgency hint: {local_urgency}
Retrieved similar completed cases (bounded evidence): {evidence}
Current complaint JSON (authoritative input): {complaint_payload}
""".strip()


def _bounded(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:MAX_PROMPT_EVIDENCE_TEXT_CHARS]
