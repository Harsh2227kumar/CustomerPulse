import unittest

from app.ai.bedrock.parser import parse_json_object
from app.ai.ml_models.classifier import classify_category
from app.ai.ml_models.sentiment import predict_sentiment
from app.ai.ml_models.urgency import estimate_urgency
from app.ai.preprocessing.cleaner import clean_complaint_text
from app.ai.preprocessing.extractor import extract_signals
from app.ai.preprocessing.summarizer import compress_for_prompt
from app.ai.validators.confidence_validator import enforce_minimum_confidence
from app.ai.validators.hallucination_guard import guard_against_empty_operational_output
from app.ai.validators.schema_validator import validate_ai_enrichment
from app.core.constants import Sentiment


class LocalAIProcessingTests(unittest.TestCase):
    def test_cleans_contact_data_and_scores_urgent_negative_complaint(self) -> None:
        cleaned = clean_complaint_text(
            "Unauthorized fee unresolved; contact me at person@example.com or 555-123-4567. "
            "See https://example.com/case."
        )
        signals = extract_signals(cleaned.cleaned)
        sentiment, _ = predict_sentiment(cleaned.cleaned)
        category, _ = classify_category(cleaned.cleaned)
        urgency, _ = estimate_urgency(cleaned.cleaned, signals)

        self.assertIn("[EMAIL]", cleaned.cleaned)
        self.assertIn("[PHONE]", cleaned.cleaned)
        self.assertIn("[URL]", cleaned.cleaned)
        self.assertEqual(sentiment, Sentiment.NEGATIVE)
        self.assertEqual(category, "Billing or fees")
        self.assertGreaterEqual(urgency, 70)

    def test_truncates_long_narratives_while_retaining_beginning_and_end(self) -> None:
        narrative = " ".join(f"word-{index}" for index in range(20))

        shortened = compress_for_prompt(narrative, max_words=10)

        self.assertIn("word-0", shortened)
        self.assertIn("[...middle omitted for token control...]", shortened)
        self.assertIn("word-19", shortened)

    def test_parses_and_validates_bedrock_enrichment_contract(self) -> None:
        raw = """
        Result:
        {
          "sentiment": "Negative",
          "category": "Billing or fees",
          "urgency_score": 82,
          "churn_risk": "High",
          "draft_response": "We reviewed your disputed fee and will provide a written resolution promptly.",
          "next_action": "Review transaction records immediately",
          "similar_cases": [],
          "confidence_scores": {
            "sentiment": 91,
            "category": 87,
            "urgency": 89,
            "churn_risk": 84,
            "draft_response": 81
          },
          "ai_confidence": 0.86,
          "ai_reasoning": "The complaint reports an unresolved unauthorized fee."
        }
        """

        enrichment = validate_ai_enrichment(parse_json_object(raw))

        self.assertIs(enforce_minimum_confidence(enrichment), enrichment)
        self.assertIs(guard_against_empty_operational_output(enrichment), enrichment)


if __name__ == "__main__":
    unittest.main()
