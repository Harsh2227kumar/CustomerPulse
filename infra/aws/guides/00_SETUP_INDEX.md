# CustomerPulse AWS Setup Handbook

This handbook records the AWS services and console steps used for the
CustomerPulse CFPB complaint import feature. Follow it again when rebuilding
the environment or helping another team member.

## Account Layout

| Account | Owns | Current Use |
| --- | --- | --- |
| Account 1 | Amazon RDS for PostgreSQL | Stores only selected imported complaints |
| Account 2 | Amazon Bedrock Claude | AI analysis after complaints are in PostgreSQL |
| Account 3 | S3, IAM, Glue, Athena; later EC2 | Stores and queries the full CFPB file |

## Data Flow

```text
Account 3
S3 raw CSV (8 GB)
    -> AWS Glue job reads multiline CSV safely
    -> S3 processed Parquet data
    -> Amazon Athena filter queries
    -> FastAPI backend

FastAPI backend
    -> Account 1 PostgreSQL RDS: save only chosen rows
    -> Account 2 Bedrock: analyze imported complaints

Frontend
    -> choose actual filter values from Athena
    -> preview limited selection
    -> import selected rows into PostgreSQL
```

## Values Used In This Project

| Setting | Value |
| --- | --- |
| Account 3 region | `ap-south-1` (Mumbai) |
| S3 bucket | `customerpulse-cfpb-data` |
| Raw source key | `raw/cfpb/complaints.csv` |
| Processed Glue output | `processed/cfpb_parquet_glue/` |
| Athena results folder | `athena/results/` |
| Athena database | `customerpulse_data` |
| Athena table used by backend | `cfpb_parquet` |

For another deployment, replace the bucket and region consistently in every
policy, Glue script, Athena query, and backend `.env` value.

## Follow These Guides In Order

| Step | Guide | Do This When |
| --- | --- | --- |
| 1 | `01_RDS_POSTGRESQL_ACCOUNT1.md` | Creating or reconnecting the PostgreSQL database |
| 2 | `02_BEDROCK_ACCOUNT2.md` | Creating or renewing Bedrock Claude access |
| 3 | `03_S3_BUCKET_ACCOUNT3.md` | Creating the private bucket and uploading the full CSV |
| 4 | `04_IAM_AND_LOCAL_CREDENTIALS_ACCOUNT3.md` | Creating uploader/backend identities and local access |
| 5 | `05_GLUE_MULTILINE_TO_PARQUET_ACCOUNT3.md` | Converting the large raw CSV safely |
| 6 | `06_ATHENA_ACCOUNT3.md` | Registering Parquet and enabling fast app filters |
| 7 | `07_APPLICATION_CONFIGURATION_AND_TESTING.md` | Connecting backend/frontend and verifying before writes |
| 8 | `08_PHASE2_EC2_ACCOUNT3.md` | Hosting a stable backend later |
| 9 | `09_BACKEND_RAG_REVIEW_PRODUCTION_UPGRADE.md` | Final backend RAG/review/job deployment readiness |

## Critical Rule For The CFPB CSV

The real uploaded CFPB file contains complaint narratives with embedded line
breaks. Do not convert it using a direct Athena raw CSV table. That can produce
errors such as:

```text
INVALID_CAST_ARGUMENT: Value cannot be cast to date:
UNAUTHORIZED HARD INQUIRIES - POTENTIAL IDENTITY THEFT ...
```

That error means narrative text has shifted into a date column. Follow the Glue
guide instead.

## Source Code Branches

| Purpose | Git Branch |
| --- | --- |
| Backend S3/Athena API and Glue/Athena code templates | `feature/cfpb-s3-import-api` |
| Frontend S3 Complaint Import page | `feature/frontend-dashboard` |
| AWS setup documentation and infrastructure templates | `feature/s3-cross-account-setup` |

## Security Rules

- Never commit `.env`, AWS credentials, Bedrock API keys, or downloaded access
  key CSV files.
- Keep S3 Block Public Access enabled.
- Give upload users upload permission only.
- Give local backend credentials read/query permission only.
- When hosting on EC2, use an EC2 IAM role rather than access keys.

## Official AWS References

- S3 Block Public Access: https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
- RDS for PostgreSQL getting started: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_GettingStarted.CreatingConnecting.PostgreSQL.html
- Bedrock API keys: https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api-keys.html
- Glue Spark job properties: https://docs.aws.amazon.com/glue/latest/dg/add-job.html
- Athena external tables: https://docs.aws.amazon.com/athena/latest/ug/create-table.html
- Athena partitions: https://docs.aws.amazon.com/athena/latest/ug/partitions.html
