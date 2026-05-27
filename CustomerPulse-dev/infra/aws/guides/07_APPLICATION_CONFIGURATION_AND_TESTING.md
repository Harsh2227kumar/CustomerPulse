# Application Configuration And Testing

This guide connects the working AWS services to the CustomerPulse backend and
frontend without loading all complaints into PostgreSQL.

## Required Code Branches

| Application Part | Feature Branch |
| --- | --- |
| Backend filtered S3/Athena import API | `feature/cfpb-s3-import-api` |
| Frontend S3 Complaint Import page | `feature/frontend-dashboard` |
| AWS guides/templates | `feature/s3-cross-account-setup` |

The backend and frontend changes must be present in the application integration
branch before running the whole feature together.

## Backend `.env` Settings

Keep `.env` private and uncommitted. Configure:

```env
# Account 1: PostgreSQL RDS
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@RDS_HOST:5432/customerpulse
DATABASE_ADMIN_URL=

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
