import unittest

from app.ai.ml_models.classifier import classify_category
from app.ai.pipelines.complaint_pipeline import ComplaintAIPipeline
from app.core.config import Settings
from app.core.constants import ChurnRisk, Sentiment
from app.intelligence.evidence_service import EvidenceService
from app.intelligence.key_issue_service import KeyIssueService
from app.intelligence.reason_codes import detect_reason_codes
from app.intelligence.resolution_validation_service import ResolutionValidationService
from app.intelligence.risk_signal_service import RiskSignalService
from app.schemas.ai_response import AIEnrichment, ConfidenceScores, SimilarCaseEvidence
from app.schemas.complaint import ComplaintProcessRequest


CHECKING_UNAUTHORIZED_NARRATIVE = (
    "On or about XX/XX/XXXX, I noticed there were at least 13 unauthorized charges "
    "on my checking account. These charges were made once per month. Capital One "
    "reversed 3 of those credits without my knowledge or consent. These charges "
    "were fraudulent and not authorized by me so Capital One should refund the money."
)


class Member1IntelligenceTests(unittest.TestCase):
    def test_reason_codes_and_evidence_use_real_unauthorized_checking_example(self) -> None:
        reason_codes = detect_reason_codes(CHECKING_UNAUTHORIZED_NARRATIVE)
        evidence = EvidenceService().snippets_for_text(CHECKING_UNAUTHORIZED_NARRATIVE)

        self.assertIn("unauthorized_transaction", reason_codes)
        self.assertIn("fee_dispute", reason_codes)
        self.assertTrue(any(snippet.matched_phrase for snippet in evidence))

    def test_key_issue_returns_summary_with_supporting_snippet(self) -> None:
        result = KeyIssueService().extract(
            CHECKING_UNAUTHORIZED_NARRATIVE,
            product="Checking or savings account",
            issue="Problem with a lender or other company charging your account",
            category="Account issue",
        )

        self.assertIn("Problem with a lender", result.summary)
        self.assertGreater(result.confidence, 0.6)
        self.assertTrue(result.evidence_snippets)

    def test_risk_signal_flags_unauthorized_financial_harm(self) -> None:
        result = RiskSignalService().score(
            CHECKING_UNAUTHORIZED_NARRATIVE,
            urgency_score=72,
            ai_confidence=0.87,
        )

        self.assertGreaterEqual(result.score, 72)
        self.assertIn(result.level, {"High", "Critical"})
        self.assertIn("unauthorized_transaction", result.reason_codes)
        self.assertIsNotNone(result.fraud_risk_score)
        self.assertIsNotNone(result.escalation_risk_score)

    def test_resolution_validation_blocks_risky_reuse_even_with_same_issue(self) -> None:
        result = ResolutionValidationService().validate(
            CHECKING_UNAUTHORIZED_NARRATIVE,
            current_category="Account issue",
            current_product="Checking or savings account",
            current_issue="Problem with a lender or other company charging your account",
            current_reason_codes=["unauthorized_transaction", "financial_harm", "delayed_response"],
            similar_cases=[
                SimilarCaseEvidence(
                    complaint_id="10012231",
                    similarity_score=0.96,
                    category="Account issue",
                    product="Checking or savings account",
                    issue="Problem with a lender or other company charging your account",
                    reason_codes=["unauthorized_transaction", "financial_harm"],
                    next_action="Review account hold.",
                    approved_response="We reviewed the account hold and restored access.",
                    ai_status="completed",
                )
            ],
            risk_reason_codes=["unauthorized_transaction", "financial_harm", "delayed_response"],
        )

        self.assertEqual(result.status, "escalate")
        self.assertIn("high_similarity_but_risky", result.reason_codes)
        self.assertIn("unauthorized_transaction_with_financial_harm", result.hard_blockers)
        self.assertGreaterEqual(result.reason_code_overlap or 0, 0.6)

    def test_resolution_validation_allows_safe_reuse_when_dataset_gates_pass(self) -> None:
        narrative = (
            "The account was charged a late fee after payment was made. "
            "I disputed the fee, provided proof, and requested correction because the fee appears incorrect. "
            "The bank should reverse the fee and explain the billing adjustment."
        )

        result = ResolutionValidationService().validate(
            narrative,
            current_category="Card services",
            current_product="Credit card or prepaid card",
            current_issue="Fees or interest",
            current_reason_codes=["fee_dispute"],
            similar_cases=[
                SimilarCaseEvidence(
                    complaint_id="3442136",
                    similarity_score=0.94,
                    category="Card services",
                    product="Credit card or prepaid card",
                    issue="Fees or interest",
                    reason_codes=["fee_dispute"],
                    approved_response="We reviewed the fee dispute and reversed the incorrect fee.",
                    ai_status="completed",
                )
            ],
            risk_reason_codes=["fee_dispute"],
        )

        self.assertEqual(result.status, "safe_reuse")
        self.assertGreaterEqual(result.reason_code_overlap or 0, 0.6)
        self.assertGreaterEqual(result.evidence_strength or 0, 0.7)
        self.assertEqual(result.hard_blockers, [])

    def test_resolution_validation_marks_below_retrieval_threshold_as_bad_match(self) -> None:
        result = ResolutionValidationService().validate(
            CHECKING_UNAUTHORIZED_NARRATIVE,
            current_category="Account issue",
            current_product="Checking or savings account",
            current_issue="Problem with a lender or other company charging your account",
            current_reason_codes=["unauthorized_transaction"],
            similar_cases=[
                SimilarCaseEvidence(
                    complaint_id="bad-1",
                    similarity_score=0.79,
                    category="Card services",
                    product="Credit card",
                    issue="Closing your account",
                    reason_codes=["fee_dispute"],
                    approved_response="We closed the account.",
                    ai_status="completed",
                )
            ],
            risk_reason_codes=["unauthorized_transaction"],
        )

        self.assertEqual(result.status, "bad_match")
        self.assertIn("similarity_below_retrieval_threshold", result.reason_codes)

    def test_classifier_uses_mismatch_profile_product_overrides(self) -> None:
        debt_category = classify_category(
            "There are collection accounts on my report that I believe contain inaccurate information.",
            product="Debt collection",
            issue="Attempts to collect debt not owed",
        )
        account_category = classify_category(
            CHECKING_UNAUTHORIZED_NARRATIVE,
            product="Checking or savings account",
            issue="Problem with a lender or other company charging your account",
        )
        transfer_category = classify_category(
            "Cash App failed to return money after an unauthorized transaction problem.",
            product="Money transfer, virtual currency, or money service",
            issue="Unauthorized transactions or other transaction problem",
        )

        self.assertEqual(debt_category[0], "Debt collection issue")
        self.assertEqual(account_category[0], "Account issue")
        self.assertEqual(transfer_category[0], "Payment or transfer issue")

    def test_pipeline_enrichment_adds_member1_metadata_without_bedrock(self) -> None:
        pipeline = ComplaintAIPipeline(
            Settings(
                _env_file=None,
                database_url="postgresql+asyncpg://user:pass@localhost/customerpulse",
                bedrock_api_key="example-key",
            )
        )
        complaint = ComplaintProcessRequest(
            complaint_id="8873634",
            narrative=CHECKING_UNAUTHORIZED_NARRATIVE,
            product="Checking or savings account",
            issue="Problem with a lender or other company charging your account",
            channel="Web",
        )
        local = pipeline.run_local_layer(complaint)
        enrichment = AIEnrichment(
            sentiment=Sentiment.NEGATIVE,
            category=local.category,
            urgency_score=local.urgency_score,
            churn_risk=ChurnRisk.HIGH,
            draft_response="",
            next_action="Manual agent review required for this complaint.",
            confidence_scores=ConfidenceScores(sentiment=80, category=88, urgency=82),
            ai_confidence=local.combined_confidence,
        )

        enriched = pipeline.enrich_with_local_intelligence(
            complaint,
            enrichment,
            local=local,
            similar_cases=[],
        )

        self.assertEqual(enriched.category, "Account issue")
        self.assertIn("unauthorized_transaction", enriched.reason_codes)
        self.assertIsNotNone(enriched.key_issue)
        self.assertIsNotNone(enriched.risk_signals)
        self.assertIsNotNone(enriched.resolution_validation)
        self.assertIsNotNone(enriched.resolution_recommendation)
        self.assertTrue(enriched.decision_metadata)
        self.assertTrue(
            any(item.decision_type == "similar_case_retrieval" for item in enriched.decision_metadata)
        )


if __name__ == "__main__":
    unittest.main()

