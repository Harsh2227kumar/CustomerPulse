# CustomerPulse

Integration branch for testing the CustomerPulse frontend, FastAPI backend, AWS infrastructure configuration, and shared API contract together before promotion to `main`.

## Integrated Services

- `frontend/`: React/Vite dashboard and controlled CFPB S3 import UI.
- `backend/`: FastAPI service with PostgreSQL storage and AWS Bedrock Claude enrichment.
- `infra/`: Nginx routing and AWS/S3 deployment material.
- `shared/schema/`: shared complaint response contract.

## Local Integration Setup

1. Copy `.env.template` to `.env` and provide real PostgreSQL, AWS Bedrock, and private S3 configuration values.
2. Ensure the configured PostgreSQL schema is ready by running backend setup when required:

```bash
cd backend
python -m app.db.setup
```

3. Start the integrated stack:

```bash
docker compose up --build
```

Open the application through Nginx at `http://localhost`. Nginx serves the frontend and forwards `/api`, `/docs`, `/openapi.json`, and `/ws` to the backend.

## Branch Flow

Feature branches are integrated into `dev` through a reviewed pull request. After tester approval on `dev`, a separate reviewed pull request can promote the tested result to `main`.

## Security

Never commit `.env`, database passwords, Bedrock keys, AWS credentials, or generated dependency/build directories.
