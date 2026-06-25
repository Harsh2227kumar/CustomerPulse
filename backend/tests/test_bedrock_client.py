import asyncio
import json
import unittest

import httpx

from app.ai.bedrock.client import AI_ENRICHMENT_SCHEMA, BEDROCK_TOOL_NAME, BedrockClient
from app.core.config import Settings
from app.core.constants import Sentiment


def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:pass@localhost/customerpulse",
        bedrock_api_key="example-key",
        bedrock_base_url="https://bedrock.local",
        auth_principals_json="{}",
    )


class BedrockStructuredOutputTests(unittest.TestCase):
    def test_analyze_complaint_forces_bedrock_tool_schema(self) -> None:
        captured_payloads = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content.decode("utf-8"))
            captured_payloads.append(payload)
            return httpx.Response(
                200,
                json={
                    "output": {
                        "message": {
                            "content": [
                                {
                                    "toolUse": {
                                        "name": BEDROCK_TOOL_NAME,
                                        "input": {
                                            "sentiment": "Negative",
                                            "category": "Card issue",
                                            "urgency_score": 72,
                                            "churn_risk": "Medium",
                                            "draft_response": "We will investigate the disputed account activity.",
                                            "next_action": "Review account activity and contact the customer.",
                                            "similar_cases": [],
                                            "confidence_scores": {
                                                "sentiment": 90,
                                                "category": 82,
                                                "urgency": 75,
                                                "churn_risk": 70,
                                                "draft_response": 80,
                                            },
                                            "ai_confidence": 0.84,
                                            "ai_reasoning": "Forced tool output for test.",
                                        },
                                    }
                                }
                            ]
                        }
                    }
                },
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        bedrock = BedrockClient(settings(), client=http_client)

        payload_text = asyncio.run(
            bedrock.analyze_complaint(
                complaint_id="CP-1",
                narrative="I have an unauthorized charge and need help.",
                channel="web",
                local_sentiment=Sentiment.NEGATIVE,
                local_category="Card issue",
                local_urgency=70,
                similar_cases=[],
            )
        )

        payload = json.loads(payload_text)
        self.assertEqual(payload["category"], "Card issue")
        request_payload = captured_payloads[0]
        tool_config = request_payload["toolConfig"]
        tool_spec = tool_config["tools"][0]["toolSpec"]
        self.assertEqual(tool_spec["name"], BEDROCK_TOOL_NAME)
        self.assertEqual(tool_spec["inputSchema"]["json"], AI_ENRICHMENT_SCHEMA)
        self.assertEqual(tool_config["toolChoice"], {"tool": {"name": BEDROCK_TOOL_NAME}})


    def test_analyze_complaint_rejects_text_fallback_when_tool_is_missing(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "output": {
                        "message": {
                            "content": [{"text": '{"category":"Card issue"}'}]
                        }
                    }
                },
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        bedrock = BedrockClient(settings(), client=http_client)

        with self.assertLogs("app.ai.bedrock.client", level="ERROR"):
            with self.assertRaisesRegex(ValueError, "structured tool output"):
                asyncio.run(
                    bedrock.analyze_complaint(
                        complaint_id="CP-2",
                        narrative="I have an unauthorized charge and need help.",
                        channel="web",
                        local_sentiment=Sentiment.NEGATIVE,
                        local_category="Card issue",
                        local_urgency=70,
                        similar_cases=[],
                    )
                )

    def test_close_only_closes_owned_http_client(self) -> None:
        injected = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
        external_bedrock = BedrockClient(settings(), client=injected)
        external_bedrock.close()
        self.assertFalse(injected.is_closed)
        injected.close()

        owned_bedrock = BedrockClient(settings())
        owned_client = owned_bedrock.client
        owned_bedrock.close()
        self.assertTrue(owned_client.is_closed)


if __name__ == "__main__":
    unittest.main()
