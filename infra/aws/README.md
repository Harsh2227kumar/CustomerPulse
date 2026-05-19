# AWS EC2 Deployment Notes

## One-Time EC2 Setup

Run on a fresh Ubuntu EC2 instance:

```bash
bash infra/aws/ec2-bootstrap.sh
```

Log out and back in after Docker group membership is added.

## Required Security Group Ports

- `22`: SSH, restricted to trusted IPs.
- `80`: HTTP for Nginx.
- `443`: HTTPS later, after TLS is configured.

Do not expose PostgreSQL publicly. The backend should reach AWS RDS through private networking or restricted RDS security group rules.

## Required Environment

Create `.env` from `.env.template` on EC2 and fill:

- `DATABASE_URL`
- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL`
- `CORS_ORIGINS`
- `REDIS_URL=redis://redis:6379/0`

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
