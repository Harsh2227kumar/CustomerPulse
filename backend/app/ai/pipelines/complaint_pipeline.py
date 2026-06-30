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
from app.intelligence.evidence_service import EvidenceService
from app.intelligence.key_issue_service import KeyIssueService
from app.intelligence.risk_signal_service import RiskSignalService
from app.intelligence.resolution_recommendation_service import ResolutionRecommendationService
from app.intelligence.resolution_validation_service import ResolutionValidationService
from app.schemas.ai_response import (
    AIEnrichment,
    DecisionMetadata,
    DecisionSource,
    EvidenceSnippet,
    SimilarCaseEvidence,
)
from app.schemas.complaint import ComplaintProcessRequest


@dataclass(frozen=True)
class LocalSignals:
    cleaned_narrative: str
    prompt_narrative: str
    sentiment: Sentiment
    sentiment_confidence: float
    category: str
    category_confidence: float
    category_reason_codes: list[str]
    category_conflict: bool
    urgency_score: int
    urgency_confidence: float
    urgency_reason_codes: list[str]
    urgency_level: str
    urgency_reason: str
    sentiment_reason_codes: list[str]
    combined_confidence: float


class BedrockUnavailableError(RuntimeError):
    pass


class InvalidAIOutputError(ValueError):
    pass


class ComplaintAIPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bedrock = BedrockClient(settings)
        self.evidence_service = EvidenceService()
        self.key_issue_service = KeyIssueService(self.evidence_service)
        self.risk_signal_service = RiskSignalService(self.evidence_service)
        self.resolution_validation_service = ResolutionValidationService(self.evidence_service)
        self.resolution_recommendation_service = ResolutionRecommendationService()

    def close(self) -> None:
        self.bedrock.close()


    def run_local_layer(self, complaint: ComplaintProcessRequest) -> LocalSignals:
        cleaned = clean_complaint_text(complaint.narrative)
        prompt_narrative = compress_for_prompt(cleaned.cleaned)
        signals = extract_signals(cleaned.cleaned)
        sentiment_result = predict_sentiment(cleaned.cleaned)
        category_result = classify_category(cleaned.cleaned, complaint.product, complaint.issue)
        urgency_result = estimate_urgency(cleaned.cleaned, signals)
        sentiment, sentiment_confidence, sentiment_reason_codes = sentiment_result
        category, category_confidence, category_reason_codes, category_conflict = category_result
        (
            urgency_score,
            urgency_confidence,
            urgency_reason_codes,
            urgency_level,
            urgency_reason,
        ) = urgency_result
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
            category_reason_codes=category_reason_codes,
            category_conflict=category_conflict,
            urgency_score=urgency_score,
            urgency_confidence=urgency_confidence,
            urgency_reason_codes=urgency_reason_codes,
            urgency_level=urgency_level,
            urgency_reason=urgency_reason,
            sentiment_reason_codes=sentiment_reason_codes,
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
        enrichment = self.enrich_with_local_intelligence(
            complaint,
            enrichment,
            local=local,
            similar_cases=evidence,
        )
        return enrichment, local

    def enrich_with_local_intelligence(
        self,
        complaint: ComplaintProcessRequest,
        enrichment: AIEnrichment,
        *,
        local: LocalSignals,
        similar_cases: list[SimilarCaseEvidence] | None = None,
    ) -> AIEnrichment:
        evidence = self.evidence_service.snippets_for_text(local.cleaned_narrative, max_snippets=6)
        key_issue = self.key_issue_service.extract(
            local.cleaned_narrative,
            product=complaint.product,
            issue=complaint.issue,
            category=enrichment.category,
        )
        risk_signals = self.risk_signal_service.score(
            local.cleaned_narrative,
            urgency_score=enrichment.urgency_score,
            ai_confidence=enrichment.ai_confidence,
        )
        resolution_validation = self.resolution_validation_service.validate(
            local.cleaned_narrative,
            current_category=enrichment.category,
            current_product=complaint.product,
            current_issue=complaint.issue,
            current_reason_codes=risk_signals.reason_codes,
            similar_cases=similar_cases or [],
            risk_reason_codes=risk_signals.reason_codes,
        )
        resolution_recommendation = self.resolution_recommendation_service.recommend(
            resolution_validation
        )
        reason_codes = sorted(
            set(enrichment.reason_codes)
            | set(local.sentiment_reason_codes)
            | set(local.category_reason_codes)
            | set(local.urgency_reason_codes)
            | set(risk_signals.reason_codes)
            | set(resolution_validation.reason_codes)
            | set(resolution_recommendation.reason_codes)
        )
        evidence_snippets = self._merge_evidence(
            enrichment.evidence_snippets,
            evidence,
            key_issue.evidence_snippets,
            risk_signals.evidence_snippets,
            resolution_validation.evidence_snippets,
        )
        source = DecisionSource(provider="customerpulse", model="member1-intelligence-v1", mode="hybrid")
        metadata = [
            DecisionMetadata(
                decision_type="classification",
                confidence=local.category_confidence,
                reason_codes=local.category_reason_codes,
                evidence_snippets=evidence_snippets[:3],
                source=DecisionSource(provider="customerpulse", model="classifier-mapping-v2"),
                notes="Category mapping uses CFPB product/issue overrides from dataset mismatch profiling.",
            ),
            DecisionMetadata(
                decision_type="urgency",
                confidence=local.urgency_confidence,
                reason_codes=local.urgency_reason_codes,
                evidence_snippets=evidence_snippets[:3],
                source=DecisionSource(provider="customerpulse", model="deterministic-urgency-v1"),
                notes=local.urgency_reason,
            ),
            DecisionMetadata(
                decision_type="risk_signal",
                confidence=risk_signals.confidence,
                reason_codes=risk_signals.reason_codes,
                evidence_snippets=risk_signals.evidence_snippets,
                source=risk_signals.source,
                notes=risk_signals.recommended_action,
            ),
            DecisionMetadata(
                decision_type="similar_case_retrieval",
                confidence=1.0 if similar_cases else 0.5,
                reason_codes=["retrieval_threshold_0_80"] if similar_cases else ["no_candidate_retrieved"],
                evidence_snippets=[],
                source=DecisionSource(
                    provider="customerpulse",
                    model="pgvector-similarity-retrieval",
                    version="colab-retrieval-threshold-0.80",
                ),
                notes="Similarity finds candidates; validation decides reuse.",
            ),
            DecisionMetadata(
                decision_type="resolution_validation",
                confidence=resolution_validation.confidence,
                reason_codes=resolution_validation.reason_codes,
                evidence_snippets=resolution_validation.evidence_snippets,
                source=resolution_validation.source,
                notes=resolution_validation.notes,
            ),
            DecisionMetadata(
                decision_type="resolution_recommendation",
                confidence=resolution_recommendation.confidence,
                reason_codes=resolution_recommendation.reason_codes,
                evidence_snippets=resolution_recommendation.evidence_snippets,
                source=resolution_recommendation.source,
                notes=resolution_recommendation.recommendation,
            ),
        ]
        return enrichment.model_copy(
            update={
                "reason_codes": reason_codes,
                "evidence_snippets": evidence_snippets,
                "key_issue": key_issue,
                "risk_signals": risk_signals,
                "resolution_validation": resolution_validation,
                "resolution_recommendation": resolution_recommendation,
                "decision_metadata": metadata,
                "source_metadata": source,
            }
        )

    def _merge_evidence(
        self,
        *groups: list[EvidenceSnippet],
        limit: int = 8,
    ) -> list[EvidenceSnippet]:
        merged: list[EvidenceSnippet] = []
        seen: set[tuple[str | None, str]] = set()
        for group in groups:
            for snippet in group:
                key = (snippet.reason_code, snippet.text.lower())
                if key in seen:
                    continue
                seen.add(key)
                merged.append(snippet)
                if len(merged) >= limit:
                    return merged
        return merged
