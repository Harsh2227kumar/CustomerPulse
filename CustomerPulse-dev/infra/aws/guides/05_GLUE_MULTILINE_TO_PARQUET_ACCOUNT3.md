# AWS Glue Multiline CSV To Parquet - Account 3

Use Glue once after uploading a new full CFPB CSV. Glue converts the raw CSV
into efficient Parquet files for Athena.

## Why Glue Is Required

The uploaded CFPB CSV includes long consumer narratives that contain embedded
line breaks. A direct Athena CSV table can treat those line breaks as new rows
and shift narrative text into the wrong column.

The observed failure looked like:

```text
INVALID_CAST_ARGUMENT: Value cannot be cast to date:
UNAUTHORIZED HARD INQUIRIES - POTENTIAL IDENTITY THEFT ...
```

That is why the app must use this path:

```text
S3 raw CSV -> Glue with multiLine=true -> S3 Parquet -> Athena
```

## Source And Target Locations

| Purpose | S3 Location |
| --- | --- |
| Raw uploaded CSV | `s3://customerpulse-cfpb-data/raw/cfpb/complaints.csv` |
| Clean Parquet output | `s3://customerpulse-cfpb-data/processed/cfpb_parquet_glue/` |

## Create The Glue Service Role

1. In **Account 3**, open **IAM > Roles**.
2. Click **Create role**.
3. Select **AWS service**.
4. For service/use case, select **Glue**.
5. Continue to permissions.
6. Attach AWS managed policy:

   ```text
   AWSGlueServiceRole
   ```

7. Name the role:

   ```text
   CustomerPulseGlueCsvToParquetRole
   ```

8. Create the role.
9. Open the created role.
10. Choose **Add permissions > Create inline policy**.
11. Open the **JSON** editor and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListCustomerPulseBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data"
    },
    {
      "Sid": "ReadRawCfpbCsv",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data/raw/cfpb/*"
    },
    {
      "Sid": "WriteProcessedParquet",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload"
      ],
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data/processed/cfpb_parquet_glue/*"
    }
  ]
}
```

12. Name the inline policy:

    ```text
    CustomerPulseGlueS3ConversionAccess
    ```

13. Create the policy.

## Create The Glue ETL Job

1. Open **AWS Glue** in **Account 3**.
2. Set region to **Asia Pacific (Mumbai) `ap-south-1`**.
3. Open **ETL jobs**.
4. Choose **Script editor**.
5. Select **Spark script editor** and create a new script.
6. Configure job properties:

| Property | Starting Value |
| --- | --- |
| Name | `customerpulse-cfpb-csv-to-parquet` |
| IAM role | `CustomerPulseGlueCsvToParquetRole` |
| Type | Spark |
| Glue version | Latest Spark version shown in the console |
| Language | Python 3 |
| Worker type | `G.2X` |
| Number of workers | `5` |
| Timeout | `120` minutes |
| Retries | `0` |

This worker count is a practical starting value for the 8.8 GB source. Glue
costs money while jobs run, so do not repeatedly run it without a new source
file or a correction to apply.

## Glue Script

Paste the following complete script into the Glue script editor:

```python
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


args = getResolvedOptions(sys.argv, ["JOB_NAME"])
spark_context = SparkContext()
glue_context = GlueContext(spark_context)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

SOURCE_PATH = "s3://customerpulse-cfpb-data/raw/cfpb/complaints.csv"
TARGET_PATH = "s3://customerpulse-cfpb-data/processed/cfpb_parquet_glue/"

raw = (
    spark.read.option("header", "true")
    .option("multiLine", "true")
    .option("quote", '"')
    .option("escape", '"')
    .option("encoding", "UTF-8")
    .csv(SOURCE_PATH)
)

renamed = raw.select(
    F.col("`Date received`").alias("date_received"),
    F.col("`Product`").alias("product"),
    F.col("`Sub-product`").alias("sub_product"),
    F.col("`Issue`").alias("issue"),
    F.col("`Sub-issue`").alias("sub_issue"),
    F.col("`Consumer complaint narrative`").alias("consumer_complaint_narrative"),
    F.col("`Company public response`").alias("company_public_response"),
    F.col("`Company`").alias("company"),
    F.col("`State`").alias("state"),
    F.col("`ZIP code`").alias("zip_code"),
    F.col("`Tags`").alias("tags"),
    F.col("`Consumer consent provided?`").alias("consumer_consent_provided"),
    F.col("`Submitted via`").alias("submitted_via"),
    F.col("`Date sent to company`").alias("date_sent_to_company"),
    F.col("`Company response to consumer`").alias("company_response_to_consumer"),
    F.col("`Timely response?`").alias("timely_response"),
    F.col("`Consumer disputed?`").alias("consumer_disputed"),
    F.col("`Complaint ID`").alias("complaint_id"),
)

clean = (
    renamed.filter(F.col("complaint_id").isNotNull())
    .filter(F.col("consumer_complaint_narrative").isNotNull())
    .filter(F.length(F.trim(F.col("consumer_complaint_narrative"))) > 0)
    .withColumn("date_received", F.to_date("date_received", "yyyy-MM-dd"))
    .withColumn("date_sent_to_company", F.to_date("date_sent_to_company", "yyyy-MM-dd"))
    .withColumn("timely_response", F.lower(F.col("timely_response")) == F.lit("yes"))
    .withColumn("product_partition", F.col("product"))
)

(
    clean.write.mode("overwrite")
    .partitionBy("product_partition")
    .parquet(TARGET_PATH)
)

job.commit()
```

The backend feature branch also stores this script at:

```text
backend/glue/cfpb_csv_to_parquet.py.template
```

## Run And Monitor The Job

1. Save the job.
2. Click **Run**.
3. Open the **Runs** tab.
4. Wait for status **Succeeded**.
5. If it fails, open the run logs and keep the error message before changing
   settings.

## Confirm Parquet Was Written

In S3, open:

```text
processed/cfpb_parquet_glue/
```

After success, this prefix should contain folders beginning with:

```text
product_partition=
```

and Parquet part files inside them.

## Rerunning With A New Full CSV

1. Upload the new full CSV over:

   ```text
   raw/cfpb/complaints.csv
   ```

2. Run the same Glue job again.
3. The script uses overwrite mode for the processed output.
4. Re-run Athena partition repair as described in the next guide.

## Official AWS References

- https://docs.aws.amazon.com/glue/latest/dg/add-job.html
- https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-format-csv-home.html
