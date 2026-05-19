# CustomerPulse

Phase 1 runs the backend and frontend locally while using PostgreSQL for real complaint storage and the OpenAI API for AI enrichment.

Backend setup is automatic on startup, and can also be run manually:

```bash
cd backend
python -m app.db.setup
```

Fill `.env` from `.env.template` before running the backend. Set `OPENAI_API_KEY` to your real key. Never commit real secrets.

The shared API contract lives at `shared/schema/complaint.schema.json`.
