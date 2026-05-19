# API Contract

## Startup Contract

Before the API accepts requests, backend startup verifies:

- PostgreSQL connectivity.
- Target database existence.
- `pgvector` extension.
- `complaints` table and indexes.
- Basic row permissions.
- OpenAI API access using `OPENAI_API_KEY` and `OPENAI_MODEL`.

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

## WebSocket `/ws`

Events:

- `received`
- `preprocessing`
- `local_ml`
- `openai_processing`
- `validating`
- `saved`
- `failed`
