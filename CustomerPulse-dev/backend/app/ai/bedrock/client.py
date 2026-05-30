import asyncio
import logging
from typing import Any

import httpx

from app.ai.bedrock.prompts import SYSTEM_PROMPT, build_user_prompt
from app.core.config import Settings
from app.core.constants import Sentiment

logger = logging.getLogger(__name__)


AI_ENRICHMENT_SCHEMA: dict[str, Any] = {
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
}


class BedrockClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(timeout=settings.ai_timeout_seconds, trust_env=False)

    @property
    def converse_url(self) -> str:
        base_url = self.settings.bedrock_base_url or (
            f"https://bedrock-runtime.{self.settings.bedrock_region}.amazonaws.com"
        )
        return f"{base_url.rstrip('/')}/model/{self.settings.bedrock_model}/converse"

    def _create_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.settings.bedrock_api_key is not None
        response = self.client.post(
            self.converse_url,
            headers={
                "Authorization": f"Bearer {self.settings.bedrock_api_key}",
                "content-type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def check_connection(self) -> None:
        await asyncio.to_thread(
            self._create_message,
            {
                "system": [{"text": "Reply with ok."}],
                "messages": [{"role": "user", "content": [{"text": "Connection check."}]}],
                "inferenceConfig": {"maxTokens": 16},
            },
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
            self._create_message,
            {
                "system": [{"text": SYSTEM_PROMPT}],
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"temperature": 0, "maxTokens": 1200},
            },
        )

        text_parts = [
            content["text"]
            for content in response.get("output", {}).get("message", {}).get("content", [])
            if content.get("text")
        ]
        if text_parts:
            return "".join(text_parts)

        logger.error("Bedrock returned no text content: %s", response)
        raise ValueError("Bedrock returned no text content")
