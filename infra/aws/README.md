# AWS Deployment Notes

CustomerPulse is being built in two stages:

- Phase 1: run backend and frontend locally, while using PostgreSQL for real complaint data and AWS Bedrock Claude for AI processing.
- Phase 2: host backend on AWS EC2 with Docker Compose, Nginx, Redis, and a managed PostgreSQL database.

## Phase 1: Local Backend With PostgreSQL And Bedrock

Services needed now:

- PostgreSQL database. AWS RDS is acceptable for the shared team database.
- Amazon Bedrock API key from the AWS account that owns Claude model access.

Database:

- Use the existing PostgreSQL instance.
- Keep the database URL in local `.env`.
- Use async SQLAlchemy format:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/customerpulse
DATABASE_ADMIN_URL=
```

- If using RDS, allow the developer machine public IP in the RDS security group on port `5432`.
- Start the backend or run `python -m app.db.setup` from the `backend` folder to create/verify the database, `vector` extension, `complaints` table, indexes, and permissions.

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

This project can use different AWS accounts for database and AI.

- User1 AWS account owns PostgreSQL/RDS. Keep that in `DATABASE_URL`.
- User2 AWS account owns Amazon Bedrock Claude access. Keep that in `BEDROCK_API_KEY`, `BEDROCK_REGION`, and `BEDROCK_MODEL`.

The backend does not need user2 AWS IAM credentials when using a Bedrock API key. It only needs network access to the Bedrock endpoint and the key itself. The database account remains separate; RDS networking still controls whether the backend can connect to user1 PostgreSQL.

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
- `REDIS_URL=redis://redis:6379/0`.

Put `BEDROCK_API_KEY` in managed deployment secret storage when possible.

## Deploy

```bash
PROJECT_DIR=$HOME/CustomerPulse BRANCH=feature/backend-ai-pipeline bash infra/aws/deploy.sh
```

## Smoke Checks

```bash
docker compose ps
curl http://localhost/api/health
curl http://PUBLIC_EC2_IP/api/health
```
