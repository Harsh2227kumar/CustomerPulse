from datetime import UTC, datetime
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/customerpulse_test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

from app.db.session import get_db_session
from app.sla.api.routes import router
from app.sla.schemas.sla_schemas import (
    SLABreachRiskQuery,
    SLABreachRiskResponse,
    SLAGroupedQuery,
    SLAGroupedResponse,
    SLASummaryQuery,
    SLASummaryResponse,
    SLATrendGranularity,
    SLATrendQuery,
    SLATrendResponse,
)
from app.sla.services.sla_service import SLAService


class SLAServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_rounds_metrics_and_logs_warning(self) -> None:
        repository = SimpleNamespace(
            get_summary=AsyncMock(
                return_value={
                    "total_complaints": 4821,
                    "timely_count": 4102,
                    "untimely_count": 719,
                    "avg_urgency_score": 62.444,
                    "high_urgency_untimely_count": 143,
                }
            )
        )

        with self.assertLogs("app.sla.services.sla_service", level="WARNING") as logs:
            result = await SLAService(repository).get_summary(
                db=object(),
                filters=SLASummaryQuery(),
            )

        self.assertEqual(result.timely_rate_pct, 85.09)
        self.assertEqual(result.avg_urgency_score, 62.44)
        self.assertIn("143", logs.output[0])

    async def test_trend_formats_monthly_periods(self) -> None:
        repository = SimpleNamespace(
            get_trend=AsyncMock(
                return_value=[
                    {
                        "period": datetime(2026, 1, 1, tzinfo=UTC),
                        "total": 410,
                        "timely": 348,
                        "untimely": 62,
                    }
                ]
            )
        )

        result = await SLAService(repository).get_trend(
            db=object(),
            filters=SLATrendQuery(granularity=SLATrendGranularity.MONTHLY),
        )

        self.assertEqual(result.items[0].period, "2026-01")
        self.assertEqual(result.items[0].timely_rate_pct, 84.88)

    async def test_breach_risk_returns_schema_response(self) -> None:
        repository = SimpleNamespace(
            get_breach_risk=AsyncMock(
                return_value=(
                    [
                        {
                            "complaint_id": "SRC-1",
                            "source_complaint_id": "SRC-1",
                            "channel": "Email",
                            "product": "Credit card",
                            "timely_response": False,
                            "date_received": datetime(2026, 1, 2, tzinfo=UTC),
                            "urgency_score": 91,
                            "churn_risk": "High",
                            "processed_at": datetime(2026, 1, 3, tzinfo=UTC),
                            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
                        }
                    ],
                    1,
                )
            )
        )

        result = await SLAService(repository).get_breach_risk(
            db=object(),
            filters=SLABreachRiskQuery(churn_risk="High"),
        )

        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].complaint_id, "SRC-1")


class SLARouterTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)

        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session
        self.client = TestClient(app)

    def test_invalid_granularity_returns_422(self) -> None:
        response = self.client.get("/api/sla/trend", params={"granularity": "daily"})
        self.assertEqual(response.status_code, 422)

    def test_summary_endpoint(self) -> None:
        item = SLASummaryResponse(
            total_complaints=4821,
            timely_count=4102,
            untimely_count=719,
            timely_rate_pct=85.08,
            avg_urgency_score=62.4,
            high_urgency_untimely_count=143,
            period_from=None,
            period_to=None,
        )
        service = SimpleNamespace(get_summary=AsyncMock(return_value=item))

        with patch("app.sla.api.routes.SLAService", return_value=service):
            response = self.client.get("/api/sla/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["timely_rate_pct"], 85.08)
        args = service.get_summary.await_args.args
        self.assertIsInstance(args[1], SLASummaryQuery)

    def test_by_product_endpoint(self) -> None:
        payload = SLAGroupedResponse(items=[], count=0)
        service = SimpleNamespace(get_by_product=AsyncMock(return_value=payload))

        with patch("app.sla.api.routes.SLAService", return_value=service):
            response = self.client.get("/api/sla/by-product", params={"sort_by": "total"})

        self.assertEqual(response.status_code, 200)
        args = service.get_by_product.await_args.args
        self.assertIsInstance(args[1], SLAGroupedQuery)

    def test_breach_risk_endpoint(self) -> None:
        payload = SLABreachRiskResponse(items=[], total=0, limit=50, offset=0)
        service = SimpleNamespace(get_breach_risk=AsyncMock(return_value=payload))

        with patch("app.sla.api.routes.SLAService", return_value=service):
            response = self.client.get("/api/sla/breach-risk", params={"churn_risk": "High"})

        self.assertEqual(response.status_code, 200)
        args = service.get_breach_risk.await_args.args
        self.assertIsInstance(args[1], SLABreachRiskQuery)

    def test_trend_endpoint(self) -> None:
        payload = SLATrendResponse(granularity="monthly", items=[])
        service = SimpleNamespace(get_trend=AsyncMock(return_value=payload))

        with patch("app.sla.api.routes.SLAService", return_value=service):
            response = self.client.get("/api/sla/trend")

        self.assertEqual(response.status_code, 200)
        args = service.get_trend.await_args.args
        self.assertIsInstance(args[1], SLATrendQuery)
