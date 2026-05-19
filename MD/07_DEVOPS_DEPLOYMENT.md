# DevOps Deployment Tracker

## Implemented

- Root `docker-compose.yml`.
- Backend container build from `backend/Dockerfile`.
- Redis service for Phase 2 pub/sub readiness.
- Nginx reverse proxy for `/api`, `/docs`, `/openapi.json`, and `/ws`.
- EC2 Docker bootstrap script.
- EC2 deploy script.
- AWS deployment notes.

## Environment Rules

- Real secrets belong only in `.env` or AWS-managed environment injection.
- `.env.template` documents required values.
- RDS should not be publicly open.
- Nginx should be the public HTTP entrypoint.

## Pending For Sparsh

- Add HTTPS/TLS once domain is available.
- Add frontend container after Atharva's frontend folder is merged.
- Add CI/CD workflow after branch protection is finalized.
- Add CloudWatch or external log monitoring if time allows.
