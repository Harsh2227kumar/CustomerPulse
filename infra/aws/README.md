# AWS Deployment Notes

CustomerPulse is being built in two stages:

- Phase 1: run backend and frontend locally, while using PostgreSQL for real complaint data and OpenAI for AI processing.
- Phase 2: host backend on AWS EC2 with Docker Compose, Nginx, Redis, and a managed PostgreSQL database.

## Phase 1: Local Backend With PostgreSQL And OpenAI

Services needed now:

- PostgreSQL database. AWS RDS is acceptable for the shared team database.
- OpenAI API key.

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

OpenAI:

- Create or choose an OpenAI API key.
- Put it in `.env`, never in git:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=replace_with_real_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
S3_BUCKET_NAME=
```

`OPENAI_BASE_URL` should stay blank unless the team intentionally uses an OpenAI-compatible gateway.

## Multiple Cloud Accounts

Using multiple cloud accounts is possible, but it adds complexity.

Simplest setup:

- PostgreSQL, hosting, and deployment secrets are managed by the same team owner.

If accounts are split:

- One account may hold the database.
- Another account may host EC2.
- EC2 must be allowed to connect to the database across accounts.
- Networking may require VPC peering, private connectivity, or tightly restricted public database rules.

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
- `AI_PROVIDER=openai`.
- `OPENAI_API_KEY`.
- `OPENAI_MODEL`.
- `CORS_ORIGINS`.
- `REDIS_URL=redis://redis:6379/0`.

Put `OPENAI_API_KEY` in managed deployment secret storage when possible.

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
