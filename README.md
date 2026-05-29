# CustomerPulse

Integration branch for testing the CustomerPulse frontend, FastAPI backend, AWS infrastructure configuration, and shared API contract together before promotion to `main`.

## Integrated Services

- `frontend/`: React/Vite dashboard and controlled CFPB S3 import UI.
- `backend/`: FastAPI service with PostgreSQL storage, Bedrock enrichment, pgvector RAG, human-review routing, and persisted batch jobs.
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

Backend Phase 2 writes require bearer credentials configured through
`AUTH_PRINCIPALS_JSON`. See `backend/API_CONTRACT_PHASE2.md` for the frozen
review, RAG, search, and batch-job contract supplied to the frontend owner.

The backend uses `sentence-transformers` plus `all-MiniLM-L6-v2`. The setup
scripts deliberately download/cache that model and verify it returns
384-dimensional embeddings before deployment. Docker deployments keep the cache
in the `sentence-transformer-cache` volume.

## Branch Flow

Feature branches are integrated into `dev` through a reviewed pull request. After tester approval on `dev`, a separate reviewed pull request can promote the tested result to `main`.

## Security

Never commit `.env`, database passwords, Bedrock keys, AWS credentials, or generated dependency/build directories.
The active deployment deliberately uses one backend instance for in-process
WebSocket events and its PostgreSQL-backed job worker; Redis is not included.
