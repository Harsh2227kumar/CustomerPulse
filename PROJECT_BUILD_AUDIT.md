# CustomerPulse Project Build Audit

This document summarizes what has already been built in the `CustomerPulse` repository, grouped by technical domain. It is based on the current repository code and is meant to help backend, frontend, ML, database, infrastructure, and demo teams understand the implemented system clearly.

---

## 1. High-Level Project Summary

`CustomerPulse` is an integrated complaint intelligence platform for banking/BFSI complaint operations. The repository is not just a frontend demo; it already contains an end-to-end integrated stack with:

- React/Vite frontend dashboard.
- FastAPI backend service.
- PostgreSQL persistence.
- AWS S3 CFPB complaint ingestion.
- Optional Athena query mode for large CFPB CSV filtering.
- Local rule-based ML signal extraction.
- Amazon Bedrock complaint enrichment.
- Sentence-transformer embeddings.
- pgvector-based similar-case retrieval / RAG evidence.
- Human-review workflow.
- Batch processing jobs.
- Analytics APIs.
- Duplicate complaint detection APIs.
- Agent feedback APIs.
- Export APIs.
- SLA reporting APIs.
- WebSocket live processing events.
- Docker Compose deployment with Nginx reverse proxy.

The root `README.md` also confirms the integrated architecture: `frontend/`, `backend/`, `infra/`, and `shared/schema/` are designed to work together before promotion to `main`.

---

## 2. Repository Domains Built

### 2.1 Frontend Domain

Location: `frontend/`

The frontend is a React/Vite dashboard with TypeScript support and API integration. It has multiple views and pages for operations, import, analytics, queue handling, and main dashboard usage.

Implemented frontend capabilities include:

- Main dashboard view.
- Complaint listing and filtering.
- Search support.
- Pagination support.
- Complaint processing form.
- Live WebSocket status display.
- Processing event timeline labels.
- Import page for controlled S3/CFPB ingestion.
- Queue processing support.
- Operations page.
- Analytics page.
- SLA API integration.
- Feedback API integration.
- Duplicate detection API integration.
- Export download support.
- API key storage through browser local storage.
- Bearer token attachment for protected backend routes.

The frontend `App.tsx` keeps state for active views such as `dashboard`, `import`, `queue`, `ops`, and `analytics`. It also maintains filters for search, sentiment, channel, product, churn risk, urgency range, date ranges, timely response, AI status, human review reason, and sorting.

The frontend API client includes functions for:

- Health check.
- Complaint listing.
- Complaint detail retrieval.
- Direct complaint processing.
- Imported complaint processing.
- Review approval.
- Review resolution.
- Review rerun.
- S3 import options.
- S3 import preview.
- S3 complaint import.
- Processing job creation.
- Embedding backfill job creation.
- Job polling and retry.
- Complaint trend analytics.
- Product summary analytics.
- Human review analytics.
- High urgency analytics.
- SLA summary.
- SLA by product.
- SLA by channel.
- SLA breach risk.
- SLA trends.
- Agent feedback submission and listing.
- Duplicate detection.
- Duplicate group listing.
- Duplicate group read.
- Duplicate merge / reject.
- Duplicate channel comparison.
- CSV/PDF/backend export downloads.

This means the frontend is already connected to most backend domains, not only the main processing API.

---

### 2.2 Backend Domain

Location: `backend/`

The backend is built using FastAPI with async SQLAlchemy and PostgreSQL. The main application registers many routers and starts background systems during the FastAPI lifespan.

Implemented backend modules include:

- Health router.
- Processing router.
- Complaints router.
- S3 ingestion router.
- Review router.
- Jobs router.
- Feedback router.
- Duplicate detection router.
- Analytics router.
- Export routes.
- SLA routes.
- WebSocket router.

The backend startup lifecycle already performs:

- Startup checks.
- Bedrock verification.
- Optional embedding model readiness verification.
- Abandoned job recovery.
- Background processing worker startup.
- Background worker shutdown handling.

This shows the backend has moved beyond a simple API prototype and already contains production-style lifecycle handling.

---

## 3. Backend: ML / AI Part

Location examples:

- `backend/app/ai/pipelines/complaint_pipeline.py`
- `backend/app/ai/ml_models/sentiment.py`
- `backend/app/ai/ml_models/classifier.py`
- `backend/app/ai/ml_models/urgency.py`
- `backend/app/ai/ml_models/confidence.py`
- `backend/app/ai/preprocessing/cleaner.py`
- `backend/app/ai/preprocessing/extractor.py`
- `backend/app/ai/preprocessing/summarizer.py`
- `backend/app/ai/bedrock/client.py`
- `backend/app/ai/bedrock/parser.py`
- `backend/app/ai/bedrock/retry_handler.py`
- `backend/app/ai/validators/schema_validator.py`
- `backend/app/ai/validators/review_router.py`

### 3.1 Local ML Layer

The local ML layer is already implemented before Bedrock is called. It produces local signals from complaint text.

The local layer performs:

1. Complaint text cleaning.
2. Prompt compression.
3. Signal extraction.
4. Sentiment prediction.
5. Category classification.
6. Urgency estimation.
7. Combined confidence calculation.

The pipeline returns a `LocalSignals` object containing:

- `cleaned_narrative`
- `prompt_narrative`
- `sentiment`
- `sentiment_confidence`
- `category`
- `category_confidence`
- `urgency_score`
- `urgency_confidence`
- `combined_confidence`

This is useful because the system does not depend fully on the LLM. It has deterministic local scoring that can still run even when Bedrock fails.

### 3.2 Sentiment Model

File: `backend/app/ai/ml_models/sentiment.py`

The sentiment system is a BFSI-focused rule/dictionary model.

It includes:

- Negative phrase detection.
- Positive phrase detection.
- Negative term detection.
- Positive term detection.
- Negation handling.
- Confidence scoring.
- Reason-code output.

Examples of negative BFSI signals include:

- Account frozen.
- Account blocked.
- Transaction declined.
- Payment failed.
- Unauthorized debit.
- Fraud transaction.
- Wrong amount debited.
- Double charged.
- Refund not received.
- Service unavailable.

Examples of positive BFSI signals include:

- Case resolved.
- Complaint resolved.
- Problem fixed.
- Refund received.
- Payment successful.
- Account restored.
- Customer support helpful.

Output format:

```text
(sentiment, confidence, reason_codes)
```

Sentiment values are:

- Positive
- Neutral
- Negative

### 3.3 Category Classifier

File: `backend/app/ai/ml_models/classifier.py`

The category classifier maps complaint text, CFPB product fields, CFPB issue fields, and optional Bedrock category output into standard categories.

Standard categories built:

- Billing or fees
- Fraud or unauthorized activity
- Account servicing
- Credit reporting
- Loan or mortgage issue
- Card services
- Digital banking or transfers
- Insurance or investment
- Customer service failure
- General complaint

Important implementation details:

- CFPB `issue` has higher priority than product and narrative matching.
- CFPB `product` is used when issue is not available.
- Text phrase matching is used when CFPB fields are absent.
- Bedrock disagreement can be detected as a category conflict.
- Confidence is returned with reason codes.

Output format:

```text
(category, confidence, reason_codes, conflict)
```

This is useful for demo and explainability because the classifier can show why a complaint was categorized.

### 3.4 Urgency Model

File: `backend/app/ai/ml_models/urgency.py`

The urgency estimator is implemented as a signal-based scoring model.

It starts with a base urgency score and adds weighted points for:

- Fraud indicators.
- Financial loss.
- Blocked account/card access.
- Legal escalation.
- Failed payments.
- Repeat contact.
- Waiting/delay terms.
- Escalation terms.
- Legal terms from extractor.
- Financial harm terms from extractor.

Urgency score is clamped between 0 and 100.

Risk levels are derived from the score:

- Critical
- High
- Medium
- Low

The model also returns a human-readable risk reason.

Output format:

```text
(score, confidence, reason_codes, case_risk, risk_reason)
```

### 3.5 Confidence Combination

The ML pipeline combines confidence from sentiment, category, and urgency into an overall local confidence score. This score is later used in the processing flow and fallback enrichment.

### 3.6 Bedrock LLM Enrichment

File: `backend/app/ai/bedrock/client.py`

The Bedrock client is built around the Bedrock Runtime Converse endpoint.

The LLM enrichment schema expects:

- `sentiment`
- `category`
- `urgency_score`
- `churn_risk`
- `draft_response`
- `next_action`
- `similar_cases`
- `confidence_scores`
- `ai_confidence`
- `ai_reasoning`

The Bedrock call sends:

- System prompt.
- User prompt.
- Complaint ID.
- Complaint narrative.
- Complaint channel.
- Local sentiment.
- Local category.
- Local urgency score.
- Similar case evidence.

Inference configuration:

- Temperature: `0`
- Max tokens: `1200`

This means the Bedrock layer is intended to produce deterministic structured complaint enrichment.

### 3.7 Bedrock Retry and Validation

The AI pipeline wraps the Bedrock call with retry handling. After Bedrock returns text, the system:

1. Parses a JSON object.
2. Validates it against the AI enrichment schema.
3. Converts it into an `AIEnrichment` object.
4. Reattaches similar case evidence.

If Bedrock fails after retries, or if Bedrock returns invalid structured output, the system raises controlled errors.

### 3.8 Fallback Enrichment

The backend already includes a fallback enrichment path.

If Bedrock is unavailable or returns invalid AI output, the processing service generates fallback enrichment using local ML signals:

- Sentiment from local model.
- Category from local classifier.
- Urgency score from local urgency model.
- Churn risk based on urgency.
- Empty draft response.
- Manual-review next action.
- Similar case evidence preserved.
- Confidence scores from local model outputs.
- AI reasoning explaining that automated enrichment was unavailable.

This is an important reliability feature because complaints can still be saved and routed to human review instead of failing silently.

---

## 4. Backend: RAG / Embedding / Similar Case Part

Location examples:

- `backend/app/services/embedding_service.py`
- `backend/app/services/retrieval_service.py`
- `backend/app/models/complaint.py`

### 4.1 Embedding Service

The embedding service uses `sentence-transformers` and caches loaded models using `lru_cache`.

Implemented features:

- Loads configured sentence-transformer model.
- Embeds single complaint text.
- Embeds multiple complaint texts.
- Rejects empty narratives.
- Validates embedding dimension.
- Validates all vector values are finite.
- Uses async wrapper around blocking model inference.

The configured repo dependency includes:

- `sentence-transformers`
- `torch` CPU wheel
- `pgvector`

The README states that the MiniLM model is verified to return 384-dimensional embeddings before deployment.

### 4.2 pgvector Similar Case Retrieval

The complaint model stores an embedding vector column using pgvector. It also defines an HNSW cosine index for fast vector similarity search.

The retrieval service:

- Validates query vector dimensions.
- Validates similarity threshold.
- Validates result limit.
- Calculates cosine distance.
- Converts distance into similarity score.
- Filters only completed complaints.
- Ignores the active complaint itself.
- Returns top similar cases by ascending distance.

Returned similar-case evidence includes:

- Complaint ID.
- Similarity score.
- Category.
- Next action.
- Approved response.
- AI status.

This similar-case evidence is passed into the Bedrock prompt, so the current system already has a practical RAG-style enrichment flow.

---

## 5. Backend: Database / PostgreSQL Part

Location examples:

- `backend/app/models/complaint.py`
- `backend/app/models/processing.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/db/setup.py`

### 5.1 Database Technology

The backend uses:

- PostgreSQL.
- SQLAlchemy async ORM.
- asyncpg.
- JSONB columns.
- pgvector vectors.
- PostgreSQL full-text search through `TSVECTOR`.
- PostgreSQL indexes and constraints.

### 5.2 Complaints Table

Model: `Complaint`

Table name: `complaints`

The complaints table stores raw CFPB/customer complaint data and AI-processed outputs in one main operational record.

Raw / source fields include:

- `id`
- `source_complaint_id`
- `narrative`
- `channel`
- `product`
- `sub_product`
- `issue`
- `sub_issue`
- `company`
- `company_response`
- `timely_response`
- `date_received`

AI enrichment fields include:

- `sentiment`
- `category`
- `urgency_score`
- `churn_risk`
- `draft_response`
- `next_action`
- `confidence_scores`
- `ai_confidence`
- `ai_reasoning`
- `similar_case_evidence`
- `processed_at`
- `ai_status`
- `retry_count`
- `error_message`

Embedding/RAG fields include:

- `embedding`
- `embedding_model`
- `embedded_at`

Human review fields include:

- `human_review_reason`
- `human_review_created_at`
- `reviewed_at`
- `reviewer`
- `review_resolution`
- `approved_response`
- `review_notes`

Search/index fields include:

- Computed `search_vector` using weighted full-text search.
- GIN index on `search_vector`.
- HNSW cosine index on `embedding`.

Constraints built:

- Urgency must be between 0 and 100.
- AI confidence must be between 0 and 1.
- Retry count must be non-negative.

### 5.3 Processing Runs Table

Model: `ComplaintProcessingRun`

Table name: `complaint_processing_runs`

This table logs every processing attempt for a complaint.

Stored fields include:

- Run ID.
- Complaint ID.
- Attempt number.
- Status outcome.
- Trigger reason.
- Initiated by.
- Local signals.
- Bedrock model used.
- Prompt evidence.
- AI payload.
- Error category.
- Created timestamp.
- Finished timestamp.

Constraints built:

- Unique complaint + attempt number.
- Attempt number must be positive.

This is very useful for auditability because each processing attempt is stored separately.

### 5.4 Processing Jobs Tables

Models:

- `ProcessingJob`
- `ProcessingJobItem`

Tables:

- `processing_jobs`
- `processing_job_items`

Processing jobs store batch operations and item-level status.

Job fields include:

- Job ID.
- Job type.
- Status.
- Created by.
- Total items.
- Started at.
- Finished at.
- Created at.

Job item fields include:

- Item ID.
- Job ID.
- Complaint ID.
- Status.
- Attempt count.
- Error message.
- Result payload.
- Attempt history.
- Started at.
- Finished at.

Built job types include:

- Complaint processing jobs.
- Embedding backfill jobs.

Job statuses include queued/running/completed/failed/completed with errors style states.

### 5.5 Full Text Search

The complaint model builds a computed PostgreSQL `TSVECTOR` from:

- Narrative.
- Issue.
- Product.
- Company.
- Category.

The vector uses weighted fields:

- Narrative as high weight.
- Issue/product as medium weight.
- Company/category as lower weight.

A GIN index is added for search performance.

### 5.6 Vector Search Index

The complaint model defines an HNSW cosine index on the embedding field:

- Index name: `ix_complaints_embedding_hnsw_cosine`
- Method: HNSW
- Operator class: `vector_cosine_ops`

This is important for production-style similar-case retrieval.

---

## 6. Backend: Data Ingestion Part

Location examples:

- `backend/app/api/ingestion.py`
- `backend/app/ingestion/cfpb_s3.py`
- `backend/app/schemas/ingestion.py`

### 6.1 S3 CFPB Import APIs

The S3 ingestion API exposes:

- `GET /api/ingestion/s3/options`
- `POST /api/ingestion/s3/preview`
- `POST /api/ingestion/s3/import`

The import route is protected for manager/admin roles.

### 6.2 CSV / ZIP Import Support

The ingestion service can read from S3 objects ending in:

- `.csv`
- `.zip` containing a CSV file

It downloads/streams the object and reads rows using `csv.DictReader`.

### 6.3 CFPB Row Mapping

The mapper converts CFPB row fields into the internal complaint schema.

Mapped fields include:

- Complaint ID.
- Consumer complaint narrative.
- Submitted via.
- Product.
- Sub-product.
- Issue.
- Sub-issue.
- Company.
- Company response.
- Timely response.
- Date received.

Rows without complaint ID or narrative are skipped.

### 6.4 Filtering Built

The S3 import filter system supports:

- Product.
- Sub-product.
- Issue.
- Company.
- Channel.
- Timely response.
- Date received min.
- Date received max.
- Max records.

### 6.5 Preview Built

The preview endpoint can return selected matching rows before import. This is useful for demo and safety because users can inspect data before saving it into PostgreSQL.

### 6.6 Import Built

The import method uses PostgreSQL upsert:

- Inserts complaints in batches of 1000.
- Handles conflicts on `source_complaint_id`.
- Updates existing complaint source fields on conflict.
- Commits imported rows to PostgreSQL.
- Returns import logs.

### 6.7 Athena Mode Built

For very large CFPB CSV files, the service supports Athena query mode.

Athena mode includes:

- Config validation for database/table/output location.
- Safe identifier validation.
- SQL WHERE clause building from filters.
- Query execution.
- Polling until Athena query succeeds/fails/times out.
- Paginated query result reading.
- Distinct filter option discovery.
- Date boundary discovery.
- Filtered row selection using SQL.

If a CSV object is larger than 250 MB and the app is not using Athena mode, the service raises an error requiring Athena setup for filter discovery.

---

## 7. Backend: Complaint Processing Flow

Location: `backend/app/services/processing_service.py`

The processing flow is already complete and production-like.

Flow implemented:

1. Emit WebSocket `received` event.
2. Get or create complaint record.
3. Mark complaint as processing.
4. Start a processing run record.
5. Emit `preprocessing` event.
6. Run local ML layer.
7. Store local signals in processing run.
8. Emit `local_ml` event.
9. Generate embedding for cleaned narrative.
10. Retrieve similar completed complaints using vector search.
11. Store prompt evidence.
12. Emit `bedrock_processing` event.
13. Call Bedrock enrichment.
14. If Bedrock fails, generate fallback enrichment.
15. Emit `validating` event.
16. Run human-review routing decision.
17. Store enrichment on complaint.
18. Store embedding and embedding metadata.
19. Mark complaint as completed or human review.
20. Store AI payload and error category in processing run.
21. Commit database transaction.
22. Emit `saved` or `human_review_required` event.
23. Return processed complaint response.

Failure flow also exists:

- Rolls back DB transaction.
- Attempts to persist a failed complaint outcome.
- Increments retry count.
- Starts failed processing run.
- Emits WebSocket `failed` event.
- Raises the error after logging.

---

## 8. Backend: Human Review Part

Location examples:

- `backend/app/api/review.py`
- `backend/app/services/review_service.py`
- `backend/app/ai/validators/review_router.py`

Built review APIs:

- `POST /api/complaints/{complaint_id}/review/approve`
- `POST /api/complaints/{complaint_id}/review/resolve`
- `POST /api/complaints/{complaint_id}/review/rerun`

Role protection:

- Approve review: Manager/Admin.
- Resolve review: Manager/Admin.
- Rerun review: Agent/Manager/Admin.

Review fields stored on complaint include:

- Human review reason.
- Human review created timestamp.
- Reviewed timestamp.
- Reviewer.
- Review resolution.
- Approved response.
- Review notes.

The processing service automatically routes complaints to human review when review routing returns a reason or when Bedrock failure/invalid output occurs.

---

## 9. Backend: Jobs / Queue / Worker Part

Location examples:

- `backend/app/services/job_service.py`
- `backend/app/api/jobs.py`
- `backend/app/models/processing.py`

### 9.1 Batch Processing Jobs

The backend can create processing jobs for a list of complaint IDs.

Built features:

- Deduplicates complaint identifiers.
- Validates at least one ID.
- Enforces batch processing limit.
- Checks if complaints exist.
- Stores job and job items.
- Processes queued jobs.
- Handles item-level success, human review, and failure.
- Stores result payload per item.

### 9.2 Embedding Backfill Jobs

The backend can create embedding backfill jobs for complaints missing embeddings.

Eligibility includes complaints with statuses:

- Pending.
- Completed.
- Human review.

This is useful when old imported complaints need embeddings for RAG/search.

### 9.3 Retry Support

Failed job items can be retried.

On retry:

- Failed item history is stored.
- Item status is reset to queued.
- Error and result payload are cleared.
- Job status returns to queued.

### 9.4 Abandoned Job Recovery

On app startup, running jobs/items are recovered:

- Running job items are marked failed.
- Running jobs are marked completed with errors.
- Retry is then available.

### 9.5 Background Worker

The FastAPI lifespan starts `ProcessingJobWorker`, which polls for queued jobs and processes them using a database-backed queue.

The README confirms Redis is deliberately not included; this deployment uses one backend instance with in-process WebSocket events and PostgreSQL-backed job worker.

---

## 10. Backend: API / Security Part

Location examples:

- `backend/app/main.py`
- `backend/app/core/security.py`
- `backend/app/api/*.py`

### 10.1 API Framework

FastAPI is used with:

- Router-based modular APIs.
- Pydantic request/response schemas.
- Async DB sessions.
- Central exception handler.
- CORS middleware.

### 10.2 Authentication

Bearer token authentication is implemented through FastAPI `HTTPBearer`.

The backend reads bearer tokens from configured `AUTH_PRINCIPALS_JSON` / settings and converts them into a `Principal` containing:

- `actor`
- `role`

### 10.3 Role Authorization

The backend supports role-based route protection.

Roles used include:

- Agent.
- Manager.
- Admin.

Protected examples:

- Processing routes require Agent/Manager/Admin.
- S3 import requires Manager/Admin.
- Review approve/resolve requires Manager/Admin.
- Review rerun requires Agent/Manager/Admin.

---

## 11. Backend: Complaint Listing / Search Part

Location examples:

- `backend/app/api/complaints.py`
- `backend/app/services/complaint_service.py`
- `backend/app/models/complaint.py`

Built list filters include:

- Limit.
- Offset.
- Sentiment.
- Channel.
- Product.
- Churn risk.
- Urgency min.
- Urgency max.
- Date received min.
- Date received max.
- Timely response.
- AI status.
- Human review reason.
- Search text.
- Sort field.
- Sort direction.

Sort fields include:

- Created at.
- Date received.
- Processed at.
- Urgency score.
- Sentiment.
- Churn risk.
- AI confidence.
- AI status.
- Relevance.

The model-level full-text search vector supports relevance sorting/search.

---

## 12. Backend: Analytics Part

Location examples:

- `backend/app/analytics/router.py`
- `frontend/src/api/client.ts`

The frontend client confirms analytics APIs exist for:

- Complaint trends.
- Product summary.
- Human review trends.
- High urgency complaints.

These endpoints are used by the Analytics page and dashboard summaries.

---

## 13. Backend: SLA Part

Location examples:

- `backend/app/sla/api/routes.py`
- `frontend/src/api/client.ts`

SLA APIs integrated in the frontend include:

- SLA summary.
- SLA by product.
- SLA by channel.
- SLA breach risk.
- SLA trend.

This means the project already has an operations/SLA reporting domain beyond basic complaint processing.

---

## 14. Backend: Duplicate Detection Part

Location examples:

- `backend/app/duplicates/router.py`
- `backend/app/duplicates/repository.py`
- `frontend/src/api/client.ts`

Frontend-integrated duplicate features include:

- Detect duplicates.
- List duplicate groups.
- Read duplicate group.
- Merge duplicate group.
- Reject duplicate group.
- Duplicate channel comparison.

This domain likely supports multichannel complaint duplication analysis.

---

## 15. Backend: Feedback Part

Location examples:

- `backend/app/feedback/router.py`
- `backend/app/feedback/service.py`
- `backend/app/feedback/repository.py`
- `frontend/src/api/client.ts`

Frontend-integrated feedback APIs include:

- Submit/update feedback for a complaint.
- Get feedback for a complaint.
- List recent feedback.
- Export feedback CSV.

This is useful for improving agent workflows and later ML evaluation.

---

## 16. Backend: Export Part

Location examples:

- `backend/app/exports/api/routes.py`
- `backend/app/exports/schemas/export_schemas.py`
- `frontend/src/api/client.ts`

Export download support exists for:

- Complaints CSV.
- Complaints PDF.
- Analytics CSV.
- Feedback CSV.

The backend dependencies include `reportlab`, which is used for PDF export generation.

---

## 17. Backend: WebSocket / Realtime Part

Location examples:

- `backend/app/api/websocket.py`
- `backend/app/websocket/broadcaster.py`
- `backend/app/schemas/websocket.py`
- `frontend/src/App.tsx`

The processing service emits WebSocket events for:

- Received.
- Preprocessing.
- Local ML.
- Bedrock processing.
- Validating.
- Saved.
- Human review required.
- Failed.

The frontend maps these event names into human-readable labels and keeps WebSocket status as:

- Connecting.
- Live.
- Offline.

This is important for demo because judges/users can see complaint processing progress live.

---

## 18. Infrastructure / Deployment Part

Location examples:

- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `infra/nginx/default.conf`
- `infra/aws/guides/`
- `.env.template`

### 18.1 Docker Compose Stack

The Docker Compose stack includes:

- Backend service.
- Frontend service.
- Nginx service.
- Shared Docker network.
- Hugging Face model cache volume.

Backend service:

- Builds from `./backend`.
- Exposes port `8000`.
- Uses `.env` if available.
- Mounts `sentence-transformer-cache` to cache Hugging Face models.
- Has healthcheck against `/api/health`.

Frontend service:

- Builds from `./frontend`.
- Supports Vite API and WebSocket base URL build args.

Nginx service:

- Uses `nginx:1.27-alpine`.
- Depends on backend and frontend.
- Exposes HTTP port 80 by default.
- Uses `infra/nginx/default.conf`.

### 18.2 Nginx Routing

The README says Nginx serves the frontend and forwards:

- `/api`
- `/docs`
- `/openapi.json`
- `/ws`

This gives one local application URL while routing backend traffic properly.

### 18.3 AWS/S3 Material

AWS infra/guides exist, and backend ingestion directly uses:

- S3 bucket.
- CFPB S3 key.
- AWS region.
- Optional Athena database/table/output/workgroup.

---

## 19. Shared Contract Part

Location: `shared/schema/`

The README states there is a shared complaint response contract. The frontend and backend also share strongly aligned response shapes through TypeScript types and Pydantic schemas.

Important shared response concepts include:

- Complaint process request.
- Processed complaint response.
- Complaint detail.
- Complaint list item.
- AI enrichment.
- Similar case evidence.
- Processing job response.
- SLA responses.
- Duplicate responses.
- Feedback responses.

---

## 20. Requirements / Dependencies Built

Backend dependencies include:

- `fastapi`
- `uvicorn[standard]`
- `sqlalchemy[asyncio]`
- `asyncpg`
- `pydantic`
- `pydantic-settings`
- `httpx`
- `python-dotenv`
- `pgvector`
- `boto3`
- `torch` CPU build
- `sentence-transformers`
- `reportlab`

This dependency set confirms the backend is designed for:

- Web APIs.
- Async PostgreSQL.
- Environment-based settings.
- AWS integration.
- Local embeddings.
- Vector search.
- PDF export.

---

## 21. What Is Clearly Already Built

### Backend

- FastAPI app with modular routers.
- Health route.
- Complaint process route.
- Complaint list/detail routes.
- S3 ingestion routes.
- Review routes.
- Jobs routes.
- Feedback routes.
- Duplicate routes.
- Analytics routes.
- Export routes.
- SLA routes.
- WebSocket route.
- Global exception handler.
- CORS middleware.
- Startup checks.
- Background job worker.
- Abandoned job recovery.

### ML / AI

- Local text cleaning.
- Local signal extraction.
- BFSI sentiment model.
- BFSI category classifier.
- Urgency scoring model.
- Confidence combination.
- Bedrock client.
- Prompt builder.
- Retry handler.
- JSON parser.
- Schema validator.
- AI fallback path.
- Human review routing.

### DB

- PostgreSQL async integration.
- Complaint model.
- Processing run model.
- Processing job model.
- Processing job item model.
- JSONB storage.
- pgvector storage.
- HNSW cosine vector index.
- Full-text search vector.
- GIN full-text index.
- Check constraints.
- Upsert-based import.

### RAG / Similar Cases

- MiniLM/sentence-transformer embedding service.
- Embedding validation.
- Similar complaint retrieval.
- Similar case evidence generation.
- RAG evidence passed to Bedrock.

### Ingestion

- Private S3 CFPB source.
- CSV and ZIP reading.
- CFPB field mapper.
- Filter options.
- Preview endpoint.
- Import endpoint.
- Batch upsert.
- Athena mode for large datasets.

### Frontend

- React/Vite dashboard.
- Filters and pagination.
- Live WebSocket processing events.
- S3 import UI integration.
- Queue/job UI integration.
- Analytics integration.
- Operations/SLA integration.
- Duplicate integration.
- Feedback integration.
- Export downloads.
- API key storage.

### Infra

- Docker Compose.
- Backend Docker build.
- Frontend Docker build.
- Nginx reverse proxy.
- Hugging Face cache volume.
- Backend healthcheck.
- AWS/S3/Athena configuration material.

---

## 22. What Still Needs Verification / Possible Pending Work

These items are not confirmed as fully complete from the inspected files and should be checked before final demo or deployment.

### 22.1 Production Authentication Hardening

Bearer token role authentication exists, but before production you should verify:

- Whether static bearer keys are acceptable.
- Whether JWT or OAuth is required.
- Whether tokens are rotated securely.
- Whether frontend API key storage in localStorage is acceptable for your threat model.

### 22.2 Database Migrations

Models are built, but verify whether migration tooling exists and is complete:

- Alembic migration files.
- Initial schema migration.
- pgvector extension creation.
- HNSW index migration.
- GIN index migration.
- Rollback plan.

### 22.3 Bedrock Auth Style

The Bedrock client currently uses an Authorization bearer API key against a Bedrock Converse URL. Verify this matches the actual Bedrock deployment/account method being used, because normal AWS Bedrock Runtime commonly uses AWS SigV4 credentials through AWS SDK-style clients.

### 22.4 Multi-Instance Scaling

The README states the active deployment deliberately uses one backend instance for in-process WebSocket events and PostgreSQL-backed job worker. If scaling to multiple backend replicas, you should verify:

- Job locking behavior under multiple workers.
- WebSocket broadcast behavior across instances.
- Whether Redis/PubSub or another broadcast layer is needed.

### 22.5 Test Coverage

Verify actual test files and coverage for:

- Sentiment edge cases.
- Category mapping.
- Urgency scoring.
- Bedrock invalid JSON.
- Fallback behavior.
- S3 import mapping.
- Athena SQL query generation.
- pgvector retrieval.
- Review state transitions.
- Job retry flow.
- Frontend API error states.

### 22.6 Frontend UX Completion

The frontend APIs and views are wired, but demo readiness should still verify:

- Every route/page renders without runtime errors.
- API key input UX is understandable.
- Empty states are polished.
- Loading and error states are handled.
- WebSocket reconnect behavior is stable.
- Demo data is seeded.

### 22.7 Deployment Secrets

Before deployment, confirm `.env` contains working values for:

- PostgreSQL database URL.
- AWS region.
- S3 bucket.
- CFPB S3 key.
- Athena values if using large dataset filters.
- Bedrock model.
- Bedrock credentials/API key method.
- Auth principals.
- CORS origins.

---

## 23. Recommended Next Documentation Files

To make the repository easier for contributors, create or update these docs next:

1. `docs/ARCHITECTURE.md`
   - Full system architecture with data flow.

2. `docs/API_REFERENCE.md`
   - All backend routes, request bodies, response bodies, auth roles.

3. `docs/ML_PIPELINE.md`
   - Local ML, Bedrock, confidence, fallback, review routing.

4. `docs/DATABASE_SCHEMA.md`
   - Tables, columns, indexes, constraints, relationships.

5. `docs/DEPLOYMENT.md`
   - Docker, AWS, S3, Athena, Bedrock, PostgreSQL setup.

6. `docs/DEMO_SCRIPT.md`
   - Step-by-step hackathon/judge demo flow.

---

## 24. Suggested Demo Story Based on Built Code

A strong demo can be shown like this:

1. Open dashboard through Nginx.
2. Show API health as connected.
3. Import CFPB complaints from private S3 source.
4. Preview filtered complaints before import.
5. Import selected complaints into PostgreSQL.
6. Process one complaint live.
7. Show WebSocket events:
   - Received
   - Preprocessing
   - Local scoring
   - Bedrock analysis
   - Validation
   - Saved / Human review
8. Open processed complaint detail.
9. Show sentiment, category, urgency, churn risk, AI confidence, reasoning, draft response, next action.
10. Show similar cases from vector retrieval.
11. Trigger a batch processing job.
12. Show queue/job status.
13. Show human review approval/resolution.
14. Show analytics page.
15. Show SLA page.
16. Show duplicate detection.
17. Export report as CSV/PDF.

This demo will communicate that CustomerPulse is not just an AI prompt wrapper. It is a complete operational complaint-intelligence platform.

---

## 25. Final Build Status Summary

Current build maturity appears high.

The repository already contains:

- Real backend architecture.
- Real database models.
- Real ingestion pipeline.
- Real local ML layer.
- Real Bedrock integration layer.
- Real RAG/similar-case retrieval.
- Real batch worker.
- Real review workflow.
- Real frontend integration.
- Real infra/deployment setup.

The biggest remaining work is likely not core feature creation, but verification, polishing, production hardening, migration reliability, demo data preparation, and deployment validation.
