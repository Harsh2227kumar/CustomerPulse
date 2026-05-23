# Filtered S3 Complaint Import API

## Purpose

The raw CFPB export stays in a private S3 bucket. Operators use the frontend to
select real raw-data filters and a maximum row count; the backend alone reads S3
and writes the selected rows to PostgreSQL.

```text
Account 2 private S3 CSV/ZIP -> FastAPI import endpoints -> Account 1 RDS PostgreSQL
```

## Endpoints

- `GET /api/ingestion/s3/options`: scan the configured CSV source and return
  selectable raw CFPB fields.
- `POST /api/ingestion/s3/preview`: preview exactly which bounded set would be
  written, without database changes.
- `POST /api/ingestion/s3/import`: upsert the bounded set into `complaints` and
  return operator-visible status logs.

Request body for preview/import:

```json
{
  "product": "Credit card",
  "sub_product": null,
  "issue": null,
  "company": null,
  "channel": null,
  "timely_response": null,
  "date_received_min": null,
  "date_received_max": null,
  "max_records": 50
}
```

## Rules

- `Product` is used as the selectable raw category, for example `Credit card`.
  Bedrock-derived `category` exists only after later AI processing.
- Rows without both `Complaint ID` and `Consumer complaint narrative` are never
  imported.
- Imports upsert by complaint ID, write in batches, and keep AI fields empty with
  `ai_status=pending`.
- The browser never receives S3 credentials or downloads the raw export.
- Supported S3 object types are `.csv` and `.zip` containing a CSV file.
