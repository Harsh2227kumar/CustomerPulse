import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.analytics.repository import get_product_summary
from app.analytics.router import complaint_trends, high_urgency, human_review_trends, product_summary
from app.db.session import get_db_session
from app.main import app


class AnalyticsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

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
