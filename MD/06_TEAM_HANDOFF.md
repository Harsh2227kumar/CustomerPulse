# Team Handoff

## Harsh
Owns backend, AI pipeline, OpenAI integration, validation, WebSockets, AI enrichment fields, and the automatic Phase 1 startup/setup checks.

Phase 1 backend startup now verifies database/schema readiness, row permissions, and OpenAI model access before serving API requests.

## Yash
Owns CFPB ingestion and raw complaint insertion.

Yash must align raw data fields with `backend/app/models/complaint.py` and confirm the database user can connect, create/use the `customerpulse` database, create `pgvector`, and read/write `complaints` rows. If the app user cannot create the database, provide `DATABASE_ADMIN_URL` for setup.

## Atharva
Consumes:

- `POST /api/process`
- `GET /api/complaints`
- `GET /api/search`
- WebSocket `/ws`

Frontend should not rely on mock backend records once the real DB is connected.

The shared schema is `shared/schema/complaint.schema.json`. Treat it as the single source of truth before changing frontend types or API response assumptions.

Backend may take longer on startup because it runs database and OpenAI readiness checks before accepting frontend traffic.

## Sparsh
Owns Docker, EC2 or other hosting, database connectivity, environment injection, Nginx, and deployment.

Deployment must provide real environment variables. The backend does not contain committed secrets.

On EC2, put `OPENAI_API_KEY` in a managed secret source or deployment-only `.env`. If terminal prompts are unavailable in a hosted environment, run `python -m app.db.setup` during deployment or ensure the database/schema already exists before starting the backend.
