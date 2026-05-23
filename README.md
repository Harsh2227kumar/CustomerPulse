# CustomerPulse Frontend

React/Vite interface for CustomerPulse complaint operations and controlled S3 import. This branch contains frontend assets and frontend-specific documentation only.

The UI consumes an external CustomerPulse backend configured for PostgreSQL and AWS Bedrock Claude enrichment. Backend source, cloud infrastructure, service credentials, and deployment composition intentionally do not live in this branch.

## Run Locally

```bash
cd frontend
npm install
npm run dev
```

Configure endpoints in `frontend/.env` when the backend is not exposed through the same origin:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

`VITE_API_BASE_URL` may remain empty in deployments that proxy `/api` to the external backend on the same host.

To build and run the frontend container with external backend endpoints:

```bash
docker compose --env-file .env.template up --build
```
