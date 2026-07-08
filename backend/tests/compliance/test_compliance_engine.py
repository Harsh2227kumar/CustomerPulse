import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone

from httpx import ASGITransport, AsyncClient

from app.compliance.engine import ComplianceEngine
from app.compliance.models import AIResponseFields, AISignals, ComplaintComplianceInput, SLAState
from app.compliance.service import ComplianceEvidenceService
from app.compliance.rule_registry import load_rule_registry
from app.main import app
from app.db.session import get_db_session


BASE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def compliance_input(**overrides):
    payload = {
        "complaint_id": "complaint-1",
        "source_complaint_id": "SRC-1",
        "product": "Credit card",
        "issue": "Billing dispute",
        "date_received": BASE_DATE,
        "acknowledged_at": BASE_DATE + timedelta(days=1),
        "resolved_at": BASE_DATE + timedelta(days=10),
        "ai_signals": AISignals(severity="medium", urgency_score=50),
        "response_fields": AIResponseFields(
            category="billing",
            urgency_score=50,
            draft_response="We reviewed the complaint and prepared a response.",
            resolution="Complaint resolved with evidence.",
            next_action="Close with evidence",
            ai_confidence=0.86,
        ),
        "sla": SLAState(is_breached=False, breach_risk_level="low", days_elapsed=10),
    }
    payload.update(overrides)
    return ComplaintComplianceInput(**payload)


class ComplianceEngineTests(unittest.TestCase):
    def test_rule_registry_loads_data_driven_rules(self) -> None:
        rules = load_rule_registry()

        self.assertGreaterEqual(len(rules), 6)
        self.assertIn("RBI-FRAUD-001", {rule.rule_id for rule in rules})

    def test_clean_complaint_returns_low_risk_without_rules(self) -> None:
        result = ComplianceEngine().evaluate(compliance_input(), evaluated_at=BASE_DATE)

        self.assertEqual(result.compliance_risk_level, "low")
        self.assertEqual(result.triggered_rules, [])
        self.assertEqual(result.reason_codes, [])
        self.assertEqual(result.sla_reading.regulatory_interpretation, "no_regulatory_sla_exception")

    def test_fraud_sla_breach_triggers_audit_ready_critical_result(self) -> None:
        complaint = compliance_input(
            issue="Unauthorized transaction and fraud claim",
            acknowledged_at=None,
            resolved_at=None,
            ai_signals=AISignals(severity="high", urgency_score=91, fraud_risk_score=88, key_issue="unauthorized transfer"),
            sla=SLAState(is_breached=True, breach_risk_level="critical", days_elapsed=35),
        )

        result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=35))
        rule_ids = {rule.rule_id for rule in result.triggered_rules}

        self.assertEqual(result.compliance_risk_level, "critical")
        self.assertIn("RBI-ACK-001", rule_ids)
        self.assertIn("RBI-FRAUD-001", rule_ids)
        self.assertIn("RBI-RES-030", rule_ids)
        self.assertIn("RBI-SLA-FRAUD-002", rule_ids)
        self.assertEqual(result.reason_codes, [rule.rule_id for rule in result.triggered_rules])
        self.assertTrue(all(rule.evidence for rule in result.triggered_rules))
        self.assertTrue(all(rule.triggered_at == BASE_DATE + timedelta(days=35) for rule in result.triggered_rules))
        self.assertEqual(result.sla_reading.regulatory_interpretation, "breached_fraud_or_unauthorized_complaint")

    def test_high_value_urgency_dispute_sets_deadline_from_intake_date(self) -> None:
        complaint = compliance_input(
            amount_disputed=250000,
            issue="Transaction dispute",
            ai_signals=AISignals(severity="high", urgency_score=82),
            sla=SLAState(is_breached=False, breach_risk_level="high", days_elapsed=2),
        )

        result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE)
        actions_by_rule = {rule.rule_id: rule.required_action for rule in result.triggered_rules}

        self.assertEqual(result.compliance_risk_level, "high")
        self.assertEqual(actions_by_rule["RBI-HV-001"].deadline_at, BASE_DATE + timedelta(days=2))
        self.assertIn("RBI-NEAR-HIGH-003", actions_by_rule)


class ComplianceEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_evaluate_endpoint_returns_report_ready_contract(self) -> None:
        payload = {
            "complaint_id": "complaint-2",
            "source_complaint_id": "SRC-2",
            "product": "Checking account",
            "issue": "Unauthorized transaction",
            "date_received": BASE_DATE.isoformat(),
            "acknowledged_at": None,
            "resolved_at": None,
            "response_fields": {
                "category": "fraud",
                "urgency_score": 80,
                "draft_response": "We reviewed the unauthorized transaction complaint.",
                "resolution": "Escalated to fraud operations with evidence.",
                "next_action": "Escalate to fraud operations",
                "ai_confidence": 0.9,
            },
            "ai_signals": {
                "severity": "high",
                "urgency_score": 80,
                "fraud_risk_score": 90,
                "key_issue": "unauthorized debit",
            },
            "sla": {
                "is_breached": True,
                "breach_risk_level": "critical",
                "days_elapsed": 31,
            },
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/compliance/evaluate?store=false", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["compliance_risk_level"], "critical")
        self.assertIn("RBI-FRAUD-001", body["reason_codes"])
        self.assertIn("required_actions", body)
        self.assertIn("sla_reading", body)



class ComplianceEvidenceStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_result_captures_audit_ready_evidence_fields(self) -> None:
        complaint = compliance_input(
            issue="Unauthorized transaction and fraud claim",
            acknowledged_at=None,
            resolved_at=None,
            ai_signals=AISignals(severity="high", urgency_score=91, fraud_risk_score=88, key_issue="unauthorized transfer"),
            sla=SLAState(is_breached=True, breach_risk_level="critical", days_elapsed=35),
        )
        result = ComplianceEngine().evaluate(complaint, evaluated_at=BASE_DATE + timedelta(days=35))
        created_at = BASE_DATE + timedelta(days=35, minutes=1)

        class FakeRepository:
            async def create_record(self, db, values):
                return SimpleNamespace(id="evidence-1", created_at=created_at, updated_at=created_at, **values)

        stored = await ComplianceEvidenceService(FakeRepository()).store_result(object(), result, notes=" reviewed ")

        self.assertEqual(stored.id, "evidence-1")
        self.assertEqual(stored.risk_level, "critical")
        self.assertEqual(stored.required_action, "acknowledge")
        self.assertTrue(stored.regulatory_flag)
        self.assertIn("RBI-FRAUD-001", stored.reason_codes)
        self.assertTrue(any("fraud_risk_score=88" in snippet for snippet in stored.evidence_snippets))
        self.assertEqual(stored.notes, " reviewed ")
        self.assertEqual(stored.result.complaint_id, result.complaint_id)


class ComplianceEvidenceEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_evaluate_endpoint_stores_by_default(self) -> None:
        payload = {
            "complaint_id": "complaint-3",
            "source_complaint_id": "SRC-3",
            "product": "Checking account",
            "issue": "Unauthorized transaction",
            "date_received": BASE_DATE.isoformat(),
            "acknowledged_at": None,
            "resolved_at": None,
            "response_fields": {
                "category": "fraud",
                "urgency_score": 80,
                "draft_response": "We reviewed the unauthorized transaction complaint.",
                "resolution": "Escalated to fraud operations with evidence.",
                "next_action": "Escalate to fraud operations",
                "ai_confidence": 0.9,
            },
            "ai_signals": {
                "severity": "high",
                "urgency_score": 80,
                "fraud_risk_score": 90,
                "key_issue": "unauthorized debit",
            },
            "sla": {
                "is_breached": True,
                "breach_risk_level": "critical",
                "days_elapsed": 31,
            },
        }
        service = SimpleNamespace(store_result=AsyncMock())

        with patch("app.compliance.router.ComplianceEvidenceService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/compliance/evaluate", json=payload)

        self.assertEqual(response.status_code, 200)
        service.store_result.assert_awaited_once()


    async def test_list_evidence_endpoint_passes_metadata_filters(self) -> None:
        service = SimpleNamespace(list_records=AsyncMock(return_value=([], 0)))

        with patch("app.compliance.router.ComplianceEvidenceService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/api/compliance/evidence?product=Credit%20card&company=Test%20Bank&channel=Web"
                )

        self.assertEqual(response.status_code, 200)
        kwargs = service.list_records.await_args.kwargs
        self.assertEqual(kwargs["product"], "Credit card")
        self.assertEqual(kwargs["company"], "Test Bank")
        self.assertEqual(kwargs["channel"], "Web")

    async def test_delete_evidence_endpoint_calls_service(self) -> None:
        service = SimpleNamespace(delete_record=AsyncMock())

        with patch("app.compliance.router.ComplianceEvidenceService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete("/api/compliance/evidence/evidence-1")

        self.assertEqual(response.status_code, 204)
        service.delete_record.assert_awaited_once()

