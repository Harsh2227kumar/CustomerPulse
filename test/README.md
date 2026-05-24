# CustomerPulse Test Harness

This directory contains component-level verification for the repository in its
current state:

- `backend/` runs the existing S3 ingestion tests plus new settings, health,
  local AI, and ingestion contract tests.
- `infra/` validates the root `docker-compose.yml` and required environment
  configuration keys.
- `frontend/` detects and builds a frontend once runnable source is present.
  At present, `frontend/` contains no checked-in application or `package.json`,
  so this check reports a skip.

## Run Local Verification

From the repository root in PowerShell:

```powershell
.\test\run-all.ps1
```

This does not need a running PostgreSQL database, S3 access, or Bedrock
network access. Backend test dependencies must be installed:

```powershell
python -m pip install -r .\backend\requirements.txt
```

## Run The Backend

Create `.env` from `.env.template` and configure:

- A PostgreSQL database where `pgvector` can be installed or is installed.
- A valid Bedrock API key and configured Bedrock region/model.
- `S3_BUCKET_NAME` and `CFPB_S3_KEY` together when S3 import endpoints are used.

Container run:

```powershell
docker compose up --build
```

Local Python run:

```powershell
python -m pip install -r .\backend\requirements.txt
python -m uvicorn app.main:app --app-dir .\backend --host 0.0.0.0 --port 8000
```

The application startup performs database/schema/permission and Bedrock
connection checks. If the database or schema is absent during an interactive
local run, it asks before creating it.

## Run Live Smoke Verification

With the backend running on port `8000`:

```powershell
.\test\run-all.ps1 -Live
```

For a different port or host:

```powershell
.\test\run-all.ps1 -Live -BaseUrl http://localhost:8080
```

The live check verifies `/api/health` and expected OpenAPI endpoints. S3 import
and complaint processing calls are intentionally not triggered because they
read external data or incur Bedrock processing activity.

## Run Components Individually

```powershell
.\test\backend\run-unit.ps1
.\test\infra\verify-compose.ps1
.\test\frontend\verify-frontend.ps1
.\test\backend\run-live-smoke.ps1
```
