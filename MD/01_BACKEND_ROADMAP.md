# Backend Roadmap

## Goal
Build the CustomerPulse AI backend intelligence layer with real FastAPI, PostgreSQL, Claude, validation, and live update support. No fake complaint records, fixtures, or simulated dashboard data should be added.

## Phase 1
- FastAPI application scaffold.
- Environment-only configuration.
- Async SQLAlchemy PostgreSQL session.
- Complaint model with AI enrichment fields.
- `POST /api/process`.
- `GET /api/complaints`.
- `GET /api/search`.
- `GET /api/health`.
- Claude integration with strict JSON validation.
- Basic deterministic NLP and local scoring.

## Phase 2
- WebSocket live processing updates.
- Redis pub/sub integration.
- Similar complaint engine using embeddings and pgvector.

## Phase 3
- Churn prediction improvements.
- SLA prediction.
- Emotion timeline.
- Continuous learning workflow.
