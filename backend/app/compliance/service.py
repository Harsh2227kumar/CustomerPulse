from datetime import datetime, timezone

from app.compliance.models import (
    ComplianceEvidenceRead,
    ComplianceEvidenceStoreRequest,
    ComplianceResult,
    ComplianceRuleDefinitionCreate,
    ComplianceRuleDefinitionListResponse,
    ComplianceRuleDefinitionRead,
    ComplianceRuleDefinitionUpdate,
    ReasonCodeCreate,
    ReasonCodeListResponse,
    ReasonCodeRead,
)
from app.compliance.repository import ComplianceEvidenceRepository, ComplianceKnowledgeBaseRepository
from app.compliance.storage_models import ComplianceEvidenceRecord, ComplianceRuleRecord, ReasonCodeRecord


class ComplianceEvidenceNotFoundError(Exception):
    pass


class ComplianceRuleNotFoundError(Exception):
    pass


class ComplianceRuleVersionConflictError(Exception):
    pass


class ReasonCodeConflictError(Exception):
    pass


class ComplianceEvidenceService:
    def __init__(self, repository: ComplianceEvidenceRepository | None = None) -> None:
        self.repository = repository or ComplianceEvidenceRepository()

    async def store_result(
        self,
        db,
        result: ComplianceResult,
        notes: str | None = None,
    ) -> ComplianceEvidenceRead:
        values = self._build_record_values(result, notes)
        record = await self.repository.create_record(db, values)
        return self._to_read(record)

    async def store_request(
        self,
        db,
        payload: ComplianceEvidenceStoreRequest,
    ) -> ComplianceEvidenceRead:
        return await self.store_result(db, payload.result, payload.notes)

    async def get_record(
        self,
        db,
        record_id: str,
    ) -> ComplianceEvidenceRead:
        record = await self.repository.get_record(db, record_id)
        if record is None:
            raise ComplianceEvidenceNotFoundError(record_id)
        return self._to_read(record)

    async def list_records(
        self,
        db,
        limit: int,
        offset: int,
        complaint_id: str | None = None,
        risk_level: str | None = None,
        regulatory_flag: bool | None = None,
        product: str | None = None,
        company: str | None = None,
        channel: str | None = None,
    ) -> tuple[list[ComplianceEvidenceRead], int]:
        records, count = await self.repository.list_records(
            db,
            limit=limit,
            offset=offset,
            complaint_id=complaint_id,
            risk_level=risk_level,
            regulatory_flag=regulatory_flag,
            product=product,
            company=company,
            channel=channel,
        )
        return [self._to_read(record) for record in records], count

    async def delete_record(
        self,
        db,
        record_id: str,
    ) -> None:
        record = await self.repository.get_record(db, record_id)
        if record is None:
            raise ComplianceEvidenceNotFoundError(record_id)
        await self.repository.delete_record(db, record)

    def _build_record_values(self, result: ComplianceResult, notes: str | None) -> dict:
        triggered_rules = [rule.model_dump(mode="json") for rule in result.triggered_rules]
        required_actions = [action.model_dump(mode="json") for action in result.required_actions]
        evidence_snippets = [
            snippet
            for rule in result.triggered_rules
            for snippet in rule.evidence
        ]
        required_action = required_actions[0]["action_type"] if required_actions else None
        regulatory_flag = self._has_regulatory_flag(result)

        return {
            "complaint_id": result.complaint_id,
            "source_complaint_id": result.source_complaint_id,
            "risk_level": result.compliance_risk_level,
            "required_action": required_action,
            "regulatory_flag": regulatory_flag,
            "regulatory_interpretation": result.sla_reading.regulatory_interpretation,
            "triggered_rules": triggered_rules,
            "evidence_snippets": evidence_snippets,
            "required_actions": required_actions,
            "reason_codes": result.reason_codes,
            "result_payload": result.model_dump(mode="json"),
            "notes": notes,
            "evaluated_at": result.evaluated_at,
        }

    def _has_regulatory_flag(self, result: ComplianceResult) -> bool:
        if result.sla_reading.regulatory_interpretation != "no_regulatory_sla_exception":
            return True
        return any(action.action_type == "notify_regulator" for action in result.required_actions)

    def _to_read(self, record: ComplianceEvidenceRecord) -> ComplianceEvidenceRead:
        return ComplianceEvidenceRead(
            id=record.id,
            complaint_id=record.complaint_id,
            source_complaint_id=record.source_complaint_id,
            risk_level=record.risk_level,
            required_action=record.required_action,
            regulatory_flag=record.regulatory_flag,
            regulatory_interpretation=record.regulatory_interpretation,
            triggered_rules=record.triggered_rules,
            evidence_snippets=record.evidence_snippets,
            required_actions=record.required_actions,
            reason_codes=record.reason_codes,
            result=ComplianceResult.model_validate(record.result_payload),
            notes=record.notes,
            evaluated_at=record.evaluated_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ComplianceKnowledgeBaseService:
    def __init__(self, repository: ComplianceKnowledgeBaseRepository | None = None) -> None:
        self.repository = repository or ComplianceKnowledgeBaseRepository()

    async def create_rule(self, db, payload: ComplianceRuleDefinitionCreate) -> ComplianceRuleDefinitionRead:
        existing = await self.repository.get_rule_by_identity(db, payload.rule_id, payload.version)
        if existing is not None:
            raise ComplianceRuleVersionConflictError(payload.rule_id)
        record = await self.repository.create_rule(db, payload.model_dump(mode="python"))
        return self._rule_to_read(record)

    async def update_rule_version(
        self,
        db,
        record_id: str,
        payload: ComplianceRuleDefinitionUpdate,
    ) -> ComplianceRuleDefinitionRead:
        previous = await self.repository.get_rule(db, record_id)
        if previous is None:
            raise ComplianceRuleNotFoundError(record_id)
        if payload.rule_id == previous.rule_id and payload.version == previous.version:
            raise ComplianceRuleVersionConflictError(payload.rule_id)
        existing = await self.repository.get_rule_by_identity(db, payload.rule_id, payload.version)
        if existing is not None:
            raise ComplianceRuleVersionConflictError(payload.rule_id)
        record = await self.repository.create_rule_version(db, previous, payload.model_dump(mode="python"))
        return self._rule_to_read(record)

    async def get_rule(self, db, record_id: str) -> ComplianceRuleDefinitionRead:
        record = await self.repository.get_rule(db, record_id)
        if record is None:
            raise ComplianceRuleNotFoundError(record_id)
        return self._rule_to_read(record)

    async def list_rules(
        self,
        db,
        limit: int,
        offset: int,
        regulator: str | None = None,
        domain: str | None = None,
        status: str | None = None,
        active_on: datetime | None = None,
    ) -> ComplianceRuleDefinitionListResponse:
        records, count = await self.repository.list_rules(
            db,
            limit=limit,
            offset=offset,
            regulator=regulator,
            domain=domain,
            status=status,
            active_on=active_on,
        )
        return ComplianceRuleDefinitionListResponse(
            items=[self._rule_to_read(record) for record in records],
            limit=limit,
            offset=offset,
            count=count,
        )

    async def load_active_rules(
        self,
        db,
        regulator: str | None = None,
        domain: str | None = None,
        active_on: datetime | None = None,
    ) -> list[ComplianceRuleDefinitionRead]:
        response = await self.list_rules(
            db,
            limit=500,
            offset=0,
            regulator=regulator,
            domain=domain,
            active_on=active_on or datetime.now(timezone.utc),
        )
        return response.items

    async def create_reason_code(self, db, payload: ReasonCodeCreate) -> ReasonCodeRead:
        existing = await self.repository.get_reason_code(db, payload.code)
        if existing is not None:
            raise ReasonCodeConflictError(payload.code)
        record = await self.repository.create_reason_code(db, payload.model_dump(mode="python"))
        return self._reason_code_to_read(record)

    async def list_reason_codes(
        self,
        db,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> ReasonCodeListResponse:
        records, count = await self.repository.list_reason_codes(db, limit=limit, offset=offset, status=status)
        return ReasonCodeListResponse(
            items=[self._reason_code_to_read(record) for record in records],
            limit=limit,
            offset=offset,
            count=count,
        )

    def _rule_to_read(self, record: ComplianceRuleRecord) -> ComplianceRuleDefinitionRead:
        return ComplianceRuleDefinitionRead(
            id=record.id,
            rule_id=record.rule_id,
            rule_name=record.rule_name,
            regulator=record.regulator,
            domain=record.domain,
            version=record.version,
            status=record.status,
            description=record.description,
            evaluation_type=record.evaluation_type,
            severity=record.severity,
            reason_code=record.reason_code,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            supersedes_rule_record_id=record.supersedes_rule_record_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _reason_code_to_read(self, record: ReasonCodeRecord) -> ReasonCodeRead:
        return ReasonCodeRead(
            id=record.id,
            code=record.code,
            description=record.description,
            severity=record.severity,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )






