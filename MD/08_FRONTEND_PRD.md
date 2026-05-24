# CustomerPulse Frontend PRD

## Summary
Build a production-ready React dashboard for CustomerPulse that visually follows the uploaded TeamHub-style reference: soft mint canvas, fixed sidebar, dense dashboard cards, rounded white panels, compact charts, a right-side operations column, and mobile-friendly stacked views. The frontend must connect to the existing FastAPI backend and must not ship mock complaint rows, temporary fixtures, or simulated dashboard data.

## Goals
- Render real complaint intelligence from `GET /api/complaints`, including its `search` query parameter.
- Let users submit a real complaint through `POST /api/process` and watch backend WebSocket progress from `/ws`.
- Show operational metrics, confidence, urgency, sentiment, churn risk, and processing status from backend responses only.
- Preserve honest loading, empty, and error states when the backend, database, or AWS Bedrock Claude enrichment are unavailable.
- Prepare the frontend for local Vite development and deployment against an externally managed backend.

## Non-Goals
- No frontend seed data, fake demo complaints, placeholder API responses, or static fallback rows.
- No frontend-only simulation of AI output, charts, channel comparison, or payroll-style panels.
- No assumptions about backend API changes without updating the frontend types and the backend-owned API contract.

## Users
- Support agents need a queue, complaint detail, recommended actions, and draft response visibility.
- Managers need KPI cards, urgency/churn summaries, trend views, and live processing state.
- Demo judges need to see that all records come from real backend/database calls.

## Product Requirements
- Dashboard shell must include a brand sidebar, search bar, action icons, compact user/status area, KPI cards, table, detail panel, intake form, charts, and live activity stream.
- Complaint list must support search, sentiment, churn risk, urgency band, timely response, sort field, sort direction, limit, offset, and refresh.
- Metrics must be derived from the currently fetched backend records and total count returned by the backend.
- Charts must use fetched complaint data only. If no records exist, show an empty chart state.
- Complaint detail must show the selected real row. If no row exists, show a clear empty state.
- Intake form must create a generated `complaint_id` only at submit time and send user-entered narrative/channel/product/issue/company to `POST /api/process`.
- Process results must display only the backend response. Failed AI/backend calls must show an error state, not generated fallback content.
- WebSocket events must connect to `/ws`, show connection status, and append real backend event messages.
- Frontend API base URL must be configurable through `VITE_API_BASE_URL`; same-origin `/api` and `/ws` remain valid when hosting provides a reverse proxy.

## Interface Contract
- Source of truth: `shared/schema/complaint.schema.json`; frontend types must be revised when that contract changes.
- REST endpoints used:
  - `GET /api/health`
  - `GET /api/complaints`
  - `POST /api/process`
  - `POST /api/process/{complaint_id}` for an imported row
- WebSocket endpoint used:
  - `/ws`
- Frontend types must model nullable backend fields and avoid assuming AI fields exist before processing.

## Visual Direction
- Use a pale mint page background with white rounded panels and subtle shadows.
- Use a fixed desktop sidebar and a compact mobile sidebar strip.
- Keep cards dense and operational, closer to an internal dashboard than a landing page.
- Use teal/mint accents, restrained neutral text, circular progress visuals, compact bars, and readable data tables.
- Ensure all panels have stable dimensions and responsive wrapping so text does not overlap.

## Acceptance Criteria
- A clean install and build succeeds for `frontend`.
- With backend reachable and real data present, the dashboard renders complaint rows and derived metrics.
- With backend reachable but no rows, the UI shows empty states and no fake rows.
- With backend unreachable, the UI shows connection errors without crashing.
- Submitting the intake form calls `POST /api/process` and displays the returned backend result.
- WebSocket progress uses backend events only.
- The deployed frontend can reach the external backend through configured API/WebSocket URLs or a hosting-level reverse proxy.
