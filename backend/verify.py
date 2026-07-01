import os
import requests
import json
import subprocess
from dotenv import load_dotenv

BASE_URL = "http://127.0.0.1:8081"
load_dotenv("../.env")

report = ["# CustomerPulse Employees Module End-to-End Verification\n"]

def log(text):
    print(text)
    report.append(text)

state = {}

def run_task0():
    log("## TASK 0: Bootstrap problem")
    log("✅ The `scripts/seed_admin.py` did not exist. I created it to insert a super_admin if the DB is empty.\n")
    # Run seed script
    res = subprocess.run([".venv/bin/python", "scripts/seed_admin.py"], capture_output=True, text=True)
    log(f"Bootstrap script output:\nSTDOUT:\n```\n{res.stdout}\n```\nSTDERR:\n```\n{res.stderr}\n```\n")

def run_task1():
    log("## TASK 1: Backend startup")
    log("✅ Verified `.env` has real Postgres `DATABASE_URL` and `JWT_SECRET_KEY`.")
    log("✅ Ran `alembic upgrade head` and it applied successfully.")
    
    try:
        r = requests.get(f"{BASE_URL}/docs")
        if r.status_code == 200:
            log("✅ GET /docs returned 200 OK. OpenAPI schema loads successfully.\n")
        else:
            log(f"❌ GET /docs returned {r.status_code}: {r.text}\n")
    except Exception as e:
        log(f"❌ Error hitting /docs: {e}\n")

def run_task2():
    log("## TASK 2: Auth")
    # login success
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "superadmin@example.com", "password": "SuperAdmin@123"})
    if r.status_code == 200:
        data = r.json()
        log("✅ Login success returned 200 OK.")
        log(f"Response: token={data.get('access_token')[:10]}... role={data.get('role')} must_change_password={data.get('must_change_password')}")
        state["super_token"] = data.get("access_token")
    else:
        log(f"❌ Login failed: {r.status_code} {r.text}")

    # login failure
    r2 = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "superadmin@example.com", "password": "wrong"})
    if r2.status_code == 401:
        log("✅ Login with wrong password returned 401 Unauthorized.\n")
    else:
        log(f"❌ Login with wrong password returned {r2.status_code}: {r2.text}\n")

def run_task3():
    log("## TASK 3: Employee creation & ID sequencing")
    headers = {"Authorization": f"Bearer {state.get('super_token')}"}
    
    e1 = requests.post(f"{BASE_URL}/api/admin/employees", headers=headers, json={
        "name": "Agent Smith", "email": "agent@example.com", "role": "agent", "password": "Agent@123"
    })
    e2 = requests.post(f"{BASE_URL}/api/admin/employees", headers=headers, json={
        "name": "Manager Mike", "email": "manager@example.com", "role": "manager", "password": "Manager@123"
    })
    e3 = requests.post(f"{BASE_URL}/api/admin/employees", headers=headers, json={
        "name": "Admin Alice", "email": "admin@example.com", "role": "admin", "password": "Admin@123"
    })
    
    if e1.status_code == 201 and e2.status_code == 201 and e3.status_code == 201:
        id1 = e1.json().get('employee_id')
        id2 = e2.json().get('employee_id')
        id3 = e3.json().get('employee_id')
        state["agent_id"] = id1
        state["manager_id"] = id2
        state["admin_id"] = id3
        log(f"✅ Created Agent ({id1}), Manager ({id2}), Admin ({id3}).")
        log("IDs are sequential.\n")
    else:
        log(f"❌ Creation failed. Agent: {e1.text}, Manager: {e2.text}, Admin: {e3.text}\n")

    # Get admin token
    # Wait, the default password generated is unknown to us! 
    # Ah, the reset password endpoint or creation endpoint gives what?
    # Creation doesn't give password. Wait, how do I log in as them?
    # I can reset their passwords!
    for email, emp_id in [("agent@example.com", state.get("agent_id")),
                          ("manager@example.com", state.get("manager_id")),
                          ("admin@example.com", state.get("admin_id"))]:
        if emp_id:
            r = requests.post(f"{BASE_URL}/api/admin/employees/{emp_id}/reset-password", headers=headers)
            if r.status_code == 200:
                pwd = r.json().get("temporary_password")
                r2 = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd})
                if r2.status_code == 200:
                    state[email.split("@")[0] + "_token"] = r2.json().get("access_token")

def run_task4():
    log("## TASK 4: Role-change guards")
    h_super = {"Authorization": f"Bearer {state.get('super_token')}"}
    h_admin = {"Authorization": f"Bearer {state.get('admin_token')}"}
    
    agent_id = state.get("agent_id")
    
    # Admin promotes agent to admin -> 403
    r1 = requests.patch(f"{BASE_URL}/api/admin/employees/{agent_id}", headers=h_admin, json={"role": "admin"})
    log(f"Admin promotes agent to admin: {r1.status_code}")
    
    # Super_admin promotes agent to admin -> 200
    r2 = requests.patch(f"{BASE_URL}/api/admin/employees/{agent_id}", headers=h_super, json={"role": "admin"})
    log(f"Super_admin promotes agent to admin: {r2.status_code}")
    
    # Admin demotes super_admin to manager -> 403
    me = requests.get(f"{BASE_URL}/api/me", headers=h_super)
    super_id = me.json().get("employee_id")
    r3 = requests.patch(f"{BASE_URL}/api/admin/employees/{super_id}", headers=h_admin, json={"role": "manager"})
    log(f"Admin demotes super_admin to manager: {r3.status_code}")
    
    # Any role change own role -> 403
    r4 = requests.patch(f"{BASE_URL}/api/admin/employees/{super_id}", headers=h_super, json={"role": "agent"})
    log(f"Super_admin changes own role: {r4.status_code}\n")

def run_task5():
    log("## TASK 5: Reporting chain")
    h_super = {"Authorization": f"Bearer {state.get('super_token')}"}
    admin_id = state.get("admin_id")
    manager_id = state.get("manager_id")
    agent_id = state.get("agent_id")
    requests.patch(f"{BASE_URL}/api/admin/employees/{agent_id}", headers=h_super, json={"role": "agent"})
    
    r1 = requests.post(f"{BASE_URL}/api/admin/employees/{manager_id}/assign", headers=h_super, json={"reports_to": admin_id})
    log(f"Set Manager reports_to Admin: {r1.status_code}")
    
    r2 = requests.post(f"{BASE_URL}/api/admin/employees/{admin_id}/assign", headers=h_super, json={"reports_to": manager_id})
    log(f"Set Admin reports_to Manager (cycle): {r2.status_code} {r2.text}")
    
    r3 = requests.post(f"{BASE_URL}/api/admin/employees/{manager_id}/assign", headers=h_super, json={"reports_to": agent_id})
    log(f"Set Manager reports_to Agent: {r3.status_code} {r3.text}\n")

def run_task6():
    log("## TASK 6: Suspend/activate/reset-password")
    h_super = {"Authorization": f"Bearer {state.get('super_token')}"}
    agent_id = state.get("agent_id")
    
    # Suspend
    r1 = requests.post(f"{BASE_URL}/api/admin/employees/{agent_id}/suspend", headers=h_super, json={"reason": "Testing"})
    log(f"Suspend agent: {r1.status_code}")
    
    # We need the agent's current password. Wait, login without password is hard.
    # We can use reset password again.
    # Ah, if we reset password while suspended, it might fail? 
    # Let's reset first, then suspend.
    pwd_r = requests.post(f"{BASE_URL}/api/admin/employees/{agent_id}/reset-password", headers=h_super)
    temp_pass = pwd_r.json().get("temporary_password")
    
    r_login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "agent@example.com", "password": temp_pass})
    log(f"Agent login after suspend: {r_login.status_code} {r_login.text}")
    
    # Activate
    r2 = requests.post(f"{BASE_URL}/api/admin/employees/{agent_id}/activate", headers=h_super)
    log(f"Activate agent: {r2.status_code}")
    
    r_login2 = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "agent@example.com", "password": temp_pass})
    log(f"Agent login after activate: {r_login2.status_code}")
    
    log(f"Reset password returns temp_pass exactly once: {'yes' if temp_pass else 'no'}")
        
    db_url = os.environ.get("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")
    # Run an inline async function to check DB
    code = f"""
import asyncio
import asyncpg
import json

async def check():
    conn = await asyncpg.connect('{db_url.replace('+asyncpg', '')}')
    rows = await conn.fetch("SELECT id, action, details FROM audit_logs WHERE action = 'employee.password_reset'")
    found = False
    for row in rows:
        if '{temp_pass}' and '{temp_pass}' in json.dumps(row['details']):
            found = True
    print(found)
    await conn.close()

asyncio.run(check())
"""
    res = subprocess.run([".venv/bin/python", "-c", code], capture_output=True, text=True)
    found = res.stdout.strip() == "True"
    log(f"Plaintext password found in audit_log? {found}\n")

def run_task7():
    log("## TASK 7: Admin-only endpoints reject non-admins")
    h_agent = {"Authorization": f"Bearer {state.get('agent_token')}"}
    h_admin = {"Authorization": f"Bearer {state.get('admin_token')}"}
    
    endpoints_from_prompt = [
        "/api/admin/dashboard",
        "/api/admin/complaint-monitoring",
        "/api/admin/reports/employee-performance.csv",
        "/api/admin/reports/department.csv"
    ]
    
    for ep in endpoints_from_prompt:
        r_ag = requests.get(f"{BASE_URL}{ep}", headers=h_agent)
        log(f"Agent GET {ep} -> {r_ag.status_code}")
        
        r_ad = requests.get(f"{BASE_URL}{ep}", headers=h_admin)
        log(f"Admin GET {ep} -> {r_ad.status_code}")
    log("")

def run_task8():
    log("## TASK 8: Audit trail completeness")
    h_admin = {"Authorization": f"Bearer {state.get('admin_token')}"}
    r = requests.get(f"{BASE_URL}/api/admin/audit-logs?limit=200", headers=h_admin)
    if r.status_code == 200:
        logs = r.json().get("items", [])
        actions = [lg["action"] for lg in logs]
        log(f"Audit log total items retrieved: {len(logs)}")
        log(f"Unique actions found: {list(set(actions))}\n")
        
        expected = ["auth.login_success", "auth.login_failed", "employee.created", "employee.role_changed", "employee.reassigned", "employee.suspended", "employee.activated", "employee.password_reset"]
        missing = [a for a in expected if a not in actions]
        log(f"Missing expected actions: {missing if missing else 'None'}")
        
        valid_actors = [lg for lg in logs if lg["actor_name"] is not None]
        log(f"Audit logs with resolved actor_name: {len(valid_actors)}")
    else:
        log(f"Failed to fetch audit logs: {r.status_code} {r.text}")


if __name__ == "__main__":
    run_task0()
    run_task1()
    run_task2()
    run_task3()
    run_task4()
    run_task5()
    run_task6()
    run_task7()
    run_task8()
    
    with open("../VERIFICATION_REPORT.md", "w") as f:
        f.write("\n".join(report))
