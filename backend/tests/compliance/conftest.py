import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.compliance.models import AIResponseFields, AISignals, ComplaintComplianceInput, SLAState


BASE_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(scope="session")
def compliance_mock_data() -> dict[str, Any]:
    fixture_path = Path(__file__).parent / "fixtures" / "mock_compliance_data.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def make_complaint(**overrides: Any) -> ComplaintComplianceInput:
    payload = {
        "complaint_id": "complaint-1",
        "source_complaint_id": "SRC-1",
        "product": "Credit card",
        "issue": "Billing dispute",
        "sub_issue": None,
        "channel": "Web",
        "date_received": BASE_DATE,
        "acknowledged_at": BASE_DATE + timedelta(days=1),
        "resolved_at": BASE_DATE + timedelta(days=10),
        "amount_disputed": None,
        "ai_signals": AISignals(severity="medium", urgency_score=50),
        "response_fields": AIResponseFields(
            category="billing",
            urgency_score=50,
            draft_response="We reviewed the complaint and prepared a response.",
            resolution="Complaint resolved with evidence.",
            next_action="Close with evidence",
            ai_confidence=0.86,
        ),
        "sla": SLAState(is_breached=False, breach_risk_level="low", days_elapsed=10, days_to_deadline=20),
    }
    payload.update(overrides)
    return ComplaintComplianceInput(**payload)


class CapturingRepository:
    def __init__(self, created_at: datetime | None = None) -> None:
        self.created_at = created_at or BASE_DATE + timedelta(hours=1)
        self.records: list[dict[str, Any]] = []

    async def create_record(self, db: object, values: dict[str, Any]) -> SimpleNamespace:
        persisted_values = json.loads(json.dumps(values, default=str))
        persisted_values["evaluated_at"] = values["evaluated_at"]
        self.records.append(persisted_values)
        return SimpleNamespace(
            id=f"evidence-{len(self.records)}",
            created_at=self.created_at,
            updated_at=self.created_at,
            **values,
        )

    async def get_record(self, db: object, record_id: str) -> SimpleNamespace | None:
        index = int(record_id.rsplit("-", 1)[1]) - 1
        if index < 0 or index >= len(self.records):
            return None
        values = self.records[index]
        return SimpleNamespace(
            id=record_id,
            created_at=self.created_at,
            updated_at=self.created_at,
            **values,
        )

    async def list_records(
        self,
        db: object,
        limit: int,
        offset: int,
        complaint_id: str | None = None,
        risk_level: str | None = None,
        regulatory_flag: bool | None = None,
        product: str | None = None,
        company: str | None = None,
        channel: str | None = None,
    ) -> tuple[list[SimpleNamespace], int]:
        filtered = list(self.records)
        if complaint_id is not None:
            filtered = [record for record in filtered if record["complaint_id"] == complaint_id]
        if risk_level is not None:
            filtered = [record for record in filtered if record["risk_level"] == risk_level]
        if regulatory_flag is not None:
            filtered = [record for record in filtered if record["regulatory_flag"] is regulatory_flag]
        if product is not None:
            filtered = [record for record in filtered if record.get("product") == product]
        if company is not None:
            filtered = [record for record in filtered if record.get("company") == company]
        if channel is not None:
            filtered = [record for record in filtered if record.get("channel") == channel]

        page = filtered[offset : offset + limit]
        return [
            SimpleNamespace(
                id=f"evidence-{offset + index + 1}",
                created_at=self.created_at,
                updated_at=self.created_at,
                **record,
            )
            for index, record in enumerate(page)
        ], len(filtered)
    async def delete_record(self, db: object, record: SimpleNamespace) -> None:
        index = int(record.id.rsplit("-", 1)[1]) - 1
        if 0 <= index < len(self.records):
            self.records.pop(index)

