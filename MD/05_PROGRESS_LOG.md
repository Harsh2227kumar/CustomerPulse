# Progress Log

## 2026-05-20

Switched the Phase 1 AI provider to AWS Bedrock:

- Replaced the AI runtime with `backend/app/ai/bedrock/`.
- Removed the old provider package and old provider dependencies.
- Added Bedrock API-key settings for `AI_PROVIDER=bedrock`.
- Backend startup now checks database readiness and Bedrock access before serving requests.
- Updated `.env.template`, API docs, setup docs, DevOps notes, and handoff docs for Bedrock.
- Kept PostgreSQL, `pgvector`, complaint schema setup, and strict Pydantic validation.
- Added the missing `similar_cases` API field, complaint list `date_received` / `timely_response` fields, date/timely filters, and shared JSON schema contract.

Verification:

- Python AST syntax check passed for backend files.
- Pydantic schema checks passed for required-string cleanup and `similar_cases`.
- `git diff --check` passed.
- Full import/server verification is pending until backend dependencies are installed in the active Python environment.

Next:

- Run `py -m pip install -r requirements.txt` in `backend`.
- Add a real `BEDROCK_API_KEY` from the user2 AWS account to local `.env`.
- Run `py -m app.db.setup` with real `.env`.
- Start FastAPI and test `/api/health`, `/api/process`, `/api/complaints`, and `/api/search`.

## 2026-05-19

Implemented initial backend foundation:

- FastAPI backend package.
- Environment-based config.
- Async SQLAlchemy PostgreSQL session.
- Complaint model with AI enrichment fields.
- Pydantic request/response schemas.
- API routes for processing, complaints, search, health, and WebSocket.
- AI integration skeleton with strict JSON parsing and validation.
- NLP preprocessing and deterministic local scoring layer.
- Service layer for processing and complaint listing.
- WebSocket connection manager and broadcaster.
- pgvector helper structure for future similar complaint search.
- Backend requirements, Dockerfile, env template, and documentation.

Original pending integration:

- Real shared database URL from Yash/Sparsh.
- Real Bedrock key and model access from Harsh/team.
- Confirm final raw complaint table alignment with Yash ingestion.
- Add Redis pub/sub and pgvector similarity API after base flow is tested.

## DevOps Update

- Added Docker Compose stack.
- Added Nginx reverse proxy config.
- Added EC2 bootstrap and deploy scripts.
- Added deployment tracker documentation.
