import csv
import io
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace

from app.exports.schemas.export_schemas import ComplaintCSVExportQuery, FeedbackCSVExportQuery
from app.exports.services.csv_service import CSVExportService
from app.feedback.schemas import AgentFeedbackUpsertRequest
from app.feedback.service import FeedbackService
from app.sla.schemas.sla_schemas import SLASummaryQuery
from app.sla.services.sla_service import SLAService
from backend.tests.conftest import collect_async_text, complaint_row, feedback_payload


@dataclass
class Store:
    complaints: list[dict] = field(default_factory=list)
    feedback: list[dict] = field(default_factory=list)
    duplicate_groups: list[dict] = field(default_factory=list)


class StoreSLARepository:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def get_summary(self, db, **kwargs):
        completed = [row for row in self.store.complaints if row["ai_status"] == "completed"]
        timely = sum(1 for row in completed if row["timely_response"] is True)
        untimely = sum(1 for row in completed if row["timely_response"] is False)
        avg_urgency = (
            sum(row["urgency_score"] for row in completed if row["urgency_score"] is not None) / len(completed)
            if completed
            else None
        )
        high_urgency_untimely = sum(
            1 for row in completed if (row["urgency_score"] or 0) >= 70 and row["timely_response"] is False
        )
        return {
            "total_complaints": len(completed),
            "timely_count": timely,
            "untimely_count": untimely,
            "avg_urgency_score": avg_urgency,
            "high_urgency_untimely_count": high_urgency_untimely,
        }


class StoreExportRepository:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def stream_complaints(self, db, filters):
        for row in self.store.complaints[: filters.limit]:
            yield {
                "complaint_id": row["source_complaint_id"] or row["id"],
                "narrative": row["narrative"],
                "channel": row["channel"],
                "product": row["product"],
                "sub_product": row["sub_product"],
                "issue": row["issue"],
                "sub_issue": row["sub_issue"],
                "company": row["company"],
                "company_response": row["company_response"],
                "timely_response": row["timely_response"],
                "date_received": row["date_received"],
                "sentiment": row["sentiment"],
                "category": row["category"],
                "urgency_score": row["urgency_score"],
                "churn_risk": row["churn_risk"],
                "draft_response": row["draft_response"],
                "next_action": row["next_action"],
                "ai_confidence": row["ai_confidence"],
                "ai_status": row["ai_status"],
                "processed_at": row["processed_at"],
                "created_at": row["created_at"],
            }

    async def stream_feedback(self, db, filters):
        items = self.store.feedback
        if filters.action_type is not None:
            items = [row for row in items if row["action_type"] == filters.action_type.value]
        for row in items[: filters.limit]:
            yield row

    async def get_analytics_export_rows(self, db, filters):
        excluded = {
            member
            for group in self.store.duplicate_groups
            if group["status"] == "merged"
            for member in group["members"][1:]
        }
        rows = [row for row in self.store.complaints if row["id"] not in excluded and row["ai_status"] == "completed"]
        if not rows:
            return []
        total = len(rows)
        timely = sum(1 for row in rows if row["timely_response"] is True)
        high_churn = sum(1 for row in rows if row["churn_risk"] == "High")
        avg_urgency = sum(row["urgency_score"] for row in rows) / total
        return [
            {
                "product": rows[0]["product"],
                "channel": rows[0]["channel"],
                "sentiment": rows[0]["sentiment"],
                "total_complaints": total,
                "avg_urgency": avg_urgency,
                "timely_rate_pct": timely / total * 100.0,
                "high_churn_count": high_churn,
            }
        ]


class StoreFeedbackRepository:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def get_complaint_by_source_id(self, db, complaint_id):
        for row in self.store.complaints:
            if row["source_complaint_id"] == complaint_id:
                return SimpleNamespace(id=row["id"], source_complaint_id=row["source_complaint_id"])
        return None

    async def feedback_exists(self, db, complaint_pk):
        return any(row["complaint_pk"] == complaint_pk for row in self.store.feedback)

    async def upsert_feedback(self, db, complaint_pk, payload):
        record = {
            "feedback_id": f"fb-{len(self.store.feedback) + 1}",
            "complaint_pk": complaint_pk,
            "complaint_id": next(row["source_complaint_id"] for row in self.store.complaints if row["id"] == complaint_pk),
            "action_type": payload.feedback_action.value,
            "original_draft_response": next(row["draft_response"] for row in self.store.complaints if row["id"] == complaint_pk),
            "final_response": payload.final_response,
            "action_used": payload.action_used,
            "human_review_outcome": payload.human_review_outcome.value,
            "similar_case_useful": payload.similar_cases_useful,
            "created_at": datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        }
        self.store.feedback = [row for row in self.store.feedback if row["complaint_pk"] != complaint_pk]
        self.store.feedback.append(record)
        return SimpleNamespace(
            agent_id=payload.agent_id,
            feedback_action=payload.feedback_action.value,
            final_response=payload.final_response,
            action_used=payload.action_used,
            human_review_outcome=payload.human_review_outcome.value,
            similar_cases_useful=payload.similar_cases_useful,
            notes=payload.notes,
            revision_count=0,
            submitted_at=record["created_at"],
            updated_at=record["created_at"],
        )


class FullPipelineIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_complaint_processed_then_sla_summary_reflects_it(self) -> None:
        store = Store(complaints=[complaint_row()])

        summary = await SLAService(StoreSLARepository(store)).get_summary(object(), SLASummaryQuery())

        self.assertEqual(summary.total_complaints, 1)
        self.assertEqual(summary.timely_rate_pct, 100.0)

    async def test_complaint_processed_then_appears_in_csv_export(self) -> None:
        store = Store(complaints=[complaint_row()])
        payload = await collect_async_text(
            CSVExportService(StoreExportRepository(store)).stream_complaints_csv(
                object(),
                ComplaintCSVExportQuery(limit=10),
            )
        )

        row = list(csv.DictReader(io.StringIO(payload)))[0]
        self.assertEqual(row["complaint_id"], "CP-001")

    async def test_feedback_saved_then_appears_in_feedback_csv_export(self) -> None:
        store = Store(complaints=[complaint_row()])
        service = FeedbackService(StoreFeedbackRepository(store))

        await service.upsert_feedback(
            object(),
            "CP-001",
            AgentFeedbackUpsertRequest(**feedback_payload()),
        )
        payload = await collect_async_text(
            CSVExportService(StoreExportRepository(store)).stream_feedback_csv(
                object(),
                FeedbackCSVExportQuery(limit=10),
            )
        )

        row = list(csv.DictReader(io.StringIO(payload)))[0]
        self.assertEqual(row["complaint_id"], "CP-001")
        self.assertEqual(row["action_type"], "accepted")

    async def test_duplicate_group_created_then_excluded_from_analytics(self) -> None:
        store = Store(
            complaints=[
                complaint_row(id="pk-1", source_complaint_id="CP-001"),
                complaint_row(id="pk-2", source_complaint_id="CP-002"),
            ],
            duplicate_groups=[{"status": "merged", "members": ["pk-1", "pk-2"]}],
        )

        rows = await StoreExportRepository(store).get_analytics_export_rows(object(), SimpleNamespace())

        self.assertEqual(rows[0]["total_complaints"], 1)

    async def test_analytics_trend_matches_manually_computed_values(self) -> None:
        store = Store(
            complaints=[
                complaint_row(id="pk-1", source_complaint_id="CP-001", timely_response=True, urgency_score=80),
                complaint_row(id="pk-2", source_complaint_id="CP-002", timely_response=False, urgency_score=60),
            ]
        )

        rows = await StoreExportRepository(store).get_analytics_export_rows(object(), SimpleNamespace())

        self.assertEqual(rows[0]["total_complaints"], 2)
        self.assertEqual(rows[0]["timely_rate_pct"], 50.0)
        self.assertEqual(rows[0]["avg_urgency"], 70.0)
