import unittest

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.ai.bedrock.prompts import build_user_prompt
from app.ai.pipelines.complaint_pipeline import ComplaintAIPipeline
from app.ai.validators.review_router import review_reason_for
from app.core.config import Settings
from app.core.constants import ChurnRisk, ReviewReason, Role, Sentiment
from app.core.security import Principal, get_current_principal, require_roles
from app.schemas.ai_response import AIEnrichment, ConfidenceScores, SimilarCaseEvidence
from app.schemas.complaint import ComplaintFilters
from app.schemas.complaint import ComplaintProcessRequest
from app.services.embedding_service import EmbeddingService, InvalidEmbeddingError
from app.services.retrieval_service import SimilarComplaintService
from pydantic import ValidationError


def enrichment(**overrides) -> AIEnrichment:
    values = {
        "sentiment": Sentiment.NEGATIVE,
        "category": "Billing dispute",
        "urgency_score": 55,
        "churn_risk": ChurnRisk.MEDIUM,
        "draft_response": "We received your complaint and will investigate the disputed charge promptly.",
        "next_action": "Review the account transaction history.",
        "confidence_scores": ConfidenceScores(sentiment=80, category=85, urgency=70),
        "ai_confidence": 0.8,
    }
    values.update(overrides)
    return AIEnrichment(**values)


def settings(auth_json: str = "{}") -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:pass@localhost/customerpulse",
        bedrock_api_key="example-key",
        auth_principals_json=auth_json,
    )


class ReviewRoutingTests(unittest.TestCase):
    def test_safe_enrichment_has_no_review_reason(self) -> None:
        self.assertIsNone(review_reason_for(enrichment()))

    def test_low_confidence_routes_to_review(self) -> None:
        self.assertEqual(
            review_reason_for(enrichment(ai_confidence=0.2)),
            ReviewReason.LOW_CONFIDENCE,
        )

    def test_weak_output_routes_to_review(self) -> None:
        self.assertEqual(
            review_reason_for(enrichment(draft_response="Too short.")),
            ReviewReason.WEAK_DRAFT_RESPONSE,
        )
        self.assertEqual(
            review_reason_for(enrichment(next_action="Investigate now")),
            ReviewReason.VAGUE_NEXT_ACTION,
        )
        self.assertEqual(
            review_reason_for(enrichment(next_action="Contact customer.")),
            ReviewReason.VAGUE_NEXT_ACTION,
        )

    def test_high_risk_high_urgency_requires_review(self) -> None:
        self.assertEqual(
            review_reason_for(
                enrichment(churn_risk=ChurnRisk.HIGH, urgency_score=80)
            ),
            ReviewReason.HIGH_RISK_HIGH_URGENCY,
        )

    def test_pipeline_accepts_enriched_ml_result_contracts(self) -> None:
        local = ComplaintAIPipeline(settings()).run_local_layer(
            ComplaintProcessRequest(
                complaint_id="ml-contract",
                narrative="I was charged an unauthorized fee and need urgent help.",
                product="Bank account or service",
                issue="Fees",
            )
        )

        self.assertIsInstance(local.sentiment, Sentiment)
        self.assertGreaterEqual(local.combined_confidence, 0)
        self.assertLessEqual(local.combined_confidence, 1)


class RAGContractTests(unittest.TestCase):
    def test_grounded_prompt_includes_only_structured_supplied_evidence(self) -> None:
        evidence = [
            SimilarCaseEvidence(
                complaint_id="history-1",
                similarity_score=0.75,
                category="Fees",
                next_action="Review fees.",
                approved_response=None,
                ai_status="completed",
            )
        ]
        prompt = build_user_prompt(
            complaint_id="active-1",
            narrative="I was charged a fee.",
            channel="Web",
            local_sentiment=Sentiment.NEGATIVE,
            local_category="Fees",
            local_urgency=60,
            similar_cases=evidence,
        )

        self.assertIn('"complaint_id":"history-1"', prompt)
        self.assertIn("context only", prompt)

    def test_structured_similar_case_validation(self) -> None:
        result = enrichment(
            similar_cases=[
                {
                    "complaint_id": "history-2",
                    "similarity_score": 0.65,
                    "category": None,
                    "next_action": None,
                    "approved_response": None,
                    "ai_status": "completed",
                }
            ]
        )

        self.assertEqual(result.similar_cases[0].complaint_id, "history-2")

    def test_embedding_vector_contract_rejects_wrong_dimensions(self) -> None:
        with self.assertRaises(InvalidEmbeddingError):
            EmbeddingService("unused")._validate_embedding([0.1, 0.2])

    def test_retrieval_rejects_invalid_bounds_before_database_access(self) -> None:
        service = SimilarComplaintService()
        with self.assertRaises(ValueError):
            service._validate_query([0.0] * 384, threshold=1.1, limit=3)
        with self.assertRaises(ValueError):
            service._validate_query([0.0] * 383, threshold=0.6, limit=3)


class ComplaintFilterTests(unittest.TestCase):
    def test_relevance_requires_search(self) -> None:
        with self.assertRaises(ValidationError):
            ComplaintFilters(sort_by="relevance")


class AuthorizationTests(unittest.TestCase):
    def test_configured_bearer_key_maps_to_principal(self) -> None:
        configured = settings(
            '{"manager-key":{"actor":"harsh","role":"manager"}}'
        )
        principal = get_current_principal(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="manager-key"),
            configured,
        )

        self.assertEqual(principal, Principal(actor="harsh", role=Role.MANAGER))

    def test_agent_cannot_execute_manager_guard(self) -> None:
        manager_only = require_roles(Role.MANAGER, Role.ADMIN)

        with self.assertRaises(HTTPException) as raised:
            manager_only(Principal(actor="agent", role=Role.AGENT))

        self.assertEqual(raised.exception.status_code, 403)

    def test_invalid_auth_mapping_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            settings('{"key":{"actor":"x","role":"owner"}}')


if __name__ == "__main__":
    unittest.main()
