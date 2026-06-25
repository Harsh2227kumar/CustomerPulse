# CustomerPulse — MASTER PLAN (Full Depth, Status-Trackable)

**Purpose of this document:** Paste this entire plan into a fresh Claude/Codex conversation along with a one-line status update such as "we are at Sprint 2, Member 3 is working on timeline API, completed import hardening" and the assistant will have full context to continue without re-explaining the project.

---

## SECTION A: VERIFIED CURRENT STATE

### A1. What is real and working

- FastAPI backend, PostgreSQL + pgvector, AWS Bedrock/Claude integration, React frontend, Docker Compose, and Nginx reverse proxy.
- Bedrock LLM enrichment pipeline with prompt engineering, RAG-style evidence injection, schema validation, retry/fallback handling, and review routing.
- Duplicate detection using exact-hash and pgvector similarity clustering.
- SLA backend analytics for breach risk, trends, and grouped views.
- PDF/CSV exports through existing export services.
- DB-backed background job worker with websocket events.
- Role-based auth for agent/manager/admin API writes.
- Manual complaint intake and CFPB S3/Athena batch import path.
- Feedback/review flow.
- Dashboard and complaint queue flows.
- Backend and frontend tests exist across important modules.

### A2. Latest import status

The S3/Athena import path has been hardened for demo safety:

- Default import limit is 5 rows.
- Controlled-test cap is 50 rows.
- Backend rejects values above 50.
- Import errors are classified for credentials missing, Athena timeout, table missing, no matching rows, and generic source unavailable.
- Import page can show a clear status panel for S3/Athena failures.

Why this matters:

The live demo should safely preview/import 1-5 real complaints without accidentally pulling a huge Athena result or causing timeout/cost issues.

### A3. ML layer caution from original plan

The older plan correctly warned that some local ML files were dictionary/rule based, not truly trained ML models.

Rules going forward:

- Do not claim keyword/rule logic as trained ML.
- If trained models are added, keep backend function signatures stable.
- If time is short, present deterministic engines honestly as explainable platform intelligence.
- Claude should assist with drafting and summarization, while CustomerPulse owns decision signals, validation, evidence, workflow, and audit.

---

## SECTION B: TARGET ARCHITECTURE

### B1. Strategic positioning

CustomerPulse should become a **Banking Complaint Intelligence Platform**.

Core statement:

**Claude drafts and assists, but CustomerPulse decides, validates, explains, learns, and audits.**

### B2. Backend target flow

```text
Complaint Intake
  ↓
Unified Complaint Schema
  ↓
AI / ML / Deterministic Intelligence Signals
  ↓
Compliance Rules
  ↓
SLA + Escalation Workflow
  ↓
Communication Timeline
  ↓
Regulatory Reports + Analytics
```

### B3. Decision flow

```text
Complaint text + metadata
  ↓
Platform intelligence:
  - category
  - sentiment
  - urgency/severity
  - key issue
  - risk/fraud score
  - reason codes
  ↓
Compliance validation:
  - triggered rules
  - evidence
  - required action
  ↓
Escalation decision:
  - SLA risk
  - AI confidence
  - compliance risk
  - fraud/risk score
  ↓
Claude/Bedrock:
  - draft response
  - summarization
  - response phrasing
```

### B4. Design constraints

- Keep existing API contracts stable where possible.
- Prefer new modules over overloading existing files.
- Keep `processing_service.py` as an orchestrator.
- Do not add every new field directly to `Complaint`; use separate tables/modules.
- Every major decision should have evidence, confidence, reason codes, and audit metadata.

---

## SECTION C: UPDATED TARGET MODULE STRUCTURE

```text
backend/app/
├── ai/                         existing AI/Bedrock/ML logic
├── intelligence/               [NEW] platform-owned risk, issue, recommendation services
├── explainability/             [NEW] decision metadata and reason-code helpers
├── compliance/                 [NEW] banking/compliance rules and evidence
├── communications/             [NEW] communication history and timeline API
├── escalations/                [NEW] escalation state, notes, queue, workflow
├── ingestion/                  existing S3/Athena import
├── analytics/                  existing analytics, extended for trends/root cause
├── exports/                    existing CSV/PDF exports, extended for regulatory preset
├── reports/                    [NEW optional] report presets and report service wrappers
├── feedback/                   existing feedback/review data, extended for learning loop
├── duplicates/                 existing duplicate/similar complaint module
├── sla/                        existing SLA module
└── models/, schemas/, services/
```

If real trained ML models are added later:

```text
ml_training/
├── notebooks/
├── data/
├── exported_models/
└── TRAINING_LOG.md
```

Important:

If no trained model exists, do not market rule logic as trained ML. Call it deterministic, explainable intelligence.

---

## SECTION D: EXPLICITLY EXCLUDED OR DEFERRED

Do not prioritize these before core PS gaps are done:

- Full customer self-service portal
- Full model retraining/self-learning loop
- PII-scrubbing regulatory export
- Scheduled reporting before basic regulatory preset
- Compliance knowledge graph before deterministic compliance rules
- Agent copilot before backend workflow/evidence is stable
- Semantic auto-resolution without validation

Reason:

The biggest PS gaps are communication history, 360 complaint view, escalation, regulatory reporting, root cause, and explainability.

---

## SECTION E: OBJECTIVE COVERAGE MAP

### Objective 1: Unified Complaint Aggregation

Status: partially covered by manual intake and CFPB/S3 import.

Owners:

- Member 4: S3/Athena import and channel normalization
- Member 3: communication/timeline backend

Target proof:

Complaints from different channels appear in one queue with channel metadata.

### Objective 2: Intelligent Complaint Categorization

Status: mostly covered by current AI pipeline, needs stronger defensibility.

Owner:

- Member 1: category, sentiment, severity/urgency, confidence, reason codes

Target proof:

Complaint detail exposes category, product/service, sentiment, severity, confidence, and evidence.

### Objective 3: Key Issue Extraction

Status: partially covered, needs explicit field/output.

Owners:

- Member 1: key issue extraction
- Member 3: 360 backend support to expose it

Target proof:

Complaint detail includes short core issue and evidence snippets.

### Objective 4: Duplicate And Similar Complaint Detection

Status: substantially covered by duplicate/pgvector modules.

Owners:

- Member 1: similarity threshold testing and resolution validation
- Member 4: duplicate trend/reporting use

Target proof:

Duplicate/similar complaints appear with similarity score and evidence.

### Objective 5: AI-Powered Response Suggestions

Status: mostly covered through Bedrock draft and next action.

Owners:

- Member 1: response support, next-best action, validation
- Member 3: workflow integration

Target proof:

Agent can approve, edit, or reject AI draft and the feedback is stored.

### Objective 6: 360-Degree Complaint View

Status: high-priority gap.

Owners:

- Member 3: workspace-ready backend and timeline
- Member 1: AI insights
- Member 2: compliance evidence
- Member 4: import/source/report context

Target proof:

One detail endpoint/workspace can show metadata, AI, SLA, duplicates, review, escalation, and timeline.

### Objective 7: Communication History Tracking

Status: high-priority gap.

Owner:

- Member 3: communications module and timeline API

Target proof:

`GET /api/complaints/{id}/timeline` returns ordered customer/support/system events.

### Objective 8: SLA Monitoring And Management

Status: mostly covered by existing SLA module.

Owners:

- Member 3: SLA workflow and escalation integration
- Member 2: compliance interpretation
- Member 4: SLA reports and metrics

Target proof:

SLA breach risk can trigger escalation and appear in reports.

### Objective 9: Escalation Management System

Status: high-priority gap.

Owner:

- Member 3: escalation model, API, queue, workflow, state transitions

Inputs:

- Member 1: confidence, urgency, fraud/risk score
- Member 2: compliance risk
- SLA module: breach risk

Target proof:

High-risk complaint can be escalated, tracked, and resolved with notes.

### Objective 10: Trend Analysis And Insights

Status: partially covered.

Owner:

- Member 4: trend analytics and business metrics

Target proof:

Analytics APIs show frequent issues, product/category/channel trends, and bottlenecks.

### Objective 11: Root Cause Identification

Status: medium-priority gap.

Owners:

- Member 4: root-cause analytics
- Member 1: key issue/category signals

Target proof:

Top Root Causes and Emerging Complaint Themes can be generated from DB data.

### Objective 12: Regulatory Reporting

Status: partially covered by existing CSV/PDF exports.

Owners:

- Member 2: compliance evidence and regulatory data requirements
- Member 4: export implementation
- Member 1: AI evidence
- Member 3: escalation/timeline evidence

Target proof:

Regulatory report preset exports complaints with audit evidence.

---

## SECTION F: BACKEND-ONLY TEAM DIVISION

All four members work on backend first. Frontend comes later.

Use this split because it has the least conflict:

```text
Member 1: ML + AI Engines
Member 2: Compliance + Regulatory Logic
Member 3: Complaint Operations + Workflow
Member 4: Data Import + Analytics + Reporting
```

### Member 1: ML + AI Engines

Mission:

Own all intelligence signals generated from complaint text and AI/ML processing.

Owns:

- categorization
- sentiment, severity, urgency
- key issue extraction
- response suggestion support
- next-best action
- AI explainability metadata
- resolution validation
- similarity threshold testing
- fraud/risk score if treated as intelligence engine

Does not own:

- escalation workflow
- compliance rules
- reports
- imports
- timeline storage

AI-agent rules:

1. Modify only AI/intelligence services unless a small integration hook is required.
2. Return structured outputs with reason codes and evidence.
3. Do not create compliance, escalation, or reporting logic.
4. Keep Claude draft text separate from platform-owned decision signals.
5. Add tests for output shape and fallback behavior.

### Member 2: Compliance + Regulatory Logic

Mission:

Own banking-specific compliance intelligence and audit evidence.

Owns:

- banking compliance engine
- compliance/RBI rule baseline
- SLA compliance interpretation
- regulatory violation detection
- compliance evidence
- compliance reason codes
- regulatory report data contract
- future compliance knowledge base

Does not own:

- report export implementation
- escalation workflow
- ML categorization
- S3/Athena import
- root-cause analytics

AI-agent rules:

1. Work inside compliance/regulatory logic.
2. Every compliance result must include rule IDs and evidence.
3. Keep rules deterministic and auditable.
4. Do not duplicate Member 1 fraud/risk scoring.
5. Define report-ready fields but do not implement final reports.

### Member 3: Complaint Operations + Workflow

Mission:

Own complaint state, timeline, SLA workflow integration, and escalation operations.

Owns:

- communication history model
- timeline event model
- `GET /api/complaints/{id}/timeline`
- `POST /api/communications`
- 360 complaint backend support
- escalation model/table
- escalation APIs
- operations queue API
- escalation notes/history
- SLA workflow integration

Does not own:

- ML scoring
- compliance rules
- import pipelines
- analytics/report exports

AI-agent rules:

1. Own timeline and escalation state only.
2. Expose `TimelineService.add_event(...)`.
3. Other modules call the timeline service instead of writing timeline rows directly.
4. Consume ML, compliance, and SLA signals for escalation decisions.
5. Every escalation action creates a timeline/history event.
6. Add tests for ordering and state transitions.

### Member 4: Data Import + Analytics + Reporting

Mission:

Own data entry from external sources and manager-level insight/reporting.

Owns:

- S3/Athena import reliability
- unified complaint aggregation backend
- channel normalization
- import audit logs
- trend analytics APIs
- root-cause analytics
- duplicate/similar complaint reporting
- business impact metrics
- regulatory report export implementation
- CSV/PDF export integration

Does not own:

- ML scoring logic
- compliance rule logic
- escalation state machine
- timeline internals

AI-agent rules:

1. Own ingestion, analytics, and export/report implementation.
2. Keep imports bounded and demo-safe.
3. Do not compute ML/compliance/escalation decisions directly; consume outputs.
4. Reports must include evidence fields from other modules when available.
5. Analytics should be deterministic and explainable.
6. Add tests for import bounds, aggregation, and report filters.

---

## SECTION G: CONFLICT PREVENTION RULES

### G1. Do not overload `Complaint`

Use separate owned tables:

- Member 1: decision/intelligence metadata
- Member 2: compliance results
- Member 3: communications and escalations
- Member 4: import audits and analytics queries

### G2. Keep processing orchestration clean

`processing_service.py` should orchestrate. Logic belongs in dedicated services.

### G3. Timeline writes go through Member 3

Shared helper:

```python
TimelineService.add_event(complaint_id, event_type, actor, payload)
```

### G4. Escalation belongs to Member 3

Member 1 and Member 2 provide signals only.

Escalation consumes:

- AI confidence
- urgency
- fraud/risk score
- compliance risk
- SLA breach risk

### G5. Reports belong to Member 4

Reports consume:

- Member 1 AI metadata
- Member 2 compliance evidence
- Member 3 escalation/timeline state
- existing SLA, duplicate, feedback modules

### G6. Fraud split

- Fraud risk score: Member 1
- Fraud regulatory interpretation: Member 2

---

## SECTION H: UPDATED SPRINT PLAN

### Sprint 1: Demo Reliability

Owner: Member 4

Support: Member 3 for timeline import events

Focus:

- S3/Athena import reliability
- import audit logs
- bounded import behavior
- live EC2 import verification

Outcome:

Real data can be loaded and imported safely.

### Sprint 2: Timeline And 360 Backend

Owner: Member 3

Support: Member 1 for AI fields, Member 4 for import events

Focus:

- communication history
- timeline API
- workspace-ready complaint response
- system events

Outcome:

Complaint detail backend can support a full 360-degree workspace.

### Sprint 3: AI Explainability And Feedback

Owner: Member 1

Support: Member 3 for workflow events

Focus:

- key issue extraction
- AI metadata
- explainability output
- feedback learning fields
- resolution validation baseline

Outcome:

AI decisions become structured and auditable.

### Sprint 4: Compliance And Escalation

Owners: Member 2 and Member 3

Focus:

- compliance engine
- compliance evidence
- escalation status/model/API
- SLA/compliance/AI escalation triggers

Outcome:

Risky complaints can be flagged and escalated with evidence.

### Sprint 5: Reports And Insights

Owner: Member 4

Support: Member 1, Member 2, and Member 3 provide contracts/data

Focus:

- regulatory report preset
- trend analytics
- root-cause analytics
- business impact metrics

Outcome:

Managers can see trends, root causes, and audit-ready reports.

---

## SECTION I: HOW TO RESUME IN A NEW AI SESSION

When resuming, state:

1. Current sprint number
2. Current member/domain
3. Completed tasks
4. Blockers
5. Files changed
6. Whether shared contracts changed

Example:

We are at Sprint 2. Member 3 is building communication history. Timeline event schema is agreed. S3 import reliability is done. Need next implementation step for `GET /api/complaints/{id}/timeline`.

---

## SECTION J: FINAL POSITIONING

Current risk:

CustomerPulse may be perceived as a workflow app that relies too much on Claude.

Target position:

CustomerPulse is a Banking Complaint Intelligence Platform where:

- CustomerPulse owns risk decisions.
- CustomerPulse validates resolutions.
- CustomerPulse explains every action.
- CustomerPulse learns from human correction.
- CustomerPulse reports with audit evidence.
- Claude helps with drafting and summarization.
