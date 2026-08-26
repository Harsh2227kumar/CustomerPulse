# CustomerPulse

**An AI-powered, audit-ready complaint intelligence platform for banking & BFSI operations.**

CustomerPulse ingests customer complaints from multiple channels, enriches each one with a hybrid AI pipeline (local ML signals + Amazon Bedrock, grounded by retrieval-augmented generation), and drives the full resolution lifecycle — triage, similar-case reuse, SLA tracking, auto-escalation, explainable regulatory reporting, and a human-in-the-loop review workflow — through a real-time Next.js dashboard.

<div align="center">

[![Backend Tests](https://img.shields.io/github/actions/workflow/status/Harsh2227kumar/CustomerPulse/backend-tests.yml?branch=main&style=for-the-badge&label=Backend%20Tests&logo=githubactions&logoColor=white&color=2ea44f)](https://github.com/Harsh2227kumar/CustomerPulse/actions/workflows/backend-tests.yml)

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon%20Bedrock-Claude-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

</div>

> 🏆 **Top 30 Finalist — Union Bank of India IDEA 2.0 National Hackathon.**
> Built for the problem statement *"Unified Customer Complaint Communication Dashboard"*: a Gen-AI system that categorizes complaints, detects duplicates, drafts compliant responses, tracks SLAs, escalates critical cases, and produces regulatory-ready reporting.

---

## Table of Contents

- [Why CustomerPulse](#why-customerpulse)
- [Key Features](#key-features)
- [What Makes It Different](#what-makes-it-different)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quickstart (Docker Compose)](#quickstart-docker-compose)
  - [Manual Local Development](#manual-local-development)
  - [Configuration](#configuration)
  - [Database Migrations & Seeding](#database-migrations--seeding)
  - [Running Tests](#running-tests)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Getting Help](#getting-help)
- [Maintainers & Credits](#maintainers--credits)
- [License](#license)

---

## Why CustomerPulse

Banks handle enormous volumes of complaints across email, web, phone, social, and regulator feeds (e.g. CFPB). Manual triage is slow, inconsistent, and hard to audit — a serious problem in a domain where every customer response can carry regulatory weight.

CustomerPulse turns that firehose into structured, actionable, and **traceable** work:

- **Resolve faster** — every complaint arrives pre-classified with sentiment, category, urgency, churn risk, a suggested next action, and a ready-to-edit draft response.
- **Stay compliant** — AI output is grounded in retrieved evidence, guarded against hallucination, and backed by reason codes and evidence mapping, so every decision can be explained to an auditor or regulator.
- **Never miss an SLA** — built-in SLA tracking and rule-based auto-escalation surface breach-risk cases before they slip.
- **Cut duplicate effort** — vector similarity detects duplicate and related complaints and lets agents safely reuse proven resolutions.
- **Keep humans in control** — low-confidence or high-risk cases are automatically routed to a human review queue instead of being auto-sent.

---

## Key Features

| Domain | Capabilities |
| --- | --- |
| **Omnichannel Ingestion** | CFPB dataset import from private **Amazon S3** (CSV or large-scale **Athena** query mode), web intake, and an optional IMAP **email intake** worker; upsert-based persistence with a filterable preview before import. |
| **Hybrid AI Enrichment** | Local rule-based ML (sentiment, category, urgency, confidence) fused with **Amazon Bedrock** (Claude) for churn risk, next actions, and customer-ready draft responses — with validation, retries, and timeouts. |
| **RAG (dual surface)** | (1) **Similar-case retrieval** over past complaints via pgvector cosine similarity to ground draft responses and enable safe resolution reuse; (2) **regulatory-document RAG** with multi-format ingestion and chunking for a compliance research workspace. |
| **Duplicate Detection** | Embedding-based duplicate/related-complaint grouping with merge/reject actions and cross-channel comparison. |
| **Complaint Workflow** | 360° complaint view, full communication timeline, agent notes, rule-based **auto-escalation** + manual escalation, and a prioritized **operations queue**. |
| **SLA & Analytics** | SLA summary, by-product, by-channel, breach-risk, and trend reporting; complaint trends, product summaries, high-urgency and human-review analytics. |
| **Explainable Compliance** | Rule registry, risk aggregation, reason codes, evidence mapping, and regulatory report serialization with **PDF export**. |
| **Human-in-the-Loop Review** | Confidence and hallucination validators route uncertain cases to a review queue; agents approve, edit, resolve, or re-run. |
| **Real-Time & Durable** | Live **WebSocket** processing events and a **PostgreSQL-backed job queue** with abandoned-job recovery — no Redis required. |
| **Access Control** | JWT authentication with role-based access (agent, manager, admin, super-admin), employee management, monitoring, and an audit trail. |

---

## What Makes It Different

Most hackathon complaint tools stop at "classify text with an LLM." CustomerPulse is built like a system a regulated bank could actually run:

1. **Grounded, guarded generation — not raw LLM output.** Draft responses are produced only after relevant past cases are retrieved via pgvector and injected as *bounded evidence*. A dedicated hallucination guard and confidence validator reject vague or unsafe output, and anything risky is escalated to a human instead of sent. Safety is a pipeline stage, not an afterthought.

2. **Every AI decision is explainable and auditable.** A rule registry, reason codes, risk justifier, and evidence mapper mean each classification, escalation, and regulatory report can be traced back to concrete inputs and rules — the difference between a demo and something that survives a compliance review.

3. **Hybrid intelligence that respects cost and latency.** Cheap, deterministic local ML handles the signals it does well (sentiment, urgency, category, confidence); the expensive LLM is reserved for where it genuinely adds value. The result is faster, cheaper, and more predictable than an LLM-only design.

4. **Production posture from day one.** Async FastAPI + SQLAlchemy 2.0, Alembic migrations, Dockerized services behind an Nginx reverse proxy, container health checks, a durable Postgres-backed worker, CI on every push, and full AWS deployment runbooks (RDS, Bedrock, S3, Athena, IAM, EC2).

5. **Real banking data, real scale considerations.** Ingests the public CFPB complaint corpus directly from S3, with an Athena mode for filtering large CSVs without loading them into memory.

---

## Architecture

```mermaid
---
config:
  layout: elk
  theme: neo
  look: neo
---
flowchart TB
 subgraph OUTER[" "]
 direction TB
 subgraph Sources["Complaint Sources"]
        S3["CFPB via Amazon S3 / Athena"]
        WEB["Web Intake"]
        MAIL["Email Intake (IMAP)"]
  end
 subgraph Backend["FastAPI Backend (async)"]
        ING["Ingestion + Upsert"]
        PIPE["AI Pipeline"]
        ML["Local ML Signals<br>(sentiment · urgency · category)"]
        RAG["pgvector RAG<br>Similar-Case Retrieval"]
        BR["Amazon Bedrock<br>(Claude enrichment)"]
        GUARD["Validators & Hallucination Guard"]
        WORK["Workflow<br>escalation · SLA · duplicates · review"]
        JOBS["Durable Job Worker<br>(PostgreSQL-backed)"]
  end
    Sources --> ING
    ING --> PIPE
    PIPE --> ML & RAG
    ML --> GUARD
    RAG --> BR
    BR --> GUARD
    GUARD --> WORK
    WORK --> DB[("PostgreSQL + pgvector")] & WS(["WebSocket live events"])
    RAG <--> DB
    JOBS --> PIPE
    WS --> UI["Next.js Dashboard"]
    UI -- REST /api --> Backend
    Nginx["Nginx reverse proxy"] --- UI & Backend
 end
 style OUTER fill:#ffffff,stroke:#ffffff,stroke-width:0px
```

Requests reach an **Nginx reverse proxy** that serves the frontend and forwards `/api`, `/docs`, `/openapi.json`, and `/ws` to the backend. Complaints flow through ingestion into the AI pipeline, which combines local ML and RAG-grounded Bedrock enrichment, passes through validators, and lands in PostgreSQL — broadcasting live progress to the dashboard over WebSockets.

> **Note on diagram size:** Mermaid/GitHub auto-sizes the rendered SVG to fit its content — there's no literal "window height" property to set. To make the diagram render roughly twice as tall, the `rankSpacing`/`nodeSpacing`/`padding` values above have been doubled from Mermaid's typical defaults (~80/50/20 → 160/100/40). If you want it taller or shorter still, scale those three numbers up or down together.

---

## Tech Stack

| Layer | Technologies |
| --- | --- |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, ECharts |
| **Backend** | FastAPI, async SQLAlchemy 2.0, Pydantic v2, Uvicorn, WebSockets |
| **Database** | PostgreSQL + `pgvector`, Alembic migrations, `asyncpg` |
| **AI / ML** | Amazon Bedrock (Claude) via `boto3`, `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim), local rule-based classifiers |
| **Documents** | `pymupdf4llm`, `mammoth` (multi-format → markdown for regulatory RAG), `reportlab` (PDF exports) |
| **Infrastructure** | Docker & Docker Compose, Nginx, AWS (RDS, Bedrock, S3, Athena, EC2), GitHub Actions CI/CD |

---

## Getting Started

### Prerequisites

Choose one of the following paths:

- **Docker path (recommended):** Docker and Docker Compose.
- **Manual path:** Python 3.11+, Node.js 20+, and PostgreSQL 16 with the `pgvector` extension available.

You will also need **AWS credentials** with access to Amazon Bedrock (and, for real CFPB import, an S3 bucket). For local UI/backend work you can skip Bedrock/S3 — see the notes below.

### Quickstart (Docker Compose)

```bash
# 1. Clone
git clone https://github.com/Harsh2227kumar/CustomerPulse.git
cd CustomerPulse

# 2. Configure environment
cp .env.template .env
#   → edit .env with your PostgreSQL, Bedrock, and S3 values

# 3. Build and run the full stack (backend + frontend + Nginx)
docker compose up --build
```

Then open **http://localhost** — Nginx serves the dashboard and proxies the API. Interactive API docs are at **http://localhost/docs**.

### Manual Local Development

**Backend**

```bash
cd backend

# Guided setup: creates a venv, installs deps, prepares the DB schema,
# and downloads/caches the MiniLM embedding model (verifies 384-dim output).
VERIFY_EMBEDDING=true bash scripts/setup_backend.sh      # Linux/macOS
# or on Windows PowerShell:
#   backend\scripts\setup_backend.ps1 -VerifyEmbedding

# Run the API (http://localhost:8000, docs at /docs)
uvicorn app.main:app --reload --port 8000
```

To skip Bedrock while doing local infra/UI work, use `SKIP_BEDROCK=true` (or `-SkipBedrock` on PowerShell).

**Frontend**

```bash
cd frontend
npm install

# Point the app at your backend
export NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
export NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000

npm run dev   # http://localhost:3000
```

### Configuration

All configuration is via environment variables (loaded from `.env`). Copy [`.env.template`](.env.template) and fill in the values. The most important keys:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | PostgreSQL async URL, e.g. `postgresql+asyncpg://user:pass@host:5432/postgres` |
| `BEDROCK_API_KEY` / `BEDROCK_REGION` / `BEDROCK_MODEL` | Amazon Bedrock credentials and model (default `claude-sonnet-4`) |
| `S3_BUCKET_NAME` / `CFPB_S3_KEY` / `AWS_REGION` | CFPB dataset location; set `CFPB_INGESTION_MODE=csv` or `athena` |
| `EMBEDDING_MODEL` | Sentence-transformer model (default `all-MiniLM-L6-v2`) |
| `SIMILARITY_THRESHOLD` / `SIMILAR_CASE_LIMIT` | RAG retrieval tuning for similar-case grounding |
| `JWT_SECRET_KEY` | 32+ character secret for auth tokens (required outside development) |
| `AUTH_USERS_JSON` | Bootstrap/fallback users and roles (replace all sample keys) |
| `EMAIL_INTAKE_ENABLED` + `EMAIL_INTAKE_*` | Enable and configure the optional IMAP email intake worker |
| `NEXT_PUBLIC_API_BASE_URL` / `NEXT_PUBLIC_WS_BASE_URL` | Frontend → backend endpoints |

> **Security:** Never commit `.env`, database passwords, Bedrock keys, or AWS credentials. Replace every sample key in `.env.template` before deploying.

### Database Migrations & Seeding

```bash
cd backend
alembic upgrade head                 # apply schema migrations (requires pgvector)
python scripts/download_embedding_model.py   # cache the embedding model offline
python scripts/seed_admin.py         # bootstrap the first super-admin (if empty)
```

### Running Tests

```bash
cd backend
bash scripts/run_backend_checks.sh   # full suite (or run_backend_checks.ps1 on Windows)
# or directly:
pytest
```

CI runs the backend test suite (with compliance coverage) on every push and pull request to `main`/`dev`.

---

## Usage

1. **Sign in.** The dashboard requires authentication. Sample development users ship in `.env.template` (`admin` / `Admin@123`, `manager` / `Manager@123`, `agent` / `Agent@123`) — **change these before any real deployment.**
2. **Import complaints.** Use the **Import** page to preview and import CFPB data from S3, or submit a complaint from **New Complaint**.
3. **Watch processing live.** The AI pipeline enriches each complaint; progress streams into the UI over WebSockets.
4. **Work the queue.** The **Operations** and **Queue** views prioritize human-review, high-urgency, and escalated cases. Open any complaint for its **360° view**, timeline, similar cases, and an editable draft response.
5. **Track and report.** Use **Insights** for analytics/SLA and the **Regulatory RAG** workspace for compliance research and explainable reporting (with PDF export).

The frontend routes map to these areas: `dashboard`, `import`, `new-complaint`, `queue`, `operations`, `insights`, `regulatory-rag`, and `admin`.

**Selected API endpoints** (full interactive reference at `/docs`):

```text
GET  /api/health                          Service health
POST /api/process                         Enrich a complaint through the AI pipeline
GET  /api/complaints                      List/filter complaints
GET  /api/complaints/{id}/360             Consolidated 360° complaint view
POST /api/complaints/{id}/escalate        Manually escalate a complaint
GET  /api/operations/queue                Prioritized agent work queue
GET  /api/escalations                     List/manage escalations
GET  /api/analytics/...                   Trends, product & review analytics
GET  /api/sla/...                         SLA summary, breach risk, trends
WS   /ws                                  Live processing events
```

The complete, frozen backend contract lives in [`backend/API_CONTRACT_PHASE2.md`](backend/API_CONTRACT_PHASE2.md).

---

## Project Structure

```text
CustomerPulse/
├── frontend/              # Next.js 16 dashboard (App Router, TypeScript, Tailwind)
├── backend/               # FastAPI service
│   └── app/
│       ├── ai/            # pipeline, Bedrock client, ML signals, validators, guardrails
│       ├── intelligence/  # similarity policy, evidence, reason codes, recommendations
│       ├── compliance/    # rule registry, explainability, reporting, regulatory RAG
│       ├── ingestion/     # CFPB S3/Athena, email intake
│       ├── services/      # processing, retrieval (RAG), jobs, embeddings, review
│       ├── analytics/ · duplicates/ · escalations/ · sla/ · exports/ · feedback/
│       ├── communications/# timeline & 360° workspace
│       ├── employees/     # auth, RBAC, monitoring
│       └── websocket/     # live event broadcaster
├── infra/                 # Nginx config + AWS deployment scripts & guides
├── shared/schema/         # Shared complaint response contract (JSON Schema)
└── docker-compose.yml     # backend + frontend + Nginx
```

---

## Documentation

- [Build audit — everything implemented, by domain](PROJECT_BUILD_AUDIT.md)
- [Backend API contract (Phase 2)](backend/API_CONTRACT_PHASE2.md)
- [Complaint operations & workflow notes](notes.md)
- [AWS setup guides (RDS · Bedrock · S3 · Athena · EC2)](infra/aws/guides/00_SETUP_INDEX.md)
- [Docker infrastructure notes](infra/docker/README.md)
- [Shared complaint schema](shared/schema/complaint.schema.json)

---

## Roadmap

Planned enhancements are tracked in [`deliverables/FUTURE_UPGRADES_PLAN.md`](deliverables/FUTURE_UPGRADES_PLAN.md) and include deeper analytics, expanded regulatory-report templates, and scaling the job worker for higher throughput.

---

## Contributing

Contributions are welcome. The repository uses a reviewed branch flow:

1. Branch off `dev` and open a pull request into `dev`.
2. Ensure the backend suite passes: `bash backend/scripts/run_backend_checks.sh`.
3. After tester approval on `dev`, a separate reviewed PR promotes changes to `main`.

Please never commit secrets or generated build/dependency directories, and keep changes covered by tests where practical.

---

## Getting Help

- **API reference:** the live Swagger UI at `/docs` (and `/openapi.json`) once the backend is running.
- **Setup & deployment:** the guides under [`infra/aws/`](infra/aws/README.md).
- **Questions & bugs:** open a GitHub issue on the repository.

---

## Maintainers & Credits

Built by **Harsh Kumar** ([@Harsh2227kumar](https://github.com/Harsh2227kumar)) and the CustomerPulse team for the **Union Bank of India IDEA 2.0** national hackathon, where it was selected as a **Top 30 finalist**.

---

## License

No open-source license is currently declared for this project; all rights are reserved by the authors. If you'd like to use, adapt, or build on CustomerPulse, please contact the maintainer first.
