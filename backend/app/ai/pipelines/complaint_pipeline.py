from dataclasses import dataclass

from app.ai.ml_models.classifier import classify_category
from app.ai.ml_models.confidence import combine_confidence
from app.ai.ml_models.sentiment import predict_sentiment
from app.ai.ml_models.urgency import estimate_urgency
from app.ai.bedrock.client import BedrockClient
from app.ai.bedrock.parser import parse_json_object
from app.ai.bedrock.retry_handler import with_retries
from app.ai.preprocessing.cleaner import clean_complaint_text
from app.ai.preprocessing.extractor import extract_signals
from app.ai.preprocessing.summarizer import compress_for_prompt
from app.ai.validators.schema_validator import validate_ai_enrichment
from app.core.config import Settings
from app.core.constants import Sentiment
from app.schemas.ai_response import AIEnrichment, SimilarCaseEvidence
from app.schemas.complaint import ComplaintProcessRequest


@dataclass(frozen=True)
class LocalSignals:
    cleaned_narrative: str
    prompt_narrative: str
    sentiment: Sentiment
    sentiment_confidence: float
    category: str
    category_confidence: float
    urgency_score: int
    urgency_confidence: float
    combined_confidence: float


class BedrockUnavailableError(RuntimeError):
    pass


class InvalidAIOutputError(ValueError):
    pass


class ComplaintAIPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bedrock = BedrockClient(settings)

    def run_local_layer(self, complaint: ComplaintProcessRequest) -> LocalSignals:
        cleaned = clean_complaint_text(complaint.narrative)
        prompt_narrative = compress_for_prompt(cleaned.cleaned)
        signals = extract_signals(cleaned.cleaned)
        sentiment_result = predict_sentiment(cleaned.cleaned)
        category_result = classify_category(cleaned.cleaned, complaint.product, complaint.issue)
        urgency_result = estimate_urgency(cleaned.cleaned, signals)
        sentiment, sentiment_confidence = sentiment_result[:2]
        category, category_confidence = category_result[:2]
        urgency_score, urgency_confidence = urgency_result[:2]
        combined_result = combine_confidence(
            sentiment_confidence,
            category_confidence,
            urgency_confidence,
        )
        combined_confidence = (
            combined_result[0] if isinstance(combined_result, tuple) else combined_result
        )
        return LocalSignals(
            cleaned_narrative=cleaned.cleaned,
            prompt_narrative=prompt_narrative,
            sentiment=sentiment,
            sentiment_confidence=sentiment_confidence,
            category=category,
            category_confidence=category_confidence,
            urgency_score=urgency_score,
            urgency_confidence=urgency_confidence,
            combined_confidence=combined_confidence,
        )

    async def process(
        self,
        complaint: ComplaintProcessRequest,
        *,
        local: LocalSignals | None = None,
        similar_cases: list[SimilarCaseEvidence] | None = None,
    ) -> tuple[AIEnrichment, LocalSignals]:
        local = local or self.run_local_layer(complaint)
        evidence = similar_cases or []

        async def call_bedrock() -> str:
            return await self.bedrock.analyze_complaint(
                complaint_id=complaint.complaint_id,
                narrative=local.prompt_narrative,
                channel=complaint.channel,
                local_sentiment=local.sentiment,
                local_category=local.category,
                local_urgency=local.urgency_score,
                similar_cases=evidence,
            )

        try:
            raw_response = await with_retries(call_bedrock, self.settings.ai_max_retries)
        except Exception as exc:
            raise BedrockUnavailableError("Bedrock processing failed after retries.") from exc
        try:
            parsed = parse_json_object(raw_response)
            enrichment = validate_ai_enrichment(parsed)
        except Exception as exc:
            raise InvalidAIOutputError("Bedrock returned an invalid structured response.") from exc
        enrichment = enrichment.model_copy(update={"similar_cases": evidence})
        return enrichment, local
