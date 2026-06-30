import asyncio
import os
import sys

from sqlalchemy import select
<<<<<<< HEAD
=======
from sqlalchemy.ext.asyncio import AsyncSession
>>>>>>> 28a6894 (Add member-3 changes: employees module, escalations, exports, and backend updates)

# Ensure we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import AsyncSessionLocal
from app.employees.models import Employee
from app.employees.repository import EmployeeRepository
from app.employees.service import hash_password


async def seed_admin():
    async with AsyncSessionLocal() as db:
<<<<<<< HEAD
        email = os.getenv("SEED_ADMIN_EMAIL", "superadmin@example.com")
        password = os.getenv("SEED_ADMIN_PASSWORD", "SuperAdmin@123")
        name = os.getenv("SEED_ADMIN_NAME", "System Super Admin")
        hashed = hash_password(password)

        existing_admin_result = await db.execute(
            select(Employee).where(Employee.email == email)
        )
        existing_admin = existing_admin_result.scalar_one_or_none()
        if existing_admin is not None:
            existing_admin.name = name
            existing_admin.password_hash = hashed
            existing_admin.role = "super_admin"
            existing_admin.status = "active"
            existing_admin.must_change_password = True
            await db.commit()
            print(
                "Success! Reset existing super_admin "
                f"{email} with employee_id: {existing_admin.employee_id}"
            )
            return
=======
        # Check if any employee exists
        result = await db.execute(select(Employee).limit(1))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Seed aborted: Employees table is not empty.")
            return

        email = os.getenv("SEED_ADMIN_EMAIL", "superadmin@example.com")
        password = os.getenv("SEED_ADMIN_PASSWORD", "SuperAdmin@123")
        name = os.getenv("SEED_ADMIN_NAME", "System Super Admin")
>>>>>>> 28a6894 (Add member-3 changes: employees module, escalations, exports, and backend updates)

        print(f"Creating first super_admin: {email}")

        repo = EmployeeRepository()
<<<<<<< HEAD
=======
        hashed = hash_password(password)
        
>>>>>>> 28a6894 (Add member-3 changes: employees module, escalations, exports, and backend updates)
        employee = await repo.create(
            db=db,
            name=name,
            email=email,
            password_hash=hashed,
            role="super_admin",
            status="active",
            must_change_password=True,
        )
<<<<<<< HEAD

=======
        
>>>>>>> 28a6894 (Add member-3 changes: employees module, escalations, exports, and backend updates)
        await db.commit()
        print(f"Success! Created super_admin with employee_id: {employee.employee_id}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
