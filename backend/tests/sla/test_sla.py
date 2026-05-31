import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.db.session import get_db_session
from app.main import app
from app.sla.schemas.sla_schemas import (
    SLABreachRiskQuery,
    SLAGroupedQuery,
    SLAGroupSortBy,
    SLASummaryQuery,
    SLATrendGranularity,
    SLATrendQuery,
)
from app.sla.services.sla_service import SLAService
from tests.conftest import make_async_repository


class SLAServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_sla_summary_computes_timely_rate_correctly(self) -> None:
        repository = make_async_repository(
            get_summary={
                "total_complaints": 4,
                "timely_count": 3,
                "untimely_count": 1,
                "avg_urgency_score": 65.444,
                "high_urgency_untimely_count": 1,
            }
        )

        result = await SLAService(repository).get_summary(object(), SLASummaryQuery())

        self.assertEqual(result.timely_rate_pct, 75.0)
        self.assertEqual(result.avg_urgency_score, 65.44)

    async def test_sla_summary_returns_zero_when_no_complaints(self) -> None:
        repository = make_async_repository(
            get_summary={
                "total_complaints": 0,
                "timely_count": 0,
                "untimely_count": 0,
                "avg_urgency_score": None,
                "high_urgency_untimely_count": 0,
            }
        )

        result = await SLAService(repository).get_summary(object(), SLASummaryQuery())

        self.assertEqual(result.total_complaints, 0)
        self.assertEqual(result.timely_rate_pct, 0.0)
        self.assertIsNone(result.avg_urgency_score)

    async def test_sla_by_product_groups_correctly(self) -> None:
        repository = make_async_repository(
            get_grouped_summary=(
                [
                    {
                        "product": "Credit card",
                        "total": 3,
                        "timely": 2,
                        "untimely": 1,
                        "avg_urgency_score": 70.0,
                    },
                    {
                        "product": "Mortgage",
                        "total": 1,
                        "timely": 1,
                        "untimely": 0,
                        "avg_urgency_score": 55.0,
                    },
                ],
                2,
            )
        )

        result = await SLAService(repository).get_by_product(
            object(),
            SLAGroupedQuery(limit=10, sort_by=SLAGroupSortBy.TOTAL),
        )

        self.assertEqual(result.count, 2)
        self.assertEqual(result.items[0].product, "Credit card")
        self.assertEqual(result.items[0].timely_rate_pct, 66.67)

    async def test_sla_by_channel_groups_correctly(self) -> None:
        repository = make_async_repository(
            get_grouped_summary=(
                [
                    {
                        "channel": "Web",
                        "total": 2,
                        "timely": 1,
                        "untimely": 1,
                        "avg_urgency_score": 60.0,
                    }
                ],
                1,
            )
        )

        result = await SLAService(repository).get_by_channel(object(), SLAGroupedQuery())

        self.assertEqual(result.count, 1)
        self.assertEqual(result.items[0].channel, "Web")
        self.assertEqual(result.items[0].untimely, 1)

    async def test_sla_breach_risk_filters_by_urgency_threshold(self) -> None:
        repository = make_async_repository(get_breach_risk=([], 0))

        await SLAService(repository).get_breach_risk(
            object(),
            SLABreachRiskQuery(urgency_threshold=88),
        )

        self.assertEqual(repository.get_breach_risk.await_args.kwargs["urgency_threshold"], 88)

    async def test_sla_breach_risk_respects_churn_risk_filter(self) -> None:
        repository = make_async_repository(get_breach_risk=([], 0))

        await SLAService(repository).get_breach_risk(
            object(),
            SLABreachRiskQuery(churn_risk="High"),
        )

        self.assertEqual(str(repository.get_breach_risk.await_args.kwargs["churn_risk"]), "High")

    async def test_sla_trend_monthly_groups_by_month(self) -> None:
        repository = make_async_repository(
            get_trend=[
                {
                    "period": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "total": 4,
                    "timely": 3,
                    "untimely": 1,
                }
            ]
        )

        result = await SLAService(repository).get_trend(
            object(),
            SLATrendQuery(granularity=SLATrendGranularity.MONTHLY),
        )

        self.assertEqual(result.items[0].period, "2026-01")
        self.assertEqual(result.items[0].timely_rate_pct, 75.0)

    async def test_sla_trend_weekly_groups_by_week(self) -> None:
        repository = make_async_repository(
            get_trend=[
                {
                    "period": datetime(2026, 1, 12, tzinfo=timezone.utc),
                    "total": 2,
                    "timely": 1,
                    "untimely": 1,
                }
            ]
        )

        result = await SLAService(repository).get_trend(
            object(),
            SLATrendQuery(granularity=SLATrendGranularity.WEEKLY),
        )

        self.assertEqual(result.items[0].period, "2026-01-12")
        self.assertEqual(result.items[0].timely_rate_pct, 50.0)

    async def test_sla_summary_excludes_non_completed_complaints(self) -> None:
        from app.sla.repositories.sla_repository import SLARepository

        conditions = SLARepository()._completed_conditions(product="Credit card")

        self.assertEqual(len(conditions), 2)
        self.assertIn("ai_status", str(conditions[0]))
        self.assertIn("product", str(conditions[1]))

    async def test_sla_breach_risk_respects_pagination(self) -> None:
        repository = make_async_repository(get_breach_risk=([], 19))

        result = await SLAService(repository).get_breach_risk(
            object(),
            SLABreachRiskQuery(limit=5, offset=10),
        )

        self.assertEqual(result.limit, 5)
        self.assertEqual(result.offset, 10)
        self.assertEqual(repository.get_breach_risk.await_args.kwargs["offset"], 10)


class SLAEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_summary_returns_200(self) -> None:
        payload = SimpleNamespace(
            get_summary=AsyncMock(
                return_value={
                    "total_complaints": 4,
                    "timely_count": 3,
                    "untimely_count": 1,
                    "timely_rate_pct": 75.0,
                    "avg_urgency_score": 65.44,
                    "high_urgency_untimely_count": 1,
                    "period_from": None,
                    "period_to": None,
                }
            )
        )
        with patch("app.sla.api.routes.SLAService", return_value=payload):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sla/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["timely_rate_pct"], 75.0)

    async def test_by_product_returns_200(self) -> None:
        payload = SimpleNamespace(
            get_by_product=AsyncMock(
                return_value={"items": [{"product": "Credit card", "total": 2, "timely": 1, "untimely": 1, "timely_rate_pct": 50.0, "avg_urgency_score": 72.0}], "count": 1}
            )
        )
        with patch("app.sla.api.routes.SLAService", return_value=payload):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sla/by-product")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    async def test_by_channel_returns_200(self) -> None:
        payload = SimpleNamespace(
            get_by_channel=AsyncMock(
                return_value={"items": [{"channel": "Web", "total": 2, "timely": 1, "untimely": 1, "timely_rate_pct": 50.0, "avg_urgency_score": 72.0}], "count": 1}
            )
        )
        with patch("app.sla.api.routes.SLAService", return_value=payload):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sla/by-channel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["channel"], "Web")

    async def test_breach_risk_returns_200(self) -> None:
        payload = SimpleNamespace(
            get_breach_risk=AsyncMock(return_value={"items": [], "total": 0, "limit": 50, "offset": 0})
        )
        with patch("app.sla.api.routes.SLAService", return_value=payload):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sla/breach-risk")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 0)

    async def test_trend_monthly_returns_200(self) -> None:
        payload = SimpleNamespace(
            get_trend=AsyncMock(return_value={"granularity": "monthly", "items": []})
        )
        with patch("app.sla.api.routes.SLAService", return_value=payload):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sla/trend", params={"granularity": "monthly"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["granularity"], "monthly")

    async def test_trend_weekly_returns_200(self) -> None:
        payload = SimpleNamespace(
            get_trend=AsyncMock(return_value={"granularity": "weekly", "items": []})
        )
        with patch("app.sla.api.routes.SLAService", return_value=payload):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sla/trend", params={"granularity": "weekly"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["granularity"], "weekly")

    async def test_sla_validation_errors_return_422(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            invalid_limit = await client.get("/api/sla/by-product", params={"limit": 0})
            invalid_granularity = await client.get("/api/sla/trend", params={"granularity": "daily"})

        self.assertEqual(invalid_limit.status_code, 422)
        self.assertEqual(invalid_granularity.status_code, 422)
