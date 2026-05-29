# Phase 2 EC2 Backend Hosting - Account 3

This is the later stable-hosting plan. During development the backend may run
on a laptop. In Phase 2, host the backend on EC2 in Account 3, beside S3,
Glue, and Athena.

## Target Architecture

```text
Account 3 EC2 backend
    -> Account 3 Athena/S3 using EC2 IAM role
    -> Account 1 RDS PostgreSQL through restricted networking
    -> Account 2 Bedrock using the chosen production credential approach
```

## Important Credential Rule

Do not copy local Account 3 IAM access keys to EC2. Attach an IAM role to the
EC2 instance. AWS supplies temporary credentials to applications on the
instance.

## Create The EC2 Backend Role

1. In **Account 3**, open **IAM > Roles > Create role**.
2. Select **AWS service**.
3. Select use case **EC2**.
4. Name the role:

   ```text
   CustomerPulseBackendEc2Role
   ```

5. Attach an S3/Athena policy equivalent to
   `CustomerPulseAthenaRuntime` in
   `04_IAM_AND_LOCAL_CREDENTIALS_ACCOUNT3.md`.
6. Include read permission for:

   ```text
   s3://customerpulse-cfpb-data/processed/cfpb_parquet_glue/*
   ```

7. Include Athena result read/write permission for:

   ```text
   s3://customerpulse-cfpb-data/athena/results/*
   ```

8. Do not create an access key for the role.

## Launch The EC2 Instance

1. Open **EC2 > Instances > Launch instances**.
2. Choose the Account 3 region appropriate to application hosting, preferably
   the same current data region:

   ```text
   ap-south-1
   ```

3. Instance name:

   ```text
   customerpulse-backend
   ```

4. Select an Ubuntu LTS AMI.
5. Initial instance size suggestion:

   ```text
   t3.medium
   ```

6. Configure a key pair or Session Manager administration approach.
7. Under advanced details, attach IAM instance profile:

   ```text
   CustomerPulseBackendEc2Role
   ```

8. Use a security group with:

| Port | Purpose | Source |
| --- | --- | --- |
| `22` | SSH only if used | Trusted administrator IP only |
| `80` | HTTP | Public only if serving the app over HTTP |
| `443` | HTTPS | Public when TLS is configured |

Do not open port `5432` on EC2 for public database service.

## Connect Account 3 EC2 To Account 1 RDS

RDS remains in Account 1, so networking must be set explicitly.

For temporary testing, allow only the EC2 outbound/source address through a
restricted Account 1 RDS security rule. For stable hosting, use controlled
cross-account private networking and restricted security groups.

The backend must reach:

```text
ACCOUNT1_RDS_HOST:5432
```

## EC2 Environment Settings

The EC2 backend environment includes RDS, Bedrock, and Athena configuration:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@ACCOUNT1_RDS_HOST:5432/postgres

AI_PROVIDER=bedrock
BEDROCK_API_KEY=replace_with_account2_production_credential_if_still_used
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6

S3_BUCKET_NAME=customerpulse-cfpb-data
CFPB_S3_KEY=raw/cfpb/complaints.csv
AWS_REGION=ap-south-1
CFPB_INGESTION_MODE=athena
ATHENA_DATABASE=customerpulse_data
ATHENA_TABLE=cfpb_parquet
ATHENA_OUTPUT_LOCATION=s3://customerpulse-cfpb-data/athena/results/
ATHENA_WORKGROUP=primary
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_VERIFY_ON_STARTUP=true
SIMILARITY_THRESHOLD=0.60
SIMILAR_CASE_LIMIT=3
BATCH_PROCESS_LIMIT=50
EMBEDDING_BACKFILL_LIMIT=100
JOB_WORKER_POLL_SECONDS=1
AUTH_PRINCIPALS_JSON={"replace-manager-key":{"actor":"demo-manager","role":"manager"},"replace-agent-key":{"actor":"demo-agent","role":"agent"}}
```

There are no `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` values on EC2 for
Account 3 access; boto3 uses the EC2 IAM role.

Run only one backend container for the current deployment. WebSocket
connections remain in process memory and PostgreSQL-backed batch/backfill jobs
are executed by that same instance. Redis is deliberately not required.

## Smoke Checks After Deployment

1. Start the backend service.
2. Check its health endpoint.
3. Open the frontend import page.
4. Confirm real Athena-backed filters load.
5. Preview a one-row selection.
6. Import one row and verify it in Account 1 RDS.
7. Run a small embedding-backfill job and process another row to verify RAG evidence.
8. Verify a human-review event and manager approval using configured bearer keys.
9. Follow `09_BACKEND_RAG_REVIEW_PRODUCTION_UPGRADE.md` for RDS pgvector,
   encryption, credential storage, monitoring, and acceptance checks.

The deployment script runs backend readiness before starting containers:

```bash
PROJECT_DIR=$HOME/CustomerPulse BRANCH=dev bash infra/aws/deploy.sh
```

For backend-only redeploys:

```bash
PROJECT_DIR=$HOME/CustomerPulse BRANCH=dev bash infra/aws/deploy-backend.sh
```

Both commands build the backend image, run schema setup, download/cache
`all-MiniLM-L6-v2`, and verify 384-dimensional embeddings.

## Official AWS References

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html
- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_GettingStarted.CreatingConnecting.PostgreSQL.html
