# API Contract

## Startup Contract

Before the API accepts requests, backend startup verifies:

- PostgreSQL connectivity.
- Target database existence.
- `pgvector` extension.
- `complaints` table and indexes.
- Basic row permissions.
- AWS Bedrock access using `AI_PROVIDER=bedrock`, `BEDROCK_API_KEY`, `BEDROCK_REGION`, and `BEDROCK_MODEL`.

If database or schema objects are missing, the backend prompts in the terminal before creating them. The same setup can be run manually from the `backend` folder:

```bash
python -m app.db.setup
```

## POST `/api/process`

Request:

```json
{
  "complaint_id": "string",
  "narrative": "string",
  "channel": "Web",
  "product": "optional string",
  "issue": "optional string",
  "company": "optional string"
}
```

Response:

```json
{
  "complaint_id": "string",
  "narrative": "string",
  "channel": "Web",
  "sentiment": "Positive|Neutral|Negative",
  "category": "string",
  "urgency_score": 85,
  "churn_risk": "Low|Medium|High",
  "draft_response": "string",
  "next_action": "string",
  "similar_cases": [],
  "confidence_scores": {
    "sentiment": 92,
    "category": 88,
    "urgency": 95,
    "churn_risk": 80,
    "draft_response": 75
  },
  "ai_confidence": 0.86,
  "ai_reasoning": "string",
  "processed_at": "ISO datetime"
}
```

## GET `/api/complaints`

Query parameters:

- `limit`
- `offset`
- `sentiment`
- `channel`
- `product`
- `churn_risk`
- `urgency_min`
- `urgency_max`
- `date_received_min`
- `date_received_max`
- `timely_response`
- `search`
- `sort_by`
- `sort_direction`

Reads only real PostgreSQL rows.

Each item includes `date_received` and `timely_response` when the source data provides them.

## GET `/api/search`

Query parameters:

- `q`
- `limit`
- `offset`

Keyword search now; pgvector similarity later.

## S3 Complaint Import

The backend reads the private CFPB CSV or CSV ZIP configured by `S3_BUCKET_NAME` and
`CFPB_S3_KEY`. The frontend does not receive S3 credentials or access raw objects.

`GET /api/ingestion/s3/options` scans eligible narrative rows and returns selectable
raw CFPB filter values for `product`, `sub_product`, `issue`, `company`, and
`channel`.

`POST /api/ingestion/s3/preview` accepts raw-file filters plus `max_records`
(`1` to `5000`) and returns the matching count and the rows that would be imported.

`POST /api/ingestion/s3/import` applies the same filters and upserts no more than
`max_records` real rows into PostgreSQL. New imported complaints are stored with
`ai_status=pending`; Bedrock enrichment remains a separate processing action.

`Product` is the raw-data category filter, for example `Credit card`. AI
`category` is not available until a complaint has been imported and processed.

## WebSocket `/ws`

Events:

- `received`
- `preprocessing`
- `local_ml`
- `bedrock_processing`
- `validating`
- `saved`
- `failed`
