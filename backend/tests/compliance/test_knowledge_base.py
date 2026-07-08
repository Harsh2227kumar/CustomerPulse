import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.compliance.models import ComplianceRuleDefinitionCreate, ComplianceRuleDefinitionUpdate, ReasonCodeCreate
from app.compliance.service import ComplianceKnowledgeBaseService
from app.db.session import get_db_session
from app.main import app

BASE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def rule_record(**overrides):
    values = {
        "id": "rule-record-1",
        "rule_id": "RBI-SLA-RESOLUTION-001",
        "rule_name": "Complaint Resolution SLA",
        "regulator": "RBI",
        "domain": "sla_compliance",
        "version": "1.0.0",
        "status": "active",
        "description": "Validate complaint resolution SLA.",
        "evaluation_type": "duration_threshold",
        "severity": "high",
        "reason_code": "SLA_BREACHED",
        "effective_from": BASE_DATE,
        "effective_to": None,
        "supersedes_rule_record_id": None,
        "created_at": BASE_DATE,
        "updated_at": BASE_DATE,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def rule_payload(**overrides):
    values = {
        "rule_id": "RBI-SLA-RESOLUTION-001",
        "rule_name": "Complaint Resolution SLA",
        "regulator": "RBI",
        "domain": "SLA Compliance",
        "version": "1.0.0",
        "status": "active",
        "description": "Validate complaint resolution SLA.",
        "evaluation_type": "Duration Threshold",
        "severity": "high",
        "reason_code": "sla breached",
        "effective_from": BASE_DATE,
        "effective_to": None,
    }
    values.update(overrides)
    return ComplianceRuleDefinitionCreate(**values)


def reason_record(**overrides):
    values = {
        "id": "reason-1",
        "code": "SLA_BREACHED",
        "description": "Complaint handling SLA has been breached.",
        "severity": "high",
        "status": "active",
        "created_at": BASE_DATE,
        "updated_at": BASE_DATE,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class KnowledgeBaseServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_rule_creation_persists_normalized_config_record(self) -> None:
        created = rule_record(domain="sla_compliance", evaluation_type="duration_threshold")
        repository = SimpleNamespace(
            get_rule_by_identity=AsyncMock(return_value=None),
            create_rule=AsyncMock(return_value=created),
        )
        service = ComplianceKnowledgeBaseService(repository)

        result = await service.create_rule(object(), rule_payload())

        repository.create_rule.assert_awaited_once()
        values = repository.create_rule.await_args.args[1]
        self.assertEqual(values["domain"], "sla_compliance")
        self.assertEqual(values["evaluation_type"], "duration_threshold")
        self.assertEqual(values["reason_code"], "SLA_BREACHED")
        self.assertEqual(result.rule_id, "RBI-SLA-RESOLUTION-001")

    async def test_rule_versioning_creates_new_record_that_supersedes_previous(self) -> None:
        previous = rule_record(id="old-record", version="1.0.0")
        created = rule_record(
            id="new-record",
            version="1.1.0",
            supersedes_rule_record_id="old-record",
            description="Updated SLA threshold.",
        )
        repository = SimpleNamespace(
            get_rule=AsyncMock(return_value=previous),
            get_rule_by_identity=AsyncMock(return_value=None),
            create_rule_version=AsyncMock(return_value=created),
        )
        service = ComplianceKnowledgeBaseService(repository)
        payload = ComplianceRuleDefinitionUpdate(**rule_payload(version="1.1.0", description="Updated SLA threshold.").model_dump())

        result = await service.update_rule_version(object(), "old-record", payload)

        repository.create_rule_version.assert_awaited_once()
        self.assertEqual(result.version, "1.1.0")
        self.assertEqual(result.supersedes_rule_record_id, "old-record")

    async def test_reason_code_creation_uses_central_catalog(self) -> None:
        repository = SimpleNamespace(
            get_reason_code=AsyncMock(return_value=None),
            create_reason_code=AsyncMock(return_value=reason_record()),
        )
        service = ComplianceKnowledgeBaseService(repository)
        payload = ReasonCodeCreate(
            code="sla breached",
            description="Complaint handling SLA has been breached.",
            severity="high",
            status="active",
        )

        result = await service.create_reason_code(object(), payload)

        values = repository.create_reason_code.await_args.args[1]
        self.assertEqual(values["code"], "SLA_BREACHED")
        self.assertEqual(result.code, "SLA_BREACHED")

    async def test_multi_regulator_rules_use_same_schema_and_filters(self) -> None:
        records = [
            rule_record(id="rbi-rule", regulator="RBI"),
            rule_record(id="npci-rule", rule_id="NPCI-UPI-DISPUTE-001", regulator="NPCI", domain="upi_disputes"),
        ]
        repository = SimpleNamespace(list_rules=AsyncMock(return_value=(records, 2)))
        service = ComplianceKnowledgeBaseService(repository)

        response = await service.list_rules(object(), limit=50, offset=0, regulator="NPCI")

        self.assertEqual(response.count, 2)
        repository.list_rules.assert_awaited_once()
        self.assertEqual(repository.list_rules.await_args.kwargs["regulator"], "NPCI")
        self.assertEqual({item.regulator for item in response.items}, {"RBI", "NPCI"})

    async def test_dynamic_rule_loading_returns_active_effective_rules(self) -> None:
        repository = SimpleNamespace(list_rules=AsyncMock(return_value=([rule_record()], 1)))
        service = ComplianceKnowledgeBaseService(repository)
        active_on = BASE_DATE + timedelta(days=10)

        rules = await service.load_active_rules(object(), regulator="RBI", domain="sla_compliance", active_on=active_on)

        self.assertEqual(len(rules), 1)
        kwargs = repository.list_rules.await_args.kwargs
        self.assertEqual(kwargs["regulator"], "RBI")
        self.assertEqual(kwargs["domain"], "sla_compliance")
        self.assertEqual(kwargs["active_on"], active_on)


class KnowledgeBaseEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_create_rule_endpoint_returns_created_record(self) -> None:
        service = SimpleNamespace(create_rule=AsyncMock(return_value=ComplianceKnowledgeBaseService()._rule_to_read(rule_record())))
        payload = rule_payload().model_dump(mode="json")

        with patch("app.compliance.router.ComplianceKnowledgeBaseService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/compliance/rules", json=payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["rule_id"], "RBI-SLA-RESOLUTION-001")
        service.create_rule.assert_awaited_once()

    async def test_list_reason_codes_endpoint_returns_catalog(self) -> None:
        response_model = ComplianceKnowledgeBaseService()._reason_code_to_read(reason_record())
        service = SimpleNamespace(
            list_reason_codes=AsyncMock(
                return_value={"items": [response_model], "limit": 50, "offset": 0, "count": 1}
            )
        )

        with patch("app.compliance.router.ComplianceKnowledgeBaseService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/compliance/reason-codes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["code"], "SLA_BREACHED")
