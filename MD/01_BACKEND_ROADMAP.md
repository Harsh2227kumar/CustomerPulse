# Backend Roadmap

## Goal
Build the CustomerPulse AI backend intelligence layer with real FastAPI, PostgreSQL, OpenAI API enrichment, validation, and live update support. No fake complaint records, fixtures, or simulated dashboard data should be added.

## Phase 1
- FastAPI application scaffold.
- Environment-only configuration.
- Async SQLAlchemy PostgreSQL session.
- Automatic startup/setup checks for database connection, database, `pgvector`, schema, indexes, permissions, and OpenAI API access.
- Complaint model with AI enrichment fields.
- `POST /api/process`.
- `GET /api/complaints`.
- `GET /api/search`.
- `GET /api/health`.
- OpenAI integration with strict JSON validation.
- Basic deterministic NLP and local scoring.
- Shared JSON schema contract in `shared/schema/complaint.schema.json`.

## Phase 1 Setup Flow
- Local backend and frontend run against PostgreSQL and OpenAI.
- Backend startup runs setup checks before serving requests.
- If the target database, `vector` extension, `complaints` table, or indexes are missing, startup asks in the terminal before creating them.
- Manual setup can also be run with `python -m app.db.setup` from the `backend` folder.
- `DATABASE_ADMIN_URL` is optional and only needed when the app DB user cannot create the target database.

## Phase 2
- WebSocket live processing updates.
- Redis pub/sub integration.
- Similar complaint engine using embeddings and pgvector.
- PostgreSQL `ts_vector` full-text search with GIN indexes.

## Phase 3
- Churn prediction improvements.
- SLA prediction.
- Emotion timeline.
- Continuous learning workflow.
