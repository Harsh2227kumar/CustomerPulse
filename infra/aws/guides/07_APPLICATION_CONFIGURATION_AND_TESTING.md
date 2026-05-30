# Application Configuration And Testing

This guide connects the working AWS services to the CustomerPulse backend and
frontend without loading all complaints into PostgreSQL.

## Required Code Branches

| Application Part | Feature Branch |
| --- | --- |
| Backend filtered S3/Athena import API | `feature/cfpb-s3-import-api` |
| Frontend dashboard, import, and Operations page | integrated from `feature/frontend-dashboard` into `feature/cfpb-s3-import-api` |
| AWS guides/templates | `feature/s3-cross-account-setup` |

The backend and frontend changes must be present in the application integration
branch before running the whole feature together.

## Backend `.env` Settings

Keep `.env` private and uncommitted. Configure:

```env
# Account 1: PostgreSQL RDS
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@RDS_HOST:5432/postgres
DATABASE_ADMIN_URL=postgresql+asyncpg://USER:PASSWORD@RDS_HOST:5432/postgres

# Account 2: Amazon Bedrock Claude
AI_PROVIDER=bedrock
BEDROCK_API_KEY=replace_with_account2_bedrock_key
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6
BEDROCK_BASE_URL=

# Account 3: S3, Glue-created Parquet, Athena
S3_BUCKET_NAME=customerpulse-cfpb-data
CFPB_S3_KEY=raw/cfpb/complaints.csv
AWS_REGION=ap-south-1
CFPB_INGESTION_MODE=athena
ATHENA_DATABASE=customerpulse_data
ATHENA_TABLE=cfpb_parquet
ATHENA_OUTPUT_LOCATION=s3://customerpulse-cfpb-data/athena/results/
ATHENA_WORKGROUP=primary
ATHENA_QUERY_TIMEOUT_SECONDS=90

CORS_ORIGINS=http://localhost:5173,http://localhost:3000
ENVIRONMENT=development
DEBUG=false
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_VERIFY_ON_STARTUP=false
SIMILARITY_THRESHOLD=0.60
SIMILAR_CASE_LIMIT=3
BATCH_PROCESS_LIMIT=50
EMBEDDING_BACKFILL_LIMIT=100
JOB_WORKER_POLL_SECONDS=1
AUTH_PRINCIPALS_JSON={"replace-manager-key":{"actor":"demo-manager","role":"manager"},"replace-agent-key":{"actor":"demo-agent","role":"agent"}}
```

## Local AWS Credentials

For local development, boto3 reads Account 3 backend-reader credentials from:

```text
C:\Users\ACER\.aws\credentials
C:\Users\ACER\.aws\config
```

These files must contain credentials for the IAM user in
`CustomerPulseS3Readers`, not the uploader user.

## Safe Verification Order

Use this order so errors are discovered before anything is inserted into RDS.

### 1. Check S3 Object

In S3 Console, confirm:

```text
s3://customerpulse-cfpb-data/raw/cfpb/complaints.csv
```

exists and is private.

### 2. Check Glue Output

In S3 Console, confirm:

```text
s3://customerpulse-cfpb-data/processed/cfpb_parquet_glue/
```

contains partition folders and Parquet files.

### 3. Check Athena Manually

In Athena run:

```sql
SELECT product, COUNT(*)
FROM customerpulse_data.cfpb_parquet
GROUP BY product
ORDER BY COUNT(*) DESC
LIMIT 20;
```

Then:

```sql
SELECT product, issue, company, complaint_id
FROM customerpulse_data.cfpb_parquet
WHERE product_partition = 'Credit card or prepaid card'
LIMIT 5;
```

Both steps are read-only.

### 4. Start Backend And Check Filter Options

Start the backend after `.env` and Account 3 local credentials are configured.
Open the frontend S3 Complaint Import page.

The page should load actual Athena-derived options such as:

```text
Credit card or prepaid card
```

Do not click import yet.

### 5. Use Preview

Choose:

| Filter | Example |
| --- | --- |
| Product category | `Credit card or prepaid card` |
| Maximum complaints | `5` |

Click **Preview**. Preview should show a small matching list and must not save
anything to PostgreSQL.

### 6. Make A Small Import Test

Only after preview works, click **Import to PostgreSQL** with a very small
number, for example `1` or `5`.

The success screen should report saved complaints and show an operation log.
Verify the imported rows in the dashboard before selecting a larger amount.

### 7. Verify Review, RAG, Jobs, And Reporting

1. Call protected import/process/job actions with a bearer key configured as
   `manager` or `agent` according to `backend/API_CONTRACT_PHASE2.md`.
2. Run embedding backfill for a small imported selection before demonstrating
   similar-case retrieval.
3. Confirm a completed complaint stores its embedding model and that later
   processing returns only thresholded completed similar cases.
4. Trigger a low-confidence or weak-output case and confirm it returns
   `human_review`, emits `human_review_required`, and can be approved or
   resolved by a manager key.
5. Keep demo process jobs at or below 50 complaints and backfill jobs at or
   below 100 complaints.
6. Before a hosted demonstration, cache the MiniLM model on the backend host
   and set `EMBEDDING_VERIFY_ON_STARTUP=true` so an absent model fails startup
   rather than the first user action.
7. Verify open reporting routes: `/api/analytics/product-summary` and
   `/api/sla/summary`.
8. Verify manager-protected reporting/actions with a bearer key:
   `/api/exports/complaints/csv`, `/api/exports/complaints/pdf`,
   `/api/feedback`, and `/api/duplicates/detect`.
9. In the frontend, open **Operations**, save a manager/admin bearer key from
   `AUTH_PRINCIPALS_JSON`, and verify:
   - complaint detail loads for a selected imported complaint,
   - review approve/resolve/rerun buttons call the backend,
   - process and embedding-backfill jobs create PostgreSQL job records,
   - analytics/SLA panels load backend responses,
   - feedback, duplicate detection, and export buttons require and use the
     saved bearer key.

Backend setup command:

```powershell
cd backend
python -m app.db.setup --yes --verify-embedding
```

This downloads/caches `all-MiniLM-L6-v2` and validates 384-dimensional output.
It also installs the current Python requirements, including `reportlab` for PDF
exports when run through `backend/scripts/setup_backend.*`.

Backend verification command:

```powershell
backend\scripts\run_backend_checks.ps1
```

## Routine Full-File Update Process

When you later receive a fresh complete CSV:

1. Upload it to the same S3 raw key.
2. Run the Glue conversion job again.
3. Run in Athena:

   ```sql
   MSCK REPAIR TABLE customerpulse_data.cfpb_parquet;
   ```

4. Verify one Athena query.
5. Open the frontend page and use its filters and import limit.

## Rules

- Never import the entire source unless that is an intentional database
  decision.
- Never add AWS keys or database URLs to Git.
- Preview before import.
- Begin with one to five records after infrastructure changes.
- Run a single backend instance for WebSocket delivery and the in-process job worker; do not add Redis.
- Rerun backend schema setup after pulling Atharva reporting changes so
  `agent_feedback`, `duplicate_groups`, and `duplicate_members` exist.
- Complete the hosted-service upgrade checklist in
  `09_BACKEND_RAG_REVIEW_PRODUCTION_UPGRADE.md` before a deployment review.
