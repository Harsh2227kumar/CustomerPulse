# Docker Stack

## Services

- `backend`: FastAPI app on container port `8000`.
- `redis`: Redis 7 for future WebSocket pub/sub and background event distribution.
- `nginx`: Reverse proxy on port `80`.

## Local Run

Create `.env` first:

```bash
cp .env.template .env
```

Fill real values, then run:

```bash
docker compose up --build
```

Backend startup runs Phase 1 checks before serving traffic:

- PostgreSQL connection.
- Target database.
- `pgvector`.
- `complaints` table and indexes.
- Basic row permissions.
- OpenAI model access.

If Docker is running without an interactive terminal, prepare the database first:

```bash
cd backend
python -m app.db.setup
```

Backend health endpoint:

```bash
http://localhost/api/health
```

Direct backend port, if `BACKEND_PORT` is left as default:

```bash
http://localhost:8000/api/health
```
