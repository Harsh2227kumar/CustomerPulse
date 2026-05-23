# Backend File Map

## Core
- `backend/app/main.py`: FastAPI app, middleware, router registration, and startup checks.
- `backend/app/core/config.py`: Pydantic settings from environment, including database, optional admin DB URL, and AWS Bedrock values.
- `backend/app/core/constants.py`: shared enums.
- `backend/app/core/logging.py`: logging setup.

## Database
- `backend/app/db/session.py`: async SQLAlchemy engine and session dependency.
- `backend/app/db/base.py`: declarative base.
- `backend/app/db/init_db.py`: extension creation, table creation, DB check.
- `backend/app/db/setup.py`: automatic Phase 1 setup and verification command for database creation, schema, indexes, permissions, and Bedrock readiness.
- `backend/app/models/complaint.py`: raw complaint plus AI enrichment fields.

## API
- `backend/app/api/process.py`: `POST /api/process`.
- `backend/app/api/complaints.py`: `GET /api/complaints`.
- `backend/app/api/search.py`: `GET /api/search`.
- `backend/app/api/health.py`: `GET /api/health`.
- `backend/app/api/websocket.py`: `/ws`.

## AI
- `backend/app/ai/preprocessing/`: text cleaning, extraction, prompt compression.
- `backend/app/ai/ml_models/`: lightweight local scoring hooks.
- `backend/app/ai/bedrock/`: AWS Bedrock client, prompt, parser, retry.
- `backend/app/ai/validators/`: JSON/schema/confidence/output guards.
- `backend/app/ai/pipelines/complaint_pipeline.py`: full complaint enrichment pipeline.
- `backend/app/ai/embeddings/`: sentence-transformers generation and pgvector similarity helpers.

## Services
- `backend/app/services/processing_service.py`: DB-backed processing orchestration.
- `backend/app/services/complaint_service.py`: dashboard list/filter queries.
- `backend/app/services/search_service.py`: keyword search entry point.
- `backend/app/utils/`: shared backend utility helpers.

## Shared Contract
- `shared/schema/complaint.schema.json`: team-visible complaint API contract for backend, frontend, ingestion, and DevOps coordination.
