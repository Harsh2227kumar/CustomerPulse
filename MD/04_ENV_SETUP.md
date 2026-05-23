# Environment Setup

CustomerPulse Phase 1 runs the backend and frontend locally while using PostgreSQL for real complaint data and AWS Bedrock Claude for AI enrichment.

Copy `.env.template` to `.env` locally and fill real values. Never commit `.env`.

## Phase 1 Local Backend Setup

Use this setup while developing locally:

- Backend: local FastAPI server.
- Frontend: local dev server, usually `http://localhost:5173` or `http://localhost:3000`.
- Database: PostgreSQL. AWS RDS is still fine for the shared team database.
- AI: AWS Bedrock API-key Messages endpoint using `BEDROCK_API_KEY`.
- Redis: optional for now, reserved for Phase 2 WebSocket/pub-sub work.

## Required Values

- `DATABASE_URL`: async PostgreSQL URL.
  - Use `postgresql+asyncpg://USER:PASSWORD@HOST:5432/customerpulse`.
  - If using AWS RDS, make sure the RDS security group allows your current local public IP on port `5432`.
- `DATABASE_ADMIN_URL`: optional admin/default PostgreSQL URL used only when the backend needs to create the target database.
  - Leave blank if the same user can connect to the default `postgres` database.
  - Set it when the app user can use `customerpulse` but cannot create databases.
- `AI_PROVIDER`: set to `bedrock`.
- `BEDROCK_API_KEY`: Amazon Bedrock API key from the AWS account that has Claude model access.
- `BEDROCK_REGION`: AWS region where the Bedrock API key and model access are configured.
- `BEDROCK_MODEL`: Bedrock Claude model used for complaint enrichment. Default: `global.anthropic.claude-sonnet-4-6`.
- `CORS_ORIGINS`: comma-separated frontend origins.
- `S3_BUCKET_NAME`: private bucket containing the CFPB CSV or CSV ZIP used for controlled import.
- `CFPB_S3_KEY`: object key such as `raw/cfpb/complaints.csv.zip`.
- `AWS_REGION`: S3 bucket region. The backend AWS identity must have cross-account read permission when the bucket is owned by another account.

Recommended Phase 1 `.env` shape:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/customerpulse
DATABASE_ADMIN_URL=

AI_PROVIDER=bedrock
BEDROCK_API_KEY=replace_with_user2_bedrock_key
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6
BEDROCK_BASE_URL=
S3_BUCKET_NAME=
CFPB_S3_KEY=raw/cfpb/complaints.csv.zip
AWS_REGION=ap-south-1

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
- Whether AWS Bedrock can be invoked with the configured model.

If the database or schema is missing, the backend asks in the terminal before creating it.

Manual setup command:

```bash
cd backend
python -m app.db.setup
```

## Bedrock Setup Checklist

1. In the user2 AWS account, request Claude model access in Amazon Bedrock.
2. Generate an Amazon Bedrock API key in the same region.
3. Put the key only in local `.env` or managed deployment secret storage.
4. Set `AI_PROVIDER=bedrock`.
5. Set `BEDROCK_REGION` to the region where the key was generated.
6. Set `BEDROCK_MODEL` to a Claude model that user2's Bedrock account can access.
7. Run `python -m app.db.setup` to verify user1 PostgreSQL access and user2 Bedrock readiness.

## Optional Values

- `BEDROCK_BASE_URL`: leave blank to use `https://bedrock-runtime.{BEDROCK_REGION}.amazonaws.com`.
- `REDIS_URL`: keep empty locally for Phase 1. Use `redis://redis:6379/0` in Docker/EC2 later.
- `VECTOR_DIMENSIONS`: defaults to `384`.
- `AI_MAX_RETRIES`: defaults to `2`.
- `AI_TIMEOUT_SECONDS`: defaults to `30`.
- `S3_BUCKET_NAME`, `CFPB_S3_KEY`, and `AWS_REGION`: needed for the controlled S3 CSV import page.

## Current Code Note

The backend calls AWS Bedrock's API-key Messages endpoint directly with structured JSON output. The PostgreSQL account and Bedrock account are intentionally separate: `DATABASE_URL` points to user1 AWS/RDS, while `BEDROCK_*` points to user2 AWS/Bedrock.
