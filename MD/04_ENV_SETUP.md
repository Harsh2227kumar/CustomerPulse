# Environment Setup

Copy `.env.template` to `.env` locally and fill real values.

Required:

- `DATABASE_URL`: async PostgreSQL URL, for example `postgresql+asyncpg://USER:PASSWORD@HOST:5432/customerpulse`.
- `ANTHROPIC_API_KEY`: real Anthropic key.
- `ANTHROPIC_MODEL`: defaults to `claude-3-5-sonnet-latest`.
- `CORS_ORIGINS`: comma-separated frontend origins.

Optional:

- `REDIS_URL`: reserved for Phase 2 pub/sub.
- `VECTOR_DIMENSIONS`: defaults to `384`.
- `AI_MAX_RETRIES`: defaults to `2`.
- `AI_TIMEOUT_SECONDS`: defaults to `30`.

Never commit `.env`.
