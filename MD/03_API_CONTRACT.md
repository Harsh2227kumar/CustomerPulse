# API Contract

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
- `search`
- `sort_by`
- `sort_direction`

Reads only real PostgreSQL rows.

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
- `claude_processing`
- `validating`
- `saved`
- `failed`
