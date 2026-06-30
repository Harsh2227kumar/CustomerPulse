import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import AsyncSessionLocal
from app.employees.models import Employee
from app.employees.repository import EmployeeRepository
from app.employees.service import hash_password


async def seed_admin():
    async with AsyncSessionLocal() as db:
        # Check if any employee exists
        result = await db.execute(select(Employee).limit(1))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Seed aborted: Employees table is not empty.")
            return

        email = os.getenv("SEED_ADMIN_EMAIL", "superadmin@example.com")
        password = os.getenv("SEED_ADMIN_PASSWORD", "SuperAdmin@123")
        name = os.getenv("SEED_ADMIN_NAME", "System Super Admin")

        print(f"Creating first super_admin: {email}")

        repo = EmployeeRepository()
        hashed = hash_password(password)
        
        employee = await repo.create(
            db=db,
            name=name,
            email=email,
            password_hash=hashed,
            role="super_admin",
            status="active",
            must_change_password=True,
        )
        
        await db.commit()
        print(f"Success! Created super_admin with employee_id: {employee.employee_id}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
