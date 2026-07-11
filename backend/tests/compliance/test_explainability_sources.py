import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.compliance.explainability.models import ComplianceExplanationWithSources
from app.compliance.explainability.service import generate_explanation_with_sources

NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)


def triggered_rule(rule_id: str = "RBI-FRAUD-001") -> dict:
    return {
        "rule_id": rule_id,
        "description": "fraud or unauthorized transaction rule",
        "severity": "high",
        "required_action": {"action_type": "escalate"},
        "evidence": ["fraud signal present in complaint metadata"],
        "triggered_at": NOW,
    }


class SourceBackedExplainabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_explanation_with_sources_attaches_regulatory_citations(self) -> None:
        search_result = SimpleNamespace(
            results=[
                SimpleNamespace(
                    chunk_id="chunk-1",
                    document_id="document-1",
                    document_title="RBI Fraud Reporting Guideline",
                    regulator="RBI",
                    domain="fraud_reporting",
                    section_reference="Section 4.1",
                    page_start=37,
                    page_end=38,
                    similarity_score=0.91,
                    chunk_text="Fraud reporting must be completed within the required regulatory timeline.",
                    keywords=["fraud", "reporting"],
                    effective_from=None,
                    effective_to=None,
                )
            ]
        )
        kb_service = SimpleNamespace(search_regulatory_knowledge=AsyncMock(return_value=search_result))

        with patch("app.compliance.explainability.service.ComplianceKnowledgeBaseService", return_value=kb_service):
            result = await generate_explanation_with_sources(
                object(),
                {
                    "complaint_id": "complaint-1",
                    "compliance_risk_level": "high",
                    "triggered_rules": [triggered_rule("RBI-FRAUD-001")],
                    "evaluated_at": NOW,
                    "engine_version": "1.0",
                    "rule_set_version": "2026.1",
                },
                {"complaint_id": "complaint-1", "category": "fraud", "issue": "unauthorized transfer"},
                settings=SimpleNamespace(embedding_model="all-MiniLM-L6-v2", embedding_local_files_only=True),
            )

        self.assertIsInstance(result, ComplianceExplanationWithSources)
        self.assertEqual(result.regulatory_sources[0].document_title, "RBI Fraud Reporting Guideline")
        self.assertEqual(result.regulatory_sources[0].supports_rule_ids, ["RBI-FRAUD-001"])
        self.assertIn("deterministic rules decide", result.limitations[0])


if __name__ == "__main__":
    unittest.main()
