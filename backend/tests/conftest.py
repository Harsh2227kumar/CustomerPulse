import os
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/customerpulse_test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")


SAMPLE_COMPLAINT_ROW = {
    "id": "abc123",
    "source_complaint_id": "CP-001",
    "narrative": "My credit card was charged incorrectly.",
    "channel": "Web",
    "product": "Credit card",
    "sub_product": None,
    "issue": "Billing dispute",
    "sub_issue": None,
    "company": "Test Bank",
    "company_response": "Closed with explanation",
    "timely_response": True,
    "date_received": datetime(2026, 1, 15, tzinfo=timezone.utc),
    "sentiment": "Negative",
    "category": "billing",
    "urgency_score": 72,
    "churn_risk": "High",
    "draft_response": "We apologize for the billing error...",
    "next_action": "Investigate charge",
    "confidence_scores": {
        "sentiment": 88,
        "category": 82,
        "urgency": 79,
    },
    "ai_confidence": 0.87,
    "ai_reasoning": "Clear billing dispute with high urgency indicators.",
    "processed_at": datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
    "ai_status": "completed",
    "retry_count": 0,
    "error_message": None,
    "created_at": datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
    "updated_at": datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
}


def complaint_row(**overrides: Any) -> dict[str, Any]:
    row = deepcopy(SAMPLE_COMPLAINT_ROW)
    row.update(overrides)
    return row


def complaint_object(**overrides: Any) -> SimpleNamespace:
    return SimpleNamespace(**complaint_row(**overrides))


def feedback_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "agent_id": "agent-007",
        "feedback_action": "accepted",
        "final_response": "We investigated the issue and corrected the charge.",
        "action_used": True,
        "human_review_outcome": "resolved",
        "similar_cases_useful": True,
        "notes": "Customer-facing response approved.",
    }
    payload.update(overrides)
    return payload


def feedback_record(**overrides: Any) -> SimpleNamespace:
    values = {
        "agent_id": "agent-007",
        "feedback_action": "accepted",
        "final_response": "We investigated the issue and corrected the charge.",
        "action_used": True,
        "human_review_outcome": "resolved",
        "similar_cases_useful": True,
        "notes": "Customer-facing response approved.",
        "revision_count": 0,
        "submitted_at": datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_async_repository(**methods: Any) -> SimpleNamespace:
    repository = SimpleNamespace()
    for name, value in methods.items():
        setattr(
            repository,
            name,
            value if isinstance(value, AsyncMock) else AsyncMock(return_value=value),
        )
    return repository


async def async_rows(rows: list[dict[str, Any]]):
    for row in rows:
        yield row


async def collect_async_text(iterator) -> str:
    chunks: list[str] = []
    async for chunk in iterator:
        chunks.append(chunk)
    return "".join(chunks)


class FakeStreamResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def mappings(self):
        for row in self._rows:
            yield row


class FakeAsyncDB:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[Any] = []

    async def stream(self, stmt):
        self.statements.append(stmt)
        return FakeStreamResult(self.rows)

    async def execute(self, stmt):
        self.statements.append(stmt)
        return SimpleNamespace(
            all=lambda: [],
            mappings=lambda: SimpleNamespace(all=lambda: [], one=lambda: {}, one_or_none=lambda: None),
            scalar_one=lambda: 0,
            scalar_one_or_none=lambda: None,
            scalars=lambda: SimpleNamespace(all=lambda: []),
            one_or_none=lambda: None,
        )
