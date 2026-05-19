import asyncio
import logging
from typing import Any

import httpx
from openai import OpenAI

from app.ai.openai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.core.config import Settings
from app.core.constants import Sentiment

logger = logging.getLogger(__name__)


AI_ENRICHMENT_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "customerpulse_ai_enrichment",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sentiment": {"type": "string", "enum": ["Positive", "Neutral", "Negative"]},
            "category": {"type": "string"},
            "urgency_score": {"type": "integer"},
            "churn_risk": {"type": "string", "enum": ["Low", "Medium", "High"]},
            "draft_response": {"type": "string"},
            "next_action": {"type": "string"},
            "similar_cases": {"type": "array", "items": {"type": "string"}},
            "confidence_scores": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "sentiment": {"type": "integer"},
                    "category": {"type": "integer"},
                    "urgency": {"type": "integer"},
                    "churn_risk": {"type": "integer"},
                    "draft_response": {"type": "integer"},
                },
                "required": [
                    "sentiment",
                    "category",
                    "urgency",
                    "churn_risk",
                    "draft_response",
                ],
            },
            "ai_confidence": {"type": "number"},
            "ai_reasoning": {"type": "string"},
        },
        "required": [
            "sentiment",
            "category",
            "urgency_score",
            "churn_risk",
            "draft_response",
            "next_action",
            "similar_cases",
            "confidence_scores",
            "ai_confidence",
            "ai_reasoning",
        ],
    },
}


class OpenAIClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        client_kwargs: dict[str, Any] = {
            "api_key": settings.openai_api_key,
            "timeout": settings.ai_timeout_seconds,
            "max_retries": 0,
        }
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        client_kwargs["http_client"] = httpx.Client(trust_env=False)
        self.client = OpenAI(**client_kwargs)

    async def check_connection(self) -> None:
        await asyncio.to_thread(
            self.client.responses.create,
            model=self.settings.openai_model,
            input="Reply with ok.",
            max_output_tokens=16,
        )

    async def analyze_complaint(
        self,
        complaint_id: str,
        narrative: str,
        channel: str | None,
        local_sentiment: Sentiment,
        local_category: str,
        local_urgency: int,
    ) -> str:
        prompt = build_user_prompt(
            complaint_id=complaint_id,
            narrative=narrative,
            channel=channel,
            local_sentiment=local_sentiment,
            local_category=local_category,
            local_urgency=local_urgency,
        )
        response = await asyncio.to_thread(
            self.client.responses.create,
            model=self.settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            text={"format": AI_ENRICHMENT_RESPONSE_FORMAT},
            temperature=0,
            max_output_tokens=1200,
        )
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        try:
            return response.output[0].content[0].text
        except Exception:
            logger.error("OpenAI returned no text content: %s", response)
            raise ValueError("OpenAI returned no text content")
