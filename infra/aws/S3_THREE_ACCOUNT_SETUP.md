# Three-Account CFPB S3 Setup Summary

The full repeatable setup handbook is in:

```text
infra/aws/guides/00_SETUP_INDEX.md
```

## Current Architecture

```text
Account 1: PostgreSQL RDS
Account 2: Amazon Bedrock Claude
Account 3: S3 raw data, AWS Glue, Amazon Athena, and future EC2 backend
```

```text
S3 raw CSV -> Glue multiline CSV conversion -> S3 Parquet -> Athena queries
                                                            |
Frontend -> FastAPI backend -------------------------------+
            |
            +-> Account 1 RDS PostgreSQL (selected complaints only)
            +-> Account 2 Bedrock (AI processing)
```

## Important Correction

Do not query or convert the raw CFPB CSV through Athena CSV tables for this
dataset. The consumer complaint narrative column contains embedded line breaks.
Athena's Open CSV SerDe does not safely support those embedded line breaks, and
can shift narrative text into columns such as `date_received`.

Use AWS Glue with multiline CSV parsing to create Parquet data first. Athena
then reads only the generated Parquet data.

## Guide Order

1. `infra/aws/guides/01_RDS_POSTGRESQL_ACCOUNT1.md`
2. `infra/aws/guides/02_BEDROCK_ACCOUNT2.md`
3. `infra/aws/guides/03_S3_BUCKET_ACCOUNT3.md`
4. `infra/aws/guides/04_IAM_AND_LOCAL_CREDENTIALS_ACCOUNT3.md`
5. `infra/aws/guides/05_GLUE_MULTILINE_TO_PARQUET_ACCOUNT3.md`
6. `infra/aws/guides/06_ATHENA_ACCOUNT3.md`
7. `infra/aws/guides/07_APPLICATION_CONFIGURATION_AND_TESTING.md`
8. `infra/aws/guides/08_PHASE2_EC2_ACCOUNT3.md`
