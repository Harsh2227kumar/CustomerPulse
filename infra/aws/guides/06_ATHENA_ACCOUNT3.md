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

## Read-Only Analysis Query Library

All queries in this section read from the Glue-created Parquet table. They do
not write to PostgreSQL and do not change S3 data. Since the Glue job keeps
rows with both a complaint ID and a narrative, these results describe
**import-eligible complaints**, not every original raw CSV row.

When a query focuses on one product, include `product_partition` as shown in
the examples so Athena can read only that product partition.

### 1. Total Import-Eligible Rows

Purpose: confirm the size of the clean Parquet dataset and the number of unique
complaint IDs.

```sql
SELECT
  COUNT(*) AS eligible_rows,
  COUNT(DISTINCT complaint_id) AS unique_complaint_ids
FROM customerpulse_data.cfpb_parquet;
```

### 2. Date Coverage Of The Dataset

Purpose: see the earliest date, latest date, and number of years available for
frontend date filters.

```sql
SELECT
  MIN(date_received) AS first_received_date,
  MAX(date_received) AS last_received_date,
  COUNT(DISTINCT year(date_received)) AS years_covered
FROM customerpulse_data.cfpb_parquet;
```

### 3. Complaints By Product Category

Purpose: identify the highest-volume product categories.

```sql
SELECT product, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
GROUP BY product
ORDER BY complaints DESC
LIMIT 20;
```

### 4. Product Category Percentage Share

Purpose: understand what percentage of all import-eligible complaints belongs
to each major category.

```sql
WITH product_counts AS (
  SELECT product, COUNT(*) AS complaints
  FROM customerpulse_data.cfpb_parquet
  GROUP BY product
)
SELECT
  product,
  complaints,
  ROUND(100.0 * complaints / SUM(complaints) OVER (), 2) AS percentage_share
FROM product_counts
ORDER BY complaints DESC
LIMIT 20;
```

### 5. Credit Card Sub-Product Breakdown

Purpose: populate or review detailed credit-card choices after selecting the
credit-card product in the frontend.

```sql
SELECT sub_product, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE product_partition = 'Credit card or prepaid card'
  AND product = 'Credit card or prepaid card'
GROUP BY sub_product
ORDER BY complaints DESC
LIMIT 20;
```

### 6. Most Frequent Credit Card Issues

Purpose: find useful issue filters for a targeted credit-card import.

```sql
SELECT issue, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE product_partition = 'Credit card or prepaid card'
  AND product = 'Credit card or prepaid card'
GROUP BY issue
ORDER BY complaints DESC
LIMIT 20;
```

### 7. Top Issues Across All Products

Purpose: compare major complaint themes across the entire selectable dataset.

```sql
SELECT issue, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE issue IS NOT NULL
GROUP BY issue
ORDER BY complaints DESC
LIMIT 25;
```

### 8. Product And Issue Combination Analysis

Purpose: discover the strongest product/issue combinations for analysis
experiments.

```sql
SELECT product, issue, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE product IS NOT NULL
  AND issue IS NOT NULL
GROUP BY product, issue
ORDER BY complaints DESC
LIMIT 30;
```

### 9. Companies With The Most Complaints

Purpose: identify companies with high complaint volume.

```sql
SELECT company, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE company IS NOT NULL
GROUP BY company
ORDER BY complaints DESC
LIMIT 25;
```

### 10. Top Credit Card Companies

Purpose: select a specific company when importing credit-card complaints.

```sql
SELECT company, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE product_partition = 'Credit card or prepaid card'
  AND product = 'Credit card or prepaid card'
  AND company IS NOT NULL
GROUP BY company
ORDER BY complaints DESC
LIMIT 25;
```

### 11. Complaints By State

Purpose: measure where complaint records are concentrated geographically.

```sql
SELECT state, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE state IS NOT NULL
  AND trim(state) <> ''
GROUP BY state
ORDER BY complaints DESC
LIMIT 25;
```

### 12. Submission Channel Mix

Purpose: analyze how consumers submitted complaints and confirm frontend
channel options.

```sql
SELECT submitted_via, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE submitted_via IS NOT NULL
GROUP BY submitted_via
ORDER BY complaints DESC;
```

### 13. Overall Timely Response Rate

Purpose: measure how many complaint records report a timely company response.

```sql
SELECT
  COUNT(*) AS complaints,
  SUM(CASE WHEN timely_response THEN 1 ELSE 0 END) AS timely_complaints,
  SUM(CASE WHEN NOT timely_response THEN 1 ELSE 0 END) AS not_timely_complaints,
  ROUND(
    100.0 * SUM(CASE WHEN timely_response THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
    2
  ) AS timely_percentage
FROM customerpulse_data.cfpb_parquet;
```

### 14. Timely Response Rate By Product

Purpose: compare company response performance across categories.

```sql
SELECT
  product,
  COUNT(*) AS complaints,
  ROUND(
    100.0 * SUM(CASE WHEN timely_response THEN 1 ELSE 0 END) / COUNT(*),
    2
  ) AS timely_percentage
FROM customerpulse_data.cfpb_parquet
WHERE product IS NOT NULL
GROUP BY product
ORDER BY complaints DESC
LIMIT 20;
```

### 15. Companies With Lowest Timely Response Rate

Purpose: identify companies needing attention while ignoring companies with
too few records for a meaningful comparison.

```sql
SELECT
  company,
  COUNT(*) AS complaints,
  ROUND(
    100.0 * SUM(CASE WHEN timely_response THEN 1 ELSE 0 END) / COUNT(*),
    2
  ) AS timely_percentage
FROM customerpulse_data.cfpb_parquet
WHERE company IS NOT NULL
GROUP BY company
HAVING COUNT(*) >= 100
ORDER BY timely_percentage ASC, complaints DESC
LIMIT 25;
```

### 16. Monthly Complaint Trend

Purpose: see complaint volume over time for dashboards and trend analysis.

```sql
SELECT
  date_trunc('month', date_received) AS received_month,
  COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE date_received IS NOT NULL
GROUP BY date_trunc('month', date_received)
ORDER BY received_month;
```

### 17. Monthly Credit Card Trend

Purpose: analyze one UI category efficiently using its partition.

```sql
SELECT
  date_trunc('month', date_received) AS received_month,
  COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE product_partition = 'Credit card or prepaid card'
  AND product = 'Credit card or prepaid card'
  AND date_received IS NOT NULL
GROUP BY date_trunc('month', date_received)
ORDER BY received_month;
```

### 18. Complaint Delivery Delay To Company

Purpose: estimate how quickly complaints were sent to companies after receipt.

```sql
SELECT
  product,
  COUNT(*) AS complaints_with_dates,
  ROUND(AVG(date_diff('day', date_received, date_sent_to_company)), 2)
    AS average_days_to_company,
  MAX(date_diff('day', date_received, date_sent_to_company))
    AS maximum_days_to_company
FROM customerpulse_data.cfpb_parquet
WHERE date_received IS NOT NULL
  AND date_sent_to_company IS NOT NULL
GROUP BY product
ORDER BY complaints_with_dates DESC
LIMIT 20;
```

### 19. Missing Filter Field Quality Check

Purpose: understand how many rows may display `Unknown` or be unavailable for
specific frontend filters.

```sql
SELECT
  COUNT(*) AS eligible_rows,
  SUM(CASE WHEN product IS NULL OR trim(product) = '' THEN 1 ELSE 0 END)
    AS missing_product,
  SUM(CASE WHEN sub_product IS NULL OR trim(sub_product) = '' THEN 1 ELSE 0 END)
    AS missing_sub_product,
  SUM(CASE WHEN issue IS NULL OR trim(issue) = '' THEN 1 ELSE 0 END)
    AS missing_issue,
  SUM(CASE WHEN company IS NULL OR trim(company) = '' THEN 1 ELSE 0 END)
    AS missing_company,
  SUM(CASE WHEN submitted_via IS NULL OR trim(submitted_via) = '' THEN 1 ELSE 0 END)
    AS missing_channel,
  SUM(CASE WHEN date_received IS NULL THEN 1 ELSE 0 END)
    AS missing_received_date
FROM customerpulse_data.cfpb_parquet;
```

### 20. Duplicate Complaint ID Check

Purpose: verify the identifier used for PostgreSQL upsert does not have
unexpected duplicates in the processed data.

```sql
SELECT complaint_id, COUNT(*) AS occurrences
FROM customerpulse_data.cfpb_parquet
GROUP BY complaint_id
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
LIMIT 50;
```

If this returns no rows, no duplicate complaint IDs were found.

### 21. Narrative Length Analysis

Purpose: estimate how large complaint narratives are before running AI
processing.

```sql
SELECT
  product,
  COUNT(*) AS complaints,
  ROUND(AVG(length(consumer_complaint_narrative)), 2)
    AS average_narrative_characters,
  MAX(length(consumer_complaint_narrative))
    AS longest_narrative_characters
FROM customerpulse_data.cfpb_parquet
WHERE consumer_complaint_narrative IS NOT NULL
GROUP BY product
ORDER BY complaints DESC
LIMIT 20;
```

### 22. Consumer Consent Distribution

Purpose: inspect availability of consumer-provided narrative permissions or
consent categories contained in the source.

```sql
SELECT consumer_consent_provided, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
GROUP BY consumer_consent_provided
ORDER BY complaints DESC;
```

### 23. Consumer Dispute Distribution

Purpose: examine legacy disputed-status values where present in the source.

```sql
SELECT consumer_disputed, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
GROUP BY consumer_disputed
ORDER BY complaints DESC;
```

### 24. Tag Distribution

Purpose: inspect special groups such as older consumers or servicemembers when
tags exist.

```sql
SELECT tags, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE tags IS NOT NULL
  AND trim(tags) <> ''
GROUP BY tags
ORDER BY complaints DESC
LIMIT 20;
```

### 25. Exact Count For A Planned Filtered Import

Purpose: see how many rows match a proposed frontend selection before
requesting only a small import limit.

```sql
SELECT COUNT(*) AS matching_complaints
FROM customerpulse_data.cfpb_parquet
WHERE product_partition = 'Credit card or prepaid card'
  AND product = 'Credit card or prepaid card'
  AND timely_response = true;
```

### 26. Preview Rows For A Planned Filtered Import

Purpose: read a small sample matching the kind of filter the frontend sends to
the backend.

```sql
SELECT
  complaint_id,
  date_received,
  product,
  sub_product,
  issue,
  company,
  submitted_via,
  timely_response
FROM customerpulse_data.cfpb_parquet
WHERE product_partition = 'Credit card or prepaid card'
  AND product = 'Credit card or prepaid card'
  AND timely_response = true
ORDER BY date_received DESC
LIMIT 50;
```

### 27. Confirm Product Partitions Are Loaded

Purpose: verify that `MSCK REPAIR TABLE` registered product folders after Glue
runs.

```sql
SELECT product_partition, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
GROUP BY product_partition
ORDER BY complaints DESC
LIMIT 20;
```

### 28. Company Response Type Breakdown

Purpose: review how companies responded to consumers across eligible
complaints.

```sql
SELECT company_response_to_consumer, COUNT(*) AS complaints
FROM customerpulse_data.cfpb_parquet
WHERE company_response_to_consumer IS NOT NULL
GROUP BY company_response_to_consumer
ORDER BY complaints DESC;
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
| `Unable to verify/create output bucket customerpulse-cfpb-data` | Athena cannot inspect or write its S3 results location | Replace `CustomerPulseAthenaRuntime` with the policy in guide 04; `s3:GetBucketLocation` must not be limited by an `s3:prefix` condition |
| Athena cannot write results | Results object permissions missing | Grant `s3:PutObject`, `s3:GetObject`, and multipart actions to `athena/results/*` |

## Official AWS References

- https://docs.aws.amazon.com/athena/latest/ug/query-results-specify-location-console.html
- https://docs.aws.amazon.com/athena/latest/ug/create-table.html
- https://docs.aws.amazon.com/athena/latest/ug/partitions.html
- https://docs.aws.amazon.com/athena/latest/ug/csv-serde.html
