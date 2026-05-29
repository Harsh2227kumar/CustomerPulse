# Backend RAG And Review Deployment Upgrade

This guide is the infrastructure checklist for deploying the Harsh-owned
backend capabilities: human review, audit history, local MiniLM embeddings,
RDS pgvector retrieval, full-text search, background jobs, and API-key role
protection.

## Architecture And Ownership

The current project uses three AWS accounts:

| Account | Owned Services | Backend Requirement |
| --- | --- | --- |
| Account 1 | Amazon RDS for PostgreSQL | Store complaints, audit runs, jobs, embeddings, and indexes. |
| Account 2 | Amazon Bedrock | Generate enrichment output and grounded draft actions. |
| Account 3 | S3, Glue, Athena, EC2 backend | Query source complaints and run the application. |

For this delivery, run exactly one backend application instance. WebSocket
subscribers are held in memory and one application process executes PostgreSQL
jobs. Multi-instance deployment requires a future event fanout and distributed
job ownership design; Redis is not part of this cycle.

## 1. RDS PostgreSQL Upgrade In Account 1

### Engine And Extension Requirement

The application uses `VECTOR(384)` plus an HNSW cosine index. Choose an RDS for
PostgreSQL engine release that supports pgvector HNSW. For a new environment,
prefer a current supported release that includes pgvector `0.8.0` or later,
such as PostgreSQL `16.5` or later where available in the selected Region.

Before changing an existing database:

1. Take an RDS snapshot.
2. Confirm the backend EC2 security group can reach only TCP `5432` on the RDS
   security group through private networking or a tightly scoped temporary
   rule.
3. Connect as a database owner permitted to create trusted extensions.
4. Check extension availability:

   ```sql
   SHOW rds.extensions;
   ```

5. Enable and confirm pgvector:

   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
   ```

### Application Schema Upgrade

The backend setup flow creates or reconciles:

- Review metadata columns on `complaints`.
- `complaint_processing_runs`.
- `processing_jobs` and `processing_job_items`.
- `embedding vector(384)` and embedding provenance fields.
- Generated full-text `search_vector`.
- GIN full-text index.
- HNSW cosine index.

From the backend host, run setup once with the production environment loaded:

```powershell
$env:PYTHONPATH='backend'
python -m app.db.setup --yes --verify-embedding
```

For a database that already received an earlier Phase 2 schema before weighted
full-text search was added, run setup during a maintenance window so the
generated `search_vector` column and its GIN index are rebuilt. Then verify:

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';

SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'complaints'
  AND indexname IN (
    'ix_complaints_embedding_hnsw_cosine',
    'ix_complaints_search_vector_gin'
  );

SELECT to_regclass('public.complaint_processing_runs'),
       to_regclass('public.processing_jobs'),
       to_regclass('public.processing_job_items');
```

### RDS Operational Settings

Enable these before submission deployment:

- Encryption at rest with a KMS key.
- Automated backups and a retention period suitable for the demonstration.
- Deletion protection for the submission database.
- CloudWatch export for PostgreSQL/error logs where permitted.
- A database user for the backend with application DML and schema-setup rights
  only as required; do not use a master password in the running application.
- A maintenance window for schema/index creation, because HNSW creation on
  large imported data can consume CPU and memory.

Do not bulk-import the full CFPB source and build embeddings immediately before
the demonstration. Import a bounded subset, backfill it, and measure query
latency first.

## 2. Embedding Model Deployment On Account 3 EC2

The backend calculates embeddings locally with:

```text
all-MiniLM-L6-v2 -> exactly 384 float dimensions
```

The Python package is not sufficient on its own; the model weights must also be
available on the host. Choose one deployment approach:

1. Build the model cache into the backend container image in CI.
2. Download the model once during EC2 setup while controlled outbound internet
   access is permitted, then retain the Docker Hugging Face cache volume.
3. Package a pre-approved cached model artifact and copy it to the persistent
   host volume during deployment.

The repository includes the cache/setup commands needed on a fresh machine:

```bash
python backend/scripts/download_embedding_model.py --model all-MiniLM-L6-v2
```

or, for full backend readiness:

```bash
VERIFY_EMBEDDING=true bash backend/scripts/setup_backend.sh
```

Docker deployments run:

```bash
docker compose run --rm backend python -m app.db.setup --yes --verify-embedding
```

This creates/reconciles schema and fails if `all-MiniLM-L6-v2` is not
downloadable/cacheable or does not return 384 dimensions.

For the Docker deployment, preserve the configured cache volume:

```text
sentence-transformer-cache:/root/.cache/huggingface
```

Production environment:

```env
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_VERIFY_ON_STARTUP=true
PRELOAD_EMBEDDING_MODEL=false
SIMILARITY_THRESHOLD=0.60
SIMILAR_CASE_LIMIT=3
```

`EMBEDDING_VERIFY_ON_STARTUP=true` makes deployment fail immediately if model
weights are unavailable or the model does not produce `384` dimensions.

## 3. S3 Data And Athena Results In Account 3

Use separate prefixes:

```text
s3://customerpulse-cfpb-data/raw/cfpb/
s3://customerpulse-cfpb-data/processed/cfpb_parquet_glue/
s3://customerpulse-cfpb-data/athena/results/
```

Required deployment controls:

- Block all public S3 access.
- Enable bucket encryption, preferably SSE-KMS with the EC2 role permitted to
  decrypt only required source/result objects.
- Enable bucket versioning for source and converted data if cost permits.
- Add an S3 lifecycle policy to expire Athena result objects after an
  appropriate audit/debug interval.
- Restrict EC2 role reads to source/processed prefixes and Athena result
  reads/writes to the results prefix.

The application calls Athena for preview/filter/import selection. It does not
need permission to modify the raw CFPB data from the backend runtime role.

## 4. Glue Data Catalog And Conversion Job In Account 3

Glue owns the Parquet conversion/catalog layer used by Athena. Before deploy:

1. Confirm the Glue job outputs Parquet to the configured processed prefix.
2. Confirm the table contains the complaint identifiers and narrative fields
   required by import.
3. Confirm the database/table names match:

   ```env
   ATHENA_DATABASE=customerpulse_data
   ATHENA_TABLE=cfpb_parquet
   ```

4. After updating partitioned output, update partitions using the crawler or:

   ```sql
   MSCK REPAIR TABLE customerpulse_data.cfpb_parquet;
   ```

5. Give the EC2 runtime role read-only Glue catalog permissions needed for
   Athena query planning: catalog, database, table, and partition reads.

If the Glue catalog is moved into another AWS account, explicitly configure
cross-account Glue catalog permission and S3 permission; catalog access alone
does not grant access to table data stored in S3.

## 5. Athena Workgroup In Account 3

Create a dedicated workgroup such as:

```text
customerpulse-backend
```

Then update:

```env
ATHENA_WORKGROUP=customerpulse-backend
ATHENA_OUTPUT_LOCATION=s3://customerpulse-cfpb-data/athena/results/
ATHENA_QUERY_TIMEOUT_SECONDS=90
```

Configure the workgroup to:

- Enforce the query-result S3 location.
- Enforce result encryption.
- Publish query metrics to CloudWatch.
- Apply a per-query data scan limit appropriate to the dataset.

EC2 role permissions must include:

- Athena query start/status/result actions for the selected workgroup.
- Glue read access to the configured catalog/database/table/partitions.
- Both `glue:GetPartition` and `glue:GetPartitions` for partitioned Athena
  tables.
- S3 read access to Parquet input.
- S3 write/read access to the Athena result prefix.
- KMS permissions if either input or output uses a customer-managed key.

## 6. Bedrock In Account 2

The current backend sends an Amazon Bedrock API key as a bearer authorization
header and stores model/Region settings in environment variables:

```env
AI_PROVIDER=bedrock
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6
BEDROCK_API_KEY=loaded_from_secret_storage
AI_MAX_RETRIES=2
AI_TIMEOUT_SECONDS=30
```

### Submission-Safe Configuration

For the current code path:

1. Confirm model access is enabled in Account 2 and in `BEDROCK_REGION`.
2. Create a narrowly scoped Bedrock API key for the demonstration.
3. Store it in AWS Secrets Manager rather than in Git, AMI user data, or a
   committed `.env` file.
4. Permit the Account 3 EC2 role to retrieve only that secret, or copy a
   controlled deployment secret into Account 3 Secrets Manager.
5. Rotate/delete the demonstration key after the event.

### Production Upgrade

AWS recommends short-term credentials for higher-security production
environments. The current `BedrockClient` is API-key based; before a real
production release, change it to an AWS SDK/SigV4 client using an EC2 instance
role or an Account 2 role assumed by Account 3 EC2. That change removes the
long-lived Bedrock key from application configuration and enables ordinary IAM
policy/CloudTrail governance.

## 7. Backend Secrets And API Roles

These values are secrets:

- `DATABASE_URL` password.
- `BEDROCK_API_KEY` while the API-key implementation remains in use.
- `AUTH_PRINCIPALS_JSON` bearer keys.

Store them in Secrets Manager and inject them into the container environment at
deployment time. Rotate all sample keys in documentation before a hosted demo.

Use at least:

```json
{
  "agent-key": {"actor": "demo-agent", "role": "agent"},
  "manager-key": {"actor": "demo-manager", "role": "manager"}
}
```

Do not expose manager credentials in frontend source. The demo frontend may
read public complaint views; protected writes must carry a bearer credential
from a controlled operator flow.

## 8. EC2 Runtime And Networking

For the current single-instance application:

- Attach an EC2 instance profile for S3, Glue, Athena, CloudWatch, KMS, and
  Secrets Manager access required by this backend only.
- Keep RDS private; allow inbound database access from the backend security
  group rather than the internet.
- Terminate HTTPS at an Application Load Balancer or Nginx with a valid
  certificate before public access.
- Run one backend container so WebSocket events and the in-process job worker
  are consistent.
- Preserve the embedding cache volume across container restarts.
- Use a restart policy and CloudWatch log shipping for worker/process failures.

Required hosted environment additions:

```env
ENVIRONMENT=production
DEBUG=false
EMBEDDING_VERIFY_ON_STARTUP=true
BATCH_PROCESS_LIMIT=50
EMBEDDING_BACKFILL_LIMIT=100
JOB_WORKER_POLL_SECONDS=1
```

## 9. Monitoring And Audit Verification

Create alarms or operational checks for:

- EC2/container health endpoint failure.
- RDS CPU/storage/connections and backup failure.
- Athena failed queries or unexpectedly high scanned bytes.
- Bedrock call errors/timeouts.
- Repeated failed processing job items.
- Growing `human_review` queue without manager resolution.

The application audit evidence to demonstrate is:

```sql
SELECT status_outcome, trigger_reason, initiated_by, error_category, created_at
FROM complaint_processing_runs
ORDER BY created_at DESC
LIMIT 20;

SELECT status, count(*)
FROM processing_job_items
GROUP BY status;
```

## 10. Deployment Acceptance Sequence

Perform these checks in order:

1. Restore/test from an RDS snapshot or create the deployment database.
2. Enable `vector`, run backend schema setup, and verify GIN/HNSW indexes.
3. Confirm S3 encryption, prefixes, lifecycle, and EC2 IAM access.
4. Run the Glue conversion/crawler and an Athena query in the application
   workgroup.
5. Provision the embedding model cache and start the backend with startup
   embedding verification enabled.
6. Verify `/api/health` and public complaint listing.
7. Preview and import one complaint using a manager credential.
8. Enqueue a small embedding backfill job and verify `embedded_at`.
9. Process a second similar complaint and inspect stored similar-case
   evidence.
10. Force or submit a review-triggering case and approve it with the manager
    credential.
11. Restart the backend while a test job is marked running and confirm the
    item is exposed as retryable rather than silently lost.
12. Rotate temporary credentials after the hosted demonstration.

## Official AWS References

- RDS PostgreSQL extension administration:
  https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Extensions.html
- RDS PostgreSQL pgvector/HNSW support:
  https://aws.amazon.com/about-aws/whats-new/2024/11/amazon-rds-for-postgresql-pgvector-080/
- Amazon Bedrock API keys and production credential guidance:
  https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html
- Athena and Glue Data Catalog permissions:
  https://docs.aws.amazon.com/athena/latest/ug/fine-grained-access-to-glue-resources.html
- Athena encryption:
  https://docs.aws.amazon.com/athena/latest/ug/encryption.html
- AWS Secrets Manager:
  https://docs.aws.amazon.com/secretsmanager/
