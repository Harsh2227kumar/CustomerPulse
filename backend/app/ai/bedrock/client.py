import asyncio
import json
import logging
from typing import Any

import httpx

from app.ai.bedrock.prompts import SYSTEM_PROMPT, build_user_prompt
from app.core.config import Settings
from app.core.constants import Sentiment
from app.schemas.ai_response import SimilarCaseEvidence

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
        "similar_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "complaint_id": {"type": "string"},
                    "similarity_score": {"type": "number"},
                    "category": {"type": ["string", "null"]},
                    "next_action": {"type": ["string", "null"]},
                    "approved_response": {"type": ["string", "null"]},
                    "ai_status": {"type": "string"},
                },
            },
        },
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


BEDROCK_TOOL_NAME = "emit_ai_enrichment"


class BedrockClient:
    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
    ):
        self.settings = settings
        self.client = client or httpx.Client(timeout=settings.ai_timeout_seconds, trust_env=False)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> "BedrockClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

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

    def _structured_tool_config(self) -> dict[str, Any]:
        return {
            "tools": [
                {
                    "toolSpec": {
                        "name": BEDROCK_TOOL_NAME,
                        "description": (
                            "Emit exactly one CustomerPulse AI enrichment JSON object "
                            "that conforms to the supplied schema."
                        ),
                        "inputSchema": {"json": AI_ENRICHMENT_SCHEMA},
                    }
                }
            ],
            "toolChoice": {"tool": {"name": BEDROCK_TOOL_NAME}},
        }

    def _extract_response_payload(self, response: dict[str, Any]) -> str:
        content_blocks = response.get("output", {}).get("message", {}).get("content", [])
        for content in content_blocks:
            tool_use = content.get("toolUse")
            if isinstance(tool_use, dict) and tool_use.get("name") == BEDROCK_TOOL_NAME:
                tool_input = tool_use.get("input")
                if isinstance(tool_input, dict):
                    return json.dumps(tool_input)

        logger.error("Bedrock returned no structured tool output: %s", response)
        raise ValueError("Bedrock returned no structured tool output")

    async def analyze_complaint(
        self,
        complaint_id: str,
        narrative: str,
        channel: str | None,
        local_sentiment: Sentiment,
        local_category: str,
        local_urgency: int,
        similar_cases: list[SimilarCaseEvidence],
    ) -> str:
        prompt = build_user_prompt(
            complaint_id=complaint_id,
            narrative=narrative,
            channel=channel,
            local_sentiment=local_sentiment,
            local_category=local_category,
            local_urgency=local_urgency,
            similar_cases=similar_cases,
        )
        response = await asyncio.to_thread(
            self._create_message,
            {
                "system": [{"text": SYSTEM_PROMPT}],
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"temperature": 0, "maxTokens": 1200},
                "toolConfig": self._structured_tool_config(),
            },
        )
        return self._extract_response_payload(response)
