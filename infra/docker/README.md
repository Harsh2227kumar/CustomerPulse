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

Backend health endpoint:

```bash
http://localhost/api/health
```

Direct backend port, if `BACKEND_PORT` is left as default:

```bash
http://localhost:8000/api/health
```
