import logging

from anthropic import AsyncAnthropic

from app.ai.claude.prompts import SYSTEM_PROMPT, build_user_prompt
from app.core.config import Settings
from app.core.constants import Sentiment

logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

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
        response = await self.client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=1200,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.settings.ai_timeout_seconds,
        )
        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        if not text_blocks:
            raise ValueError("Claude returned no text content")
        return "\n".join(text_blocks)
