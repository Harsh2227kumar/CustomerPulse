import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.analytics.repository import get_product_summary
from app.analytics.router import complaint_trends, complaint_volume_insights, high_urgency, human_review_trends, product_summary
from app.db.session import get_db_session
from app.main import app


class AnalyticsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()


    async def test_complaint_volume_insights_shapes_operational_metrics(self) -> None:
        rows = {
            "timeline": [
                {
                    "period": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "total": 10,
                    "high_urgency": 3,
                    "human_review": 2,
                    "negative": 5,
                    "timely": 8,
                    "untimely": 2,
                    "avg_urgency": 66.5,
                }
            ],
            "groups": [
                {
                    "group_value": "Credit card",
                    "count": 7,
                    "avg_urgency": 72.0,
                    "high_urgency": 2,
                    "negative": 4,
                    "human_review": 1,
                }
            ],
            "heatmap": [{"product": "Credit card", "channel": "Web", "count": 5, "avg_urgency": 70.0}],
            "sentiment_mix": [{"label": "Negative", "count": 5}],
            "status_mix": [{"label": "completed", "count": 8}],
            "samples": [
                {
                    "complaint_id": "CP-001",
                    "product": "Credit card",
                    "channel": "Web",
                    "category": "billing",
                    "sentiment": "Negative",
                    "ai_status": "completed",
                    "urgency_score": 91,
                    "date_received": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "narrative": "Charge posted twice.",
                }
            ],
        }
        with patch("app.analytics.router.get_complaint_volume_insights", AsyncMock(return_value=rows)):
            response = await complaint_volume_insights("week", "product", None, None, 12, object())

        self.assertEqual(response.summary.total_count, 10)
        self.assertEqual(response.summary.peak_count, 10)
        self.assertEqual(response.groups[0].group, "Credit card")
        self.assertEqual(response.heatmap[0].channel, "Web")
        self.assertEqual(response.samples[0].complaint_id, "CP-001")

    async def test_complaint_trend_monthly_groups_correctly(self) -> None:
        with patch(
            "app.analytics.router.get_complaint_trends",
            AsyncMock(return_value=[(datetime(2026, 1, 1, tzinfo=timezone.utc), 3)]),
        ):
            response = await complaint_trends("month", object())

        self.assertEqual(response.granularity, "month")
        self.assertEqual(response.items[0].period, "2026-01-01T00:00:00+00:00")
        self.assertEqual(response.items[0].count, 3)

    async def test_product_summary_top_products_sorted_by_count(self) -> None:
        with patch(
            "app.analytics.router.get_product_summary",
            AsyncMock(
                return_value=[
                    ("Credit card", "billing", 8, 72.5),
                    ("Mortgage", "servicing", 2, 55.0),
                ]
            ),
        ):
            response = await product_summary(object())

        self.assertEqual(response.items[0].product, "Credit card")
        self.assertGreater(response.items[0].count, response.items[1].count)

    async def test_category_summary_returns_all_categories(self) -> None:
        with patch(
            "app.analytics.router.get_product_summary",
            AsyncMock(
                return_value=[
                    ("Credit card", "billing", 8, 72.5),
                    ("Checking account", "fraud", 3, 61.0),
                ]
            ),
        ):
            response = await product_summary(object())

        self.assertEqual({item.category for item in response.items}, {"billing", "fraud"})

    async def test_human_review_trend_filters_by_date_range(self) -> None:
        with patch(
            "app.analytics.router.get_human_review_trends",
            AsyncMock(return_value=[(datetime(2026, 1, 8, tzinfo=timezone.utc), 5)]),
        ):
            response = await human_review_trends("week", object())

        self.assertEqual(response.granularity, "week")
        self.assertEqual(response.items[0].count, 5)

    async def test_high_urgency_monitor_threshold_filter(self) -> None:
        complaint = SimpleNamespace(
            id="CP-001",
            narrative="Charge posted twice.",
            product="Credit card",
            channel="Web",
            urgency_score=91,
            sentiment="Negative",
            created_at=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
        )
        with patch(
            "app.analytics.router.get_high_urgency",
            AsyncMock(return_value=([complaint], 1)),
        ):
            response = await high_urgency(90, 50, 0, object())

        self.assertEqual(response.count, 1)
        self.assertEqual(response.items[0].urgency_score, 91)

    async def test_aggregations_exclude_pending_complaints(self) -> None:
        executed_queries: list[str] = []

        class FakeDB:
            async def execute(self, query):
                executed_queries.append(str(query))
                return SimpleNamespace(all=lambda: [])

        await get_product_summary(FakeDB())

        self.assertIn("WHERE ai_status = 'completed'", executed_queries[0])

    async def test_trend_empty_period_returns_empty_items(self) -> None:
        with patch("app.analytics.router.get_complaint_trends", AsyncMock(return_value=[])):
            response = await complaint_trends("month", object())

        self.assertEqual(response.items, [])

    async def test_analytics_api_routes_are_async(self) -> None:
        complaint = SimpleNamespace(
            id="CP-001",
            narrative="Charge posted twice.",
            product="Credit card",
            channel="Web",
            urgency_score=91,
            sentiment="Negative",
            created_at=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
        )
        with patch("app.analytics.router.get_complaint_trends", AsyncMock(return_value=[])), patch(
            "app.analytics.router.get_high_urgency",
            AsyncMock(return_value=([complaint], 1)),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                trends = await client.get("/api/analytics/complaint-trends")
                urgency = await client.get("/api/analytics/high-urgency")

        self.assertEqual(trends.status_code, 200)
        self.assertEqual(urgency.status_code, 200)

    async def test_trend_by_category(self) -> None:
        with patch(
            "app.analytics.router.get_complaint_trends_by_category",
            AsyncMock(return_value=[(datetime(2026, 1, 1, tzinfo=timezone.utc), "billing", 5)]),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/analytics/trends/category")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["items"][0]["category"], "billing")
        self.assertEqual(data["items"][0]["count"], 5)

    async def test_trend_by_channel(self) -> None:
        with patch(
            "app.analytics.router.get_complaint_trends_by_channel",
            AsyncMock(return_value=[(datetime(2026, 1, 1, tzinfo=timezone.utc), "web", 12)]),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/analytics/trends/channel")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["items"][0]["channel"], "web")
        self.assertEqual(data["items"][0]["count"], 12)

    async def test_bottlenecks(self) -> None:
        metrics = {
            "avg_intake_to_ai_hours": 0.5,
            "avg_ai_to_review_hours": 2.5,
            "avg_intake_to_review_hours": 3.0,
            "processed_count": 100,
            "reviewed_count": 40,
        }
        with patch(
            "app.analytics.router.get_queue_bottlenecks",
            AsyncMock(return_value=metrics),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/analytics/bottlenecks")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), metrics)

    async def test_root_causes_phrases(self) -> None:
        with patch(
            "app.analytics.router.get_recurring_phrases",
            AsyncMock(return_value=[("Late fees charge", 15, "Credit card", "billing")]),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/analytics/root-causes/phrases")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["items"][0]["phrase"], "Late fees charge")
        self.assertEqual(data["items"][0]["count"], 15)

    async def test_root_causes_spikes(self) -> None:
        spikes = [
            {
                "product": "Credit card",
                "recent_count": 10,
                "previous_count": 2,
                "growth_rate": 4.0,
                "spike_score": 40.0
            }
        ]
        with patch(
            "app.analytics.router.get_product_spikes",
            AsyncMock(return_value=spikes),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/analytics/root-causes/spikes")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["items"][0]["product"], "Credit card")
        self.assertEqual(data["items"][0]["spike_score"], 40.0)

    async def test_root_causes_themes(self) -> None:
        dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        with patch(
            "app.analytics.router.get_duplicate_themes",
            AsyncMock(return_value=[("group-123", "Credit card", "billing", "Late fee", 5, dt)]),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/analytics/root-causes/themes")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["items"][0]["group_id"], "group-123")
        self.assertEqual(data["items"][0]["member_count"], 5)

    async def test_business_impact(self) -> None:
        kpis = {
            "auto_resolution_pct": 75.0,
            "avg_ai_processing_time_sec": 45.0,
            "avg_human_resolution_time_sec": 360.0,
            "timely_response_pct": 98.2,
            "current_breach_rate_pct": 1.8,
            "previous_breach_rate_pct": 4.5,
            "breach_reduction_rate_pct": 2.7,
            "total_processed": 500,
            "total_reviewed": 120,
            "workload_saved_hours": 280.0,
        }
        with patch(
            "app.analytics.router.get_business_impact_kpis",
            AsyncMock(return_value=kpis),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/analytics/business-impact")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), kpis)

