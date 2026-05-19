# Environment Setup

CustomerPulse Phase 1 runs the backend and frontend locally while using PostgreSQL for real complaint data and OpenAI for AI enrichment.

Copy `.env.template` to `.env` locally and fill real values. Never commit `.env`.

## Phase 1 Local Backend Setup

Use this setup while developing locally:

- Backend: local FastAPI server.
- Frontend: local dev server, usually `http://localhost:5173` or `http://localhost:3000`.
- Database: PostgreSQL. AWS RDS is still fine for the shared team database.
- AI: OpenAI API using `OPENAI_API_KEY`.
- Redis: optional for now, reserved for Phase 2 WebSocket/pub-sub work.

## Required Values

- `DATABASE_URL`: async PostgreSQL URL.
  - Use `postgresql+asyncpg://USER:PASSWORD@HOST:5432/customerpulse`.
  - If using AWS RDS, make sure the RDS security group allows your current local public IP on port `5432`.
- `DATABASE_ADMIN_URL`: optional admin/default PostgreSQL URL used only when the backend needs to create the target database.
  - Leave blank if the same user can connect to the default `postgres` database.
  - Set it when the app user can use `customerpulse` but cannot create databases.
- `AI_PROVIDER`: set to `openai`.
- `OPENAI_API_KEY`: your OpenAI API key.
- `OPENAI_MODEL`: model used for complaint enrichment. Default: `gpt-4o-mini`.
- `CORS_ORIGINS`: comma-separated frontend origins.
- `S3_BUCKET_NAME`: optional for Harsh's backend path, required when the CFPB raw JSON archive path is enabled.

Recommended Phase 1 `.env` shape:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/customerpulse
DATABASE_ADMIN_URL=

AI_PROVIDER=openai
OPENAI_API_KEY=replace_with_real_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
S3_BUCKET_NAME=

CORS_ORIGINS=http://localhost:5173,http://localhost:3000
REDIS_URL=
ENVIRONMENT=development
DEBUG=false

AI_MAX_RETRIES=2
AI_TIMEOUT_SECONDS=30
VECTOR_DIMENSIONS=384
BACKEND_PORT=8000
HTTP_PORT=80
```

## Automatic Database Setup

On backend startup, the app checks:

- PostgreSQL connection.
- Whether the `customerpulse` database exists.
- Whether the `vector` extension exists.
- Whether the `complaints` table and indexes exist.
- Whether the configured user can insert, select, update, and delete complaint rows.
- Whether OpenAI can be invoked with the configured model.

If the database or schema is missing, the backend asks in the terminal before creating it.

Manual setup command:

```bash
cd backend
python -m app.db.setup
```

## OpenAI Setup Checklist

1. Create or choose an OpenAI API key.
2. Put the key only in local `.env` or managed deployment secret storage.
3. Set `AI_PROVIDER=openai`.
4. Set `OPENAI_MODEL=gpt-4o-mini` unless the team agrees to another model.
5. Run `python -m app.db.setup` to verify database and OpenAI readiness.

## Optional Values

- `OPENAI_BASE_URL`: leave blank unless routing through an OpenAI-compatible gateway.
- `REDIS_URL`: keep empty locally for Phase 1. Use `redis://redis:6379/0` in Docker/EC2 later.
- `VECTOR_DIMENSIONS`: defaults to `384`.
- `AI_MAX_RETRIES`: defaults to `2`.
- `AI_TIMEOUT_SECONDS`: defaults to `30`.
- `S3_BUCKET_NAME`: needed for the CFPB raw JSON archive path.

## Current Code Note

The backend uses the OpenAI Python SDK and the Responses API with structured JSON output. It keeps the existing prompt, parser, validation, and complaint processing pipeline.
