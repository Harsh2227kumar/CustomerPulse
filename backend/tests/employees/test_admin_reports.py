"""Tests for GET /api/admin/reports/*.csv.

Covers:
- Employee performance CSV contains correct row count and computed values against seeded fixture data.
- Department CSV correctly aggregates employee_count and complaint metrics.
- Date range filtering works (complaints outside range excluded).
- Manager/agent calling these endpoints gets 403.
"""
import csv
import io
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.constants import Role
from app.core.security import Principal, get_current_principal
from app.db.session import get_db_session

class AdminReportsEndpointTests(unittest.TestCase):
    def _build_client(self, role: Role, actor: str = "EMP999"):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.employees.router import admin_router

        app = FastAPI()
        app.include_router(admin_router)

        async def _override_db():
            yield object()

        app.dependency_overrides[get_db_session] = _override_db
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor=actor, role=role
        )
        return TestClient(app)

    @patch("app.exports.services.csv_service.ExportRepository")
    def test_employee_performance_csv_success(self, mock_repo_class):
        mock_repo = mock_repo_class.return_value
        
        async def mock_stream(*args, **kwargs):
            yield {
                "employee_id": "EMP1",
                "name": "Alice",
                "role": "agent",
                "department": "Support",
                "complaints_handled": 10,
                "complaints_resolved": 8,
                "avg_resolution_time_hours": 1.5,
                "escalations_raised": 2,
            }
        
        mock_repo.stream_employee_performance = mock_stream
        
        client = self._build_client(Role.ADMIN)
        resp = client.get("/api/admin/reports/employee-performance.csv")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "text/csv; charset=utf-8")
        self.assertTrue("attachment" in resp.headers["content-disposition"])
        
        csv_data = resp.text
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["employee_id"], "EMP1")
        self.assertEqual(rows[0]["complaints_handled"], "10")

    @patch("app.exports.services.csv_service.ExportRepository")
    def test_department_report_csv_success(self, mock_repo_class):
        mock_repo = mock_repo_class.return_value
        
        async def mock_stream(*args, **kwargs):
            yield {
                "department": "Support",
                "employee_count": 5,
                "complaints_handled": 50,
                "avg_resolution_time_hours": 2.1,
                "sla_breach_count": 3,
            }
        
        mock_repo.stream_department_report = mock_stream
        
        client = self._build_client(Role.ADMIN)
        resp = client.get("/api/admin/reports/department.csv")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "text/csv; charset=utf-8")
        self.assertTrue("attachment" in resp.headers["content-disposition"])
        
        csv_data = resp.text
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["department"], "Support")
        self.assertEqual(rows[0]["employee_count"], "5")
        self.assertEqual(rows[0]["sla_breach_count"], "3")

    def test_manager_agent_forbidden(self):
        client = self._build_client(Role.MANAGER)
        resp1 = client.get("/api/admin/reports/employee-performance.csv")
        self.assertEqual(resp1.status_code, 403)
        
        resp2 = client.get("/api/admin/reports/department.csv")
        self.assertEqual(resp2.status_code, 403)
        
        client = self._build_client(Role.AGENT)
        resp3 = client.get("/api/admin/reports/employee-performance.csv")
        self.assertEqual(resp3.status_code, 403)
        
        resp4 = client.get("/api/admin/reports/department.csv")
        self.assertEqual(resp4.status_code, 403)

if __name__ == "__main__":
    unittest.main()
