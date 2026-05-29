# AWS Deployment Notes

CustomerPulse is being built in two stages:

- Phase 1: run backend and frontend locally, while using PostgreSQL for real complaint data and AWS Bedrock Claude for AI processing.
- Phase 2: host the integrated frontend and backend services on AWS EC2 with Docker Compose, Nginx, and a managed PostgreSQL database.

For the three-account CFPB flow and bounded S3-to-RDS import setup, begin with
`infra/aws/guides/00_SETUP_INDEX.md`. The guide set contains repeatable console
steps for RDS, Bedrock, S3, IAM, Glue, Athena, local application configuration,
and future EC2 hosting.

## Phase 1: Local Backend With PostgreSQL And Bedrock

Services needed now:

- PostgreSQL database. AWS RDS is acceptable for the shared team database.
- Amazon Bedrock API key from the AWS account that owns Claude model access.

Database:

- Use the existing PostgreSQL instance.
- Keep the database URL in local `.env`.
- Use async SQLAlchemy format:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/postgres
DATABASE_ADMIN_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/postgres
```

- If using RDS, allow the developer machine public IP in the RDS security group on port `5432`.
- The final database segment may be `postgres` or a dedicated application database such as `customerpulse`; the backend creates tables in whichever database `DATABASE_URL` targets.
- Start the backend or run `python -m app.db.setup --yes --verify-embedding` from the `backend` folder to create/verify the database, `vector` extension, `complaints` table, indexes, permissions, and MiniLM model cache.
- Phase 2 setup also creates processing audit/job tables, a full-text GIN index, and an HNSW cosine index for `Vector(384)` retrieval.

Bedrock:

- In the user2 AWS account, request Claude model access and generate an Amazon Bedrock API key.
- Put it in `.env`, never in git:

```env
AI_PROVIDER=bedrock
BEDROCK_API_KEY=replace_with_user2_bedrock_key
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6
BEDROCK_BASE_URL=
S3_BUCKET_NAME=
```

`BEDROCK_BASE_URL` should stay blank unless the team intentionally overrides the Bedrock Runtime endpoint.

## Multiple Cloud Accounts

This project uses separate AWS accounts for database, AI, and application data/hosting.

- User1 AWS account owns PostgreSQL/RDS. Keep that in `DATABASE_URL`.
- User2 AWS account owns Amazon Bedrock Claude access. Keep that in `BEDROCK_API_KEY`, `BEDROCK_REGION`, and `BEDROCK_MODEL`.
- User3 AWS account owns the private S3 CFPB bucket during development and will own the EC2 backend host in Phase 2.

During local development, the backend uses an Account 3 local AWS profile to read S3. In Phase 2, the backend uses the IAM role attached to the Account 3 EC2 instance to read the same Account 3 bucket. The backend does not need Account 2 IAM credentials when using a Bedrock API key. RDS networking still controls whether local development or Account 3 EC2 can connect to Account 1 PostgreSQL.

## Phase 2: One-Time EC2 Setup

Run on a fresh Ubuntu EC2 instance:

```bash
bash infra/aws/ec2-bootstrap.sh
```

Log out and back in after Docker group membership is added.

Recommended EC2 size:

- `t3.medium` for initial backend hosting.
- 20-30 GB gp3 disk.
- No GPU needed.

## Required Security Group Ports

- `22`: SSH, restricted to trusted IPs.
- `80`: HTTP for Nginx.
- `443`: HTTPS later, after TLS is configured.

Do not expose PostgreSQL publicly in production. The backend should reach the database through private networking or restricted security group rules.

## Required EC2 Environment

Create `.env` from `.env.template` on EC2 and fill:

- `DATABASE_URL`.
- `AI_PROVIDER=bedrock`.
- `BEDROCK_API_KEY`.
- `BEDROCK_REGION`.
- `BEDROCK_MODEL`.
- `CORS_ORIGINS`.
- `EMBEDDING_MODEL=all-MiniLM-L6-v2`, similarity and bounded batch limits.
- `EMBEDDING_VERIFY_ON_STARTUP=true` after the model cache is populated.
- `AUTH_PRINCIPALS_JSON` containing private agent/manager/admin bearer-key mappings.
- `S3_BUCKET_NAME`, `CFPB_S3_KEY`, and `AWS_REGION`.
- `CFPB_INGESTION_MODE=athena`, plus the Athena database, table, output location, and workgroup settings when querying the large Parquet-backed dataset.

Put `BEDROCK_API_KEY` in managed deployment secret storage when possible.
The local embedding model cache should be retained between deployments to avoid
re-downloading the model when batch processing begins.

## Backend Setup Scripts

Use these scripts instead of relying on manual dependency/model steps:

Windows local setup:

```powershell
backend\scripts\setup_backend.ps1 -VerifyEmbedding
```

Linux/EC2 setup:

```bash
VERIFY_EMBEDDING=true bash backend/scripts/setup_backend.sh
```

Docker/EC2 deployment:

```bash
PROJECT_DIR=$HOME/CustomerPulse BRANCH=dev bash infra/aws/deploy.sh
```

Backend-only Docker deployment:

```bash
PROJECT_DIR=$HOME/CustomerPulse BRANCH=dev bash infra/aws/deploy-backend.sh
```

Both deployment scripts run:

```bash
python -m app.db.setup --yes --verify-embedding
```

so a new machine installs dependencies, creates/reconciles schema, downloads
`all-MiniLM-L6-v2`, and fails early if the model does not produce 384 dimensions.

## Phase 2 Backend Runtime Constraints

- RAG uses processed PostgreSQL complaints only, with 384-dimensional local embeddings and thresholded pgvector retrieval.
- Human-review routing is a persisted workflow state, not an error fallback.
- Batch processing and embedding backfill run through PostgreSQL job tables and one in-process worker.
- Keep one backend event-serving instance because WebSocket subscribers are held in process memory.
- Do not add Redis to this deployment cycle.

For the final backend review/RAG deployment checklist, including RDS pgvector,
MiniLM model cache, Bedrock credentials, Athena/Glue/S3 access, monitoring, and
acceptance tests, follow
`guides/09_BACKEND_RAG_REVIEW_PRODUCTION_UPGRADE.md`.

## Deploy

```bash
PROJECT_DIR=$HOME/CustomerPulse BRANCH=dev bash infra/aws/deploy.sh
```

## Smoke Checks

```bash
docker compose ps
curl http://localhost/api/health
curl http://PUBLIC_EC2_IP/api/health
```
