import asyncio
import unittest
from unittest.mock import patch

from app.api.health import health_check


class StubSettings:
    app_name = "CustomerPulse AI Backend"
    app_version = "test"
    environment = "test"
    s3_import_configured = True


class HealthEndpointTests(unittest.TestCase):
    def test_health_contract_reports_service_readiness_metadata(self) -> None:
        with patch("app.api.health.get_settings", return_value=StubSettings()):
            result = asyncio.run(health_check())

        self.assertEqual(
            result,
            {
                "status": "ok",
                "service": "CustomerPulse AI Backend",
                "version": "test",
                "environment": "test",
                "s3_import_configured": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
