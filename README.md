# CustomerPulse

Integration branch for testing the CustomerPulse frontend, FastAPI backend, AWS infrastructure configuration, and shared API contract together before promotion to `main`.

## Integrated Services

- `frontend/`: Next.js dashboard and controlled CFPB S3 import UI.
- `backend/`: FastAPI service with PostgreSQL storage, Bedrock enrichment, pgvector RAG, human-review routing, persisted batch jobs, analytics, duplicates, feedback, exports, and SLA reporting.
- `infra/`: Nginx routing and AWS/S3 deployment material.
- `shared/schema/`: shared complaint response contract.

## Local Integration Setup

1. Copy `.env.template` to `.env` and provide real PostgreSQL, AWS Bedrock, and private S3 configuration values.
2. Install backend requirements, create/update the PostgreSQL schema, and cache the configured MiniLM embedding model:

Windows PowerShell:

```powershell
backend\scripts\setup_backend.ps1 -VerifyEmbedding
```

Linux/macOS:

```bash
VERIFY_EMBEDDING=true bash backend/scripts/setup_backend.sh
```

If you only want database setup and want to skip Bedrock during local infra work:

```powershell
backend\scripts\setup_backend.ps1 -SkipBedrock -VerifyEmbedding
```

3. Start the integrated stack:

```bash
docker compose up --build
```

Open the application through Nginx at `http://localhost`. Nginx serves the frontend and forwards `/api`, `/docs`, `/openapi.json`, and `/ws` to the backend.

Backend writes and dashboard login use credentials configured through
`AUTH_USERS_JSON`. See `backend/API_CONTRACT_PHASE2.md` for the frozen
review, RAG, search, batch-job, analytics, duplicate, feedback, export, and
SLA contract supplied to the frontend owner.

The backend uses `sentence-transformers` plus `all-MiniLM-L6-v2` for local
embeddings and `reportlab` for PDF exports. The setup scripts deliberately
install those requirements, download/cache the MiniLM model, and verify it
returns 384-dimensional embeddings before deployment. Docker deployments keep
the cache in the `sentence-transformer-cache` volume.

Run the backend verification suite before pushing or deploying:

```powershell
backend\scripts\run_backend_checks.ps1
```

or:

```bash
bash backend/scripts/run_backend_checks.sh
```

## Branch Flow

Feature branches are integrated into `dev` through a reviewed pull request. After tester approval on `dev`, a separate reviewed pull request can promote the tested result to `main`.

## Security

Never commit `.env`, database passwords, Bedrock keys, AWS credentials, or generated dependency/build directories.
The active deployment deliberately uses one backend instance for in-process
WebSocket events and its PostgreSQL-backed job worker; Redis is not included.
For local development without Docker, run the backend on port `8000` and the
frontend on port `3000`:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
cd frontend
npm run dev
```
