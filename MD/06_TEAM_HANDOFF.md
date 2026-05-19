# Team Handoff

## Harsh
Owns backend, AI pipeline, Claude integration, validation, WebSockets, and AI enrichment fields.

## Yash
Owns CFPB ingestion and raw complaint insertion. Align raw data fields with `backend/app/models/complaint.py`.

## Atharva
Consumes:

- `POST /api/process`
- `GET /api/complaints`
- `GET /api/search`
- WebSocket `/ws`

Frontend should not rely on mock backend records once the real DB is connected.

## Sparsh
Owns Docker, AWS EC2, RDS connectivity, environment injection, Nginx, and deployment.

Deployment must provide real environment variables. The backend does not contain committed secrets.
