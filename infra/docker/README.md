# Docker Stack

## Services

- `backend`: FastAPI app on container port `8000`.
- `frontend`: React/Vite application served by Nginx.
- `nginx`: Reverse proxy on port `80`.

The backend runs one in-process job worker backed by PostgreSQL job tables and
uses its existing in-memory WebSocket broadcaster. Keep one backend instance
for the current demonstration deployment; Redis is intentionally not used.

## Local Run

Create `.env` first:

```bash
cp .env.template .env
```

Fill real values, then run:

```bash
docker compose build
docker compose run --rm backend python -m app.db.setup --yes --verify-embedding
docker compose up -d
```

Backend startup runs Phase 1 checks before serving traffic:

- PostgreSQL connection.
- Target database.
- `pgvector`.
- `complaints` table and indexes.
- Processing audit/job tables, feedback and duplicate tables, full-text GIN index, and pgvector HNSW cosine index.
- Basic row permissions.
- AWS Bedrock model access.

The setup command installs Python requirements including `sentence-transformers`
and `reportlab`, downloads/caches `all-MiniLM-L6-v2` in the
`sentence-transformer-cache` Docker volume, and verifies the model returns
384-dimensional embeddings. Configure API-key roles with
`AUTH_PRINCIPALS_JSON`; protected processing, review, job, feedback-list,
duplicate-action, and export endpoints require bearer credentials. In the
frontend, open **Operations** and save a bearer key locally in the browser
before calling protected backend actions. Do not pass manager/admin keys as
Vite build arguments because those values are embedded into static assets.

When building an image in an environment that can access Hugging Face, the model
can also be baked into the backend image:

```bash
PRELOAD_EMBEDDING_MODEL=true docker compose build backend
```

For ordinary local work, keep `PRELOAD_EMBEDDING_MODEL=false` and let the setup
command populate the cache volume.

If Docker is running without an interactive terminal, prepare the database first:

```bash
cd backend
python -m app.db.setup --yes --verify-embedding
```

Backend health endpoint:

```bash
http://localhost/api/health
```

Direct backend port, if `BACKEND_PORT` is left as default:

```bash
http://localhost:8000/api/health
```

Backend verification:

```bash
bash backend/scripts/run_backend_checks.sh
```
