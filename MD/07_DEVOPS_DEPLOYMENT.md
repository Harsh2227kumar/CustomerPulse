# DevOps Deployment Tracker

## Implemented

- Root `docker-compose.yml`.
- Backend container build from `backend/Dockerfile`.
- Redis service for Phase 2 pub/sub readiness.
- Nginx reverse proxy for `/api`, `/docs`, `/openapi.json`, and `/ws`.
- EC2 Docker bootstrap script.
- EC2 deploy script.
- Deployment notes.

## Phase 1: Local Development With Shared Services

The initial working setup is local backend plus local frontend, connected to real external services:

- PostgreSQL stores real complaints and AI enrichment results.
- OpenAI provides AI inference.
- Local backend reads `.env` values.
- Redis can stay disabled locally until live pub/sub work begins.
- EC2 hosting is not required until backend and frontend are ready to run together in the cloud.

Phase 1 priorities:

- Confirm database connectivity from the local machine.
- Let backend startup or `python -m app.db.setup` create/verify the database schema.
- Add `OPENAI_API_KEY` and select `OPENAI_MODEL`.
- Validate OpenAI support in the backend AI client once the key is available.
- Run `/api/health` and one real `POST /api/process` locally.

## Phase 2: Cloud Backend Hosting

When the backend is stable and the frontend needs a hosted API, move to EC2 or another host:

- Host Docker Compose services.
- Backend runs as a Docker container.
- Redis runs as a Docker container initially.
- Nginx is the public HTTP entrypoint.
- PostgreSQL remains managed externally.
- OpenAI is called using deployment-provided secrets.

Recommended initial EC2 machine:

- Ubuntu.
- `t3.medium`.
- 2 vCPU, 4 GB RAM.
- 20-30 GB gp3 disk.
- No GPU needed because OpenAI runs inference externally.

Use `t3.large` later if local embeddings or heavier `sentence-transformers` workloads become important.

## Environment Rules

- Real secrets belong only in `.env`, GitHub Actions secrets, AWS Secrets Manager, AWS Systems Manager Parameter Store, or managed runtime environment injection.
- `.env.template` documents required values but must not contain real secrets.
- Database access should not be publicly open for production.
- During local Phase 1, allow only trusted developer IPs.
- Nginx should be the public HTTP entrypoint on EC2.

## Phase 2 Environment

Create `.env` from `.env.template` on the host and fill:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/customerpulse
DATABASE_ADMIN_URL=

AI_PROVIDER=openai
OPENAI_API_KEY=replace_with_real_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
S3_BUCKET_NAME=

CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://your-frontend-domain.com
REDIS_URL=redis://redis:6379/0
ENVIRONMENT=production
DEBUG=false

BACKEND_PORT=8000
HTTP_PORT=80
```

## Pending For Sparsh

- Validate backend OpenAI client implementation after the key is ready.
- Add HTTPS/TLS once domain is available.
- Add frontend container after Atharva's frontend folder is merged.
- Add CI/CD workflow after branch protection is finalized.
- Add CloudWatch or external log monitoring if time allows.
- Consider ElastiCache for Redis if production reliability becomes necessary.
