# Amazon S3 Raw Complaint Bucket - Account 3

Account 3 stores the full CFPB CSV, processed Parquet data, and Athena query
results. This account will also host EC2 later.

## Purpose

S3 stores the large source file without inserting every complaint into RDS.
Only filtered rows selected through the application are inserted into
PostgreSQL.

## Create The Bucket In The AWS Console

1. Sign in to **AWS Account 3**.
2. Confirm the region at the top of the console is:

   ```text
   ap-south-1
   ```

3. Open **Amazon S3**.
4. Click **Create bucket**.
5. Select **General purpose** bucket.
6. Enter the bucket name used in this project:

   ```text
   customerpulse-cfpb-data
   ```

   S3 bucket names are globally unique. If recreating the project and that name
   is unavailable, choose a new name and update every later guide value.

7. Choose region **Asia Pacific (Mumbai) `ap-south-1`**.
8. Keep **ACLs disabled / Bucket owner enforced**.
9. Keep **Block all public access** enabled.
10. Enable **Bucket Versioning**.
11. Under default encryption, keep server-side encryption enabled. S3-managed
    keys (`SSE-S3`) are sufficient for the current development flow.
12. Create the bucket.

## Required Folder Layout

S3 folders are object prefixes. Create or use these paths:

```text
raw/cfpb/
processed/cfpb_parquet_glue/
athena/results/
```

| Prefix | Used By | Contents |
| --- | --- | --- |
| `raw/cfpb/` | Upload user and Glue | Original full CSV |
| `processed/cfpb_parquet_glue/` | Glue and Athena | Optimized partitioned Parquet files |
| `athena/results/` | Athena/backend | Query result files |

## Upload The Source CSV

1. Open bucket `customerpulse-cfpb-data`.
2. Open or create folders `raw` then `cfpb`.
3. Click **Upload**.
4. Select the original complaint file.
5. Upload it with final key:

   ```text
   raw/cfpb/complaints.csv
   ```

6. Wait for upload status **Succeeded**.

An 8 GB upload can use S3 multipart upload automatically through the console.
Do not zip this file for the current workflow; Glue should read the CSV with
multiline parsing and create Parquet once.

## Verify The Object

In the S3 console:

1. Open `raw/cfpb/complaints.csv`.
2. Confirm the object size is present and the latest upload completed.
3. Do not make the object public.

The real file verified during development was approximately `8.81 GB`.

## Optional Infrastructure Template

This branch includes a bucket CloudFormation template:

```text
infra/aws/s3/cfpb-data-bucket.yaml
```

It creates a private versioned bucket with encryption and a policy that denies
unencrypted transport. The AWS Console steps above are easier when following
the guide manually.

## Do Not Do These Things

- Do not disable Block Public Access.
- Do not share account owner credentials with an uploader.
- Do not place downloaded IAM access-key CSV files in this bucket.
- Do not expect PostgreSQL RDS to fetch the CSV by itself; the backend is the
  bridge.

## Official AWS Reference

https://docs.aws.amazon.com/AmazonS3/latest/userguide/creating-bucket.html
