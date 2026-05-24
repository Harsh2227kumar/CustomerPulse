# Amazon Athena Filter Queries - Account 3

Athena queries the clean Parquet output created by Glue. The backend uses these
queries to load real filter values, preview limited rows, and select only the
requested records for PostgreSQL.

## Do Not Use The Raw CSV Table

For this CFPB file, do not use Athena to parse or convert:

```text
s3://customerpulse-cfpb-data/raw/cfpb/complaints.csv
```

The narrative column contains multiline content. Query only the Glue-created
Parquet output:

```text
s3://customerpulse-cfpb-data/processed/cfpb_parquet_glue/
```

## Configure Athena Results Folder

1. Sign in to **Account 3**.
2. Open **Amazon Athena**.
3. Select region:

   ```text
   ap-south-1
   ```

4. Open **Query editor**.
5. Open **Settings > Manage**.
6. Set query result location:

   ```text
   s3://customerpulse-cfpb-data/athena/results/
   ```

7. Save.

## Clean Up A Failed Raw CSV Conversion

If the earlier Athena CSV-to-Parquet attempt failed:

1. In Athena, run:

```sql
DROP TABLE IF EXISTS customerpulse_data.cfpb_raw_csv;
DROP TABLE IF EXISTS customerpulse_data.cfpb_parquet;
```

2. In S3, delete only incomplete output from the failed Athena attempt if it
   exists, for example:

```text
athena/results/Unsaved/2026/05/24/tables/<failed-query-id>/
processed/cfpb_parquet/
```

3. Do not delete:

```text
raw/cfpb/complaints.csv
processed/cfpb_parquet_glue/
```

## Register The Glue Parquet Data

Run this SQL in Athena only after the Glue job has succeeded:

```sql
CREATE DATABASE IF NOT EXISTS customerpulse_data;

DROP TABLE IF EXISTS customerpulse_data.cfpb_parquet;

CREATE EXTERNAL TABLE customerpulse_data.cfpb_parquet (
  date_received date,
  product string,
  sub_product string,
  issue string,
  sub_issue string,
  consumer_complaint_narrative string,
  company_public_response string,
  company string,
  state string,
  zip_code string,
  tags string,
  consumer_consent_provided string,
  submitted_via string,
  date_sent_to_company date,
  company_response_to_consumer string,
  timely_response boolean,
  consumer_disputed string,
  complaint_id string
)
PARTITIONED BY (product_partition string)
STORED AS PARQUET
LOCATION 's3://customerpulse-cfpb-data/processed/cfpb_parquet_glue/';

MSCK REPAIR TABLE customerpulse_data.cfpb_parquet;
```

The backend feature branch also stores this SQL at:

```text
backend/sql/athena_cfpb_parquet_registration.sql.template
```

`MSCK REPAIR TABLE` loads the folders written by Glue as Athena partitions.

## Test Real Filter Values

Run:

```sql
SELECT product, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
GROUP BY product
ORDER BY complaints DESC
LIMIT 20;
```

The uploaded file includes the real product value:

```text
Credit card or prepaid card
```

Test that partition:

```sql
SELECT product, issue, company, complaint_id
FROM customerpulse_data.cfpb_parquet
WHERE product_partition = 'Credit card or prepaid card'
LIMIT 5;
```

Test the fields used as frontend filter options:

```sql
SELECT DISTINCT submitted_via
FROM customerpulse_data.cfpb_parquet
ORDER BY submitted_via;
```

```sql
SELECT min(date_received), max(date_received)
FROM customerpulse_data.cfpb_parquet;
```

## How The Application Uses Athena

The backend does not load all complaints into PostgreSQL.

| Frontend Action | Athena Behavior |
| --- | --- |
| Open S3 Complaint Import page | Reads distinct filter values from Parquet |
| Click Preview | Runs filtered query with requested maximum row limit |
| Click Import to PostgreSQL | Selects the requested limited matching rows |

## Backend Permissions

Attach `CustomerPulseAthenaRuntime` to the backend readers group as described
in:

```text
infra/aws/guides/04_IAM_AND_LOCAL_CREDENTIALS_ACCOUNT3.md
```

The backend needs Athena query permission, Glue catalog metadata read
permission, S3 read permission on processed Parquet, and read/write permission
on Athena query results.

## Troubleshooting

| Error | Likely Cause | Fix |
| --- | --- | --- |
| `INVALID_CAST_ARGUMENT` with narrative words | Raw CSV was queried directly | Use Glue output and recreate `cfpb_parquet` from Parquet |
| Table returns zero rows | Partitions were not registered | Run `MSCK REPAIR TABLE customerpulse_data.cfpb_parquet;` |
| `AccessDenied` when app loads filters | Backend user lacks Athena/S3/Glue metadata access | Attach the runtime policy in guide 04 |
| Athena cannot write results | Results folder access missing | Grant `s3:PutObject` to `athena/results/*` |

## Official AWS References

- https://docs.aws.amazon.com/athena/latest/ug/query-results-specify-location-console.html
- https://docs.aws.amazon.com/athena/latest/ug/create-table.html
- https://docs.aws.amazon.com/athena/latest/ug/partitions.html
- https://docs.aws.amazon.com/athena/latest/ug/csv-serde.html
