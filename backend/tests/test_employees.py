import unittest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.constants import Role
from app.core.security import create_jwt_token, decode_jwt_token, Principal
from app.employees.models import Employee
from app.employees.schemas import EmployeeCreate, LoginRequest
from app.employees.service import (
    EmployeeService,
    InvalidCredentialsError,
    AccountSuspendedError,
    hash_password,
    verify_password,
)
from app.employees.router import auth_router, admin_router


class EmployeeServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_password_hashing(self) -> None:
        pwd = "super-secret-password-123"
        hashed = hash_password(pwd)
        self.assertNotEqual(pwd, hashed)
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    async def test_jwt_token_generation_and_decoding(self) -> None:
        secret = "my_super_secret_jwt_key_of_at_least_32_characters"
        payload = {"sub": "EMP001", "role": "admin", "exp": datetime.now(UTC).timestamp() + 3600}
        token = create_jwt_token(payload, secret)
        self.assertIsNotNone(token)
        
        decoded = decode_jwt_token(token, secret)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "EMP001")
        self.assertEqual(decoded["role"], "admin")

    @patch("app.employees.service.EmployeeRepository")
    @patch("app.employees.service.AuditLogRepository")
    async def test_create_employee_success(self, mock_audit_repo, mock_emp_repo) -> None:
        mock_db = AsyncMock()
        payload = EmployeeCreate(
            name="John Doe",
            email="john@example.com",
            password="securepassword",
            role="agent",
        )
        
        mock_emp_repo.return_value.get_by_email = AsyncMock(return_value=None)
        
        created_employee = Employee(
            id="emp-uuid",
            employee_id="EMP001",
            name="John Doe",
            email="john@example.com",
            password_hash="somehash",
            role="agent",
            status="active",
        )
        mock_emp_repo.return_value.create = AsyncMock(return_value=created_employee)
        mock_audit_repo.return_value.create = AsyncMock()

        service = EmployeeService(
            employee_repo=mock_emp_repo.return_value,
            audit_repo=mock_audit_repo.return_value,
        )
        
        emp = await service.create_employee(mock_db, payload, created_by="EMP999")
        self.assertEqual(emp.employee_id, "EMP001")
        self.assertEqual(emp.name, "John Doe")
        mock_emp_repo.return_value.create.assert_called_once()
        mock_audit_repo.return_value.create.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("app.employees.service.EmployeeRepository")
    @patch("app.employees.service.AuditLogRepository")
    async def test_authenticate_success(self, mock_audit_repo, mock_emp_repo) -> None:
        mock_db = AsyncMock()
        employee = Employee(
            id="emp-uuid",
            employee_id="EMP001",
            name="John Doe",
            email="john@example.com",
            password_hash=hash_password("securepassword"),
            role="agent",
            status="active",
            must_change_password=False,
        )
        
        mock_emp_repo.return_value.get_by_email = AsyncMock(return_value=employee)
        mock_audit_repo.return_value.create = AsyncMock()
        
        service = EmployeeService(
            employee_repo=mock_emp_repo.return_value,
            audit_repo=mock_audit_repo.return_value,
        )
        
        authenticated = await service.authenticate(mock_db, "john@example.com", "securepassword")
        self.assertEqual(authenticated.employee_id, "EMP001")
        mock_audit_repo.return_value.create.assert_called_once()
        self.assertEqual(mock_audit_repo.return_value.create.call_args[1]["action"], "auth.login_success")


class EmployeesRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(auth_router)
        self.app.include_router(admin_router)
        self.client = TestClient(self.app)

    @patch("app.employees.router.EmployeeService")
    def test_login_success(self, mock_service_class) -> None:
        employee = Employee(
            id="emp-uuid",
            employee_id="EMP001",
            name="John Doe",
            email="john@example.com",
            password_hash="somehash",
            role="agent",
            status="active",
            must_change_password=False,
        )
        
        mock_service = MagicMock()
        mock_service.authenticate = AsyncMock(return_value=employee)
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            "/api/auth/login",
            json={"email": "john@example.com", "password": "securepassword"},
        )
        
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("access_token", body)
        self.assertEqual(body["role"], "agent")
        self.assertEqual(body["employee_id"], "EMP001")
        self.assertEqual(body["must_change_password"], False)

    @patch("app.employees.router.EmployeeService")
    def test_admin_list_employees_returns_200(self, mock_service_class) -> None:
        from app.core.security import get_current_principal
        self.app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor="EMP999",
            role=Role.ADMIN,
        )
        mock_service = MagicMock()
        mock_service.list_employees = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        response = self.client.get("/api/admin/employees")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["items"], [])
        self.assertEqual(body["total"], 0)



if __name__ == "__main__":
    unittest.main()
