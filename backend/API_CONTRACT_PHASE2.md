# Backend Phase 2 Contract Handoff

This contract covers the Harsh-owned backend surfaces consumed by the frontend
and by later feature modules. Complaint-level `churn_risk` remains the legacy
API field name; it must be presented as case risk for CFPB records.

## Authentication

Protected writes use `Authorization: Bearer <key>`. Keys are configured only
through `AUTH_PRINCIPALS_JSON`.

| Role | Permitted Actions |
| --- | --- |
| `agent` | Process one complaint; rerun a review case |
| `manager` / `admin` | Agent actions plus approve/resolve review, import, create/retry batch and embedding jobs |

Read-only complaint listing, detail, health, and WebSocket connections remain
open for the demonstration dashboard. Atharva-owned export routes should reuse
the manager/admin dependency.

## Complaint And Review Endpoints

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/api/complaints` | Paged queue with filters `ai_status`, `human_review_reason`, full-text `search`, and new sort values `ai_confidence`, `ai_status`, `relevance`. |
| `GET` | `/api/complaints/{complaint_id}` | Detail, structured `similar_cases`, review metadata, and processing attempt history. |
| `POST` | `/api/process/{complaint_id}` | Processes imported complaint; returns `ai_status=completed` or `human_review`. |
| `POST` | `/api/complaints/{id}/review/rerun` | Creates a new audited processing attempt. |
| `POST` | `/api/complaints/{id}/review/approve` | Manager approves existing or edited response body. |
| `POST` | `/api/complaints/{id}/review/resolve` | Manager records another final resolution. |

Approve body:

```json
{
  "approved_response": "Optional edited response. Omit to approve current draft.",
  "notes": "Optional review note."
}
```

Resolve body:

```json
{
  "resolution": "rejected",
  "notes": "Response is not appropriate for this case."
}
```

`human_review_reason` values are `low_confidence`,
`weak_draft_response`, `vague_next_action`,
`bedrock_unavailable_after_retries`, `high_risk_high_urgency`, and
`invalid_ai_output`.

Each processing run stores a separate invocation trigger in
`trigger_reason`: `api_request`, `imported_request`, `review_rerun`, or
`batch_processing`. Review escalation reasons are recorded as the run
`error_category` and on the complaint `human_review_reason`. Protected
processing attempts also store the authenticated actor in `initiated_by`.

## RAG Evidence Shape

`similar_cases` is always structured and contains at most three completed cases
above the configured similarity threshold:

```json
[
  {
    "complaint_id": "12345",
    "similarity_score": 0.8214,
    "category": "Billing dispute",
    "next_action": "Review the disputed transaction.",
    "approved_response": null,
    "ai_status": "completed"
  }
]
```

## Job Endpoints

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/api/jobs/process` | Returns `202`; body `{ "complaint_ids": ["123", "456"] }`; maximum 50; unknown IDs are rejected. |
| `POST` | `/api/jobs/embedding-backfill` | Returns `202`; enqueues up to 100 records missing an embedding. |
| `GET` | `/api/jobs/{job_id}` | Poll status and item counts. |
| `POST` | `/api/jobs/{job_id}/retry` | Returns `202`; requeues failed items only. |

Job status values are `queued`, `running`, `completed`,
`completed_with_errors`, and `failed`. Item counts use `queued`, `running`,
`completed`, `human_review`, and `failed`. Retried failed items preserve prior
outcome snapshots in `attempt_history`.

## Realtime Event

The existing `/ws` feed adds:

```json
{
  "event": "human_review_required",
  "complaint_id": "12345",
  "payload": {
    "status": "human_review",
    "reason": "low_confidence",
    "ai_confidence": 0.21,
    "next_action": "Manual agent review required for this complaint."
  }
}
```

The deployment supports one backend instance for in-memory WebSocket delivery
and the in-process PostgreSQL-backed job worker. Redis is not part of this
project cycle.

## Backend Readiness

A new machine must install Python dependencies, create/reconcile the database
schema, and cache `all-MiniLM-L6-v2` before running protected processing or
backfill flows. Use:

```bash
VERIFY_EMBEDDING=true bash backend/scripts/setup_backend.sh
```

or, in Docker/EC2 deployment:

```bash
docker compose run --rm backend python -m app.db.setup --yes --verify-embedding
```

The setup fails if the embedding model cannot be downloaded/cached or if it
does not return exactly 384 dimensions.
