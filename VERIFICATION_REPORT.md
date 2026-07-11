# CustomerPulse Employees Module End-to-End Verification

## TASK 0: Bootstrap problem
✅ The `scripts/seed_admin.py` did not exist. I created it to insert a super_admin if the DB is empty.

Bootstrap script output:
STDOUT:
```
Seed aborted: Employees table is not empty.

```
STDERR:
```

```

## TASK 1: Backend startup
✅ Verified `.env` has real Postgres `DATABASE_URL` and `JWT_SECRET_KEY`.
✅ Ran `alembic upgrade head` and it applied successfully.
✅ GET /docs returned 200 OK. OpenAPI schema loads successfully.

## TASK 2: Auth
✅ Login success returned 200 OK.
Response: token=eyJhbGciOi... role=super_admin must_change_password=True
✅ Login with wrong password returned 401 Unauthorized.

## TASK 3: Employee creation & ID sequencing
❌ Creation failed. Agent: {"detail":"Employee with email 'agent@example.com' already exists."}, Manager: {"detail":"Employee with email 'manager@example.com' already exists."}, Admin: {"detail":"Employee with email 'admin@example.com' already exists."}

## TASK 4: Role-change guards
Admin promotes agent to admin: 401
Super_admin promotes agent to admin: 404
Admin demotes super_admin to manager: 401
Super_admin changes own role: 404

## TASK 5: Reporting chain
Set Manager reports_to Admin: 404
Set Admin reports_to Manager (cycle): 404 {"detail":"Employee 'None' not found."}
Set Manager reports_to Agent: 404 {"detail":"Employee 'None' not found."}

## TASK 6: Suspend/activate/reset-password
Suspend agent: 404
Agent login after suspend: 422 {"detail":[{"type":"string_type","loc":["body","password"],"msg":"Input should be a valid string","input":null}]}
Activate agent: 404
Agent login after activate: 422
Reset password returns temp_pass exactly once: no
Plaintext password found in audit_log? False

## TASK 7: Admin-only endpoints reject non-admins
Agent GET /api/admin/dashboard -> 401
Admin GET /api/admin/dashboard -> 401
Agent GET /api/admin/complaint-monitoring -> 401
Admin GET /api/admin/complaint-monitoring -> 401
Agent GET /api/admin/reports/employee-performance.csv -> 401
Admin GET /api/admin/reports/employee-performance.csv -> 401
Agent GET /api/admin/reports/department.csv -> 401
Admin GET /api/admin/reports/department.csv -> 401

## TASK 8: Audit trail completeness
Failed to fetch audit logs: 401 {"detail":"Invalid bearer credentials."}