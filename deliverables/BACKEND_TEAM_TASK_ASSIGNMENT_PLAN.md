# CustomerPulse Backend Team Task Assignment Plan

## Division Method

Use this backend-domain split:

- Member 1: ML + AI Engines
- Member 2: Compliance + Regulatory Logic
- Member 3: Complaint Operations + Workflow
- Member 4: Data Import + Analytics + Reporting

This is the best split for low conflicts because each member owns a type of backend feature, not random objectives. If two tasks overlap, the owner is decided here so two people do not implement the same logic twice.

## Shared Rules For Everyone

1. Do not add many unrelated fields directly to the main `Complaint` model.
   Prefer separate tables/modules such as communications, escalations, compliance results, decision metadata, import audits, and analytics.

2. Do not duplicate business logic across modules.
   If another member owns a signal, consume their service output instead of recalculating it.

3. Keep `processing_service.py` as an orchestrator.
   Add new logic in dedicated services, then call those services from the orchestration layer.

4. Agree shared response shapes before implementation:
   - ML output shape
   - Compliance result shape
   - Timeline event shape
   - Escalation status shape
   - Report filter shape

5. Each member should create tests only for their owned module and integration points.

6. If a task needs data from another member, define a small service method or schema contract. Do not edit the other member's internals.

7. Prefer new routers/services/models under owned modules rather than crowding existing shared files.

8. Every new backend feature should expose clean API-ready schemas, even if frontend is done later.

## Recommended Module Ownership

Member 1 owns:
- `backend/app/ai/`
- `backend/app/services/processing_service.py` only for AI orchestration hooks
- future `backend/app/intelligence/`
- future `backend/app/explainability/`

Member 2 owns:
- future `backend/app/compliance/`
- compliance schemas/services
- compliance evidence models

Member 3 owns:
- future `backend/app/communications/`
- future `backend/app/escalations/`
- SLA workflow integration points
- timeline event service

Member 4 owns:
- `backend/app/ingestion/`
- `backend/app/analytics/`
- `backend/app/exports/`
- future `backend/app/reports/`
- import audit models/services

Shared files that need coordination:
- `backend/app/models/__init__.py`
- `backend/app/main.py`
- `backend/app/core/constants.py`
- `backend/app/schemas/complaint.py`
- `backend/app/services/processing_service.py`

Only one member should edit a shared file at a time. If possible, each member adds a new router/module, then one integration owner wires it into `main.py`.

## Member 1: ML + AI Engines

### Mission

Own all intelligence signals generated from complaint text and AI/ML processing.

Member 1 should answer:

What is this complaint about, how serious is it, what should happen next, and how confident is the system?

### Owned Tasks

#### 1. Intelligent Complaint Categorization

Scope:
- Complaint category classification
- Product/service identification support
- Sentiment detection
- Severity/urgency scoring
- Churn/risk style scoring if already supported

Deliverables:
- Stable AI output schema for category, sentiment, urgency, severity, and confidence.
- Tests for classification output shape and fallback behavior.

#### 2. Key Issue Extraction

Scope:
- Extract short core issue from long complaint narrative.
- Extract supporting evidence snippets.
- Return concise agent-friendly issue summary.

Deliverables:
- `key_issue` or equivalent field in AI/intelligence output.
- Evidence snippets tied to original complaint text.

#### 3. AI-Powered Response Support

Scope:
- Draft response support
- Next-best action recommendation
- Resolution recommendation baseline

Deliverables:
- Response suggestion output with confidence and reason codes.
- Clear distinction between AI draft and platform decision signals.

#### 4. Explainability For AI Decisions

Scope:
- AI confidence
- Reasoning summary
- Model/provider metadata
- Similarity score when retrieval is used
- Evidence source
- Reason codes

Deliverables:
- AI decision metadata object.
- Output that Member 3 can show in timeline/workflow and Member 4 can include in reports.

#### 5. Resolution Validation Layer

Scope:
- Validate similar-case or cached resolution before reuse.
- Check complaint facts against candidate resolution.
- Return approve/escalate/manual-review recommendation.

Deliverables:
- `ResolutionValidationService`
- Result fields: `status`, `reason_codes`, `evidence`, `confidence`.

#### 6. Similarity Threshold Optimization

Scope:
- Evaluate similarity threshold choices.
- Produce defensible threshold metrics.

Deliverables:
- Test/evaluation script or documented result table.
- Recommended threshold with reasoning.

### Explicit Non-Goals

Member 1 should not:
- Build escalation status tables.
- Build regulatory report endpoints.
- Own compliance rules.
- Own import or analytics APIs.
- Add timeline event storage.

### Outputs Consumed By Others

Member 2 consumes:
- AI category
- key issue
- severity/urgency
- reason codes
- evidence snippets

Member 3 consumes:
- low confidence flag
- high urgency flag
- next-best action
- resolution validation result

Member 4 consumes:
- category
- sentiment
- severity
- key issue
- similarity score
- AI confidence

### AI Agent Rules For Member 1

If an AI coding agent is assigned to Member 1:

1. Only modify AI/intelligence-related services unless explicitly asked to wire a small integration hook.
2. Do not create escalation, compliance, or reporting business logic.
3. Return structured outputs with reason codes and evidence, not only natural-language text.
4. Keep Claude/Gen-AI as assistant logic; platform-owned scores and validation should be deterministic where possible.
5. Add tests for output schema and failure/fallback behavior.
6. When touching shared processing code, keep changes small and call dedicated services.

## Member 2: Compliance + Regulatory Logic

### Mission

Own banking-specific compliance intelligence and audit evidence.

Member 2 should answer:

Does this complaint create regulatory/compliance risk, which rule was triggered, and what action is required?

### Owned Tasks

#### 1. Banking Compliance Engine

Scope:
- RBI/compliance rule baseline
- SLA compliance interpretation
- Regulatory risk flags
- Required action recommendations

Deliverables:
- `ComplianceService`
- Compliance result schema.
- Rule definitions with reason codes.

#### 2. Compliance Evidence Storage

Scope:
- Triggered rules
- Evidence snippets
- Risk level
- Required action
- Regulatory flag
- Timestamps

Deliverables:
- Compliance result model/table or structured persisted metadata.
- Tests for compliance evidence creation.

#### 3. Compliance Decision Explainability

Scope:
- Rule triggered
- Evidence source
- Why complaint is or is not regulatory risk

Deliverables:
- Compliance explainability object that Member 3 can surface in workflow and Member 4 can export.

#### 4. Regulatory Report Data Requirements

Scope:
- Define what evidence must appear in regulatory reports.
- Define required filters:
  - high severity
  - SLA breach
  - fraud risk
  - compliance risk
  - product
  - company
  - channel
  - review outcome
  - escalation reason

Deliverables:
- Report data contract for Member 4.
- Compliance fields ready for export.

#### 5. Compliance Knowledge Base Foundation

Scope:
- Initial rules and mappings.
- Future-ready shape for knowledge graph.

Deliverables:
- Rule config or constants that can later evolve into a knowledge graph.

### Explicit Non-Goals

Member 2 should not:
- Build the final report export implementation.
- Build escalation queue workflow.
- Build ML categorization.
- Own S3/Athena import.
- Own root-cause analytics.

### Outputs Consumed By Others

Member 3 consumes:
- compliance risk level
- required action
- escalation recommendation
- triggered rules

Member 4 consumes:
- compliance risk
- regulatory flags
- compliance evidence
- report filter fields

Member 1 may consume:
- compliance labels later for model/rule evaluation.

### AI Agent Rules For Member 2

If an AI coding agent is assigned to Member 2:

1. Work only inside compliance/regulatory logic unless asked to expose a small schema/API contract.
2. Do not implement report generation; define report-ready data only.
3. Every compliance result must include evidence and rule IDs.
4. Keep compliance rules deterministic and auditable.
5. Do not duplicate ML fraud/risk scoring from Member 1.
6. Add tests for triggered and non-triggered rule cases.

## Member 3: Complaint Operations + Workflow

### Mission

Own complaint state, timeline, SLA workflow integration, and escalation operations.

Member 3 should answer:

What happened to this complaint, what is its current operational status, and who must act next?

### Owned Tasks

#### 1. Communication History Backend

Scope:
- Communication event model
- Timeline event model
- Manual notes
- Customer/support interaction events
- System events

Deliverables:
- `communications` module.
- `TimelineService.add_event(...)`.
- Timeline schemas.

#### 2. Timeline API

Scope:
- `GET /api/complaints/{id}/timeline`
- `POST /api/communications`
- Ordered timeline events
- Empty/loading/error support through API behavior

Deliverables:
- Timeline router/service/repository.
- Tests for ordering and filtering.

#### 3. 360 Complaint Backend Support

Scope:
- Backend aggregation endpoint or detail support for workspace.
- Pull together complaint metadata, AI insights, SLA, duplicates, timeline, review, and escalation.

Deliverables:
- Workspace-ready complaint detail response or supporting APIs.

#### 4. Escalation Management

Scope:
- Escalation model/table
- Statuses:
  - none
  - manager_review
  - compliance_review
  - regulatory_risk
  - resolved
- Escalation reasons
- Notes/history

Deliverables:
- `escalations` module.
- Escalation schemas and service.

#### 5. Escalation APIs

Scope:
- `GET /api/escalations`
- `POST /api/complaints/{id}/escalate`
- `POST /api/complaints/{id}/escalation/resolve`

Deliverables:
- Escalation router.
- Tests for manual escalation and resolution.

#### 6. SLA Workflow Integration

Scope:
- Consume existing SLA risk/breach status.
- Use SLA breach risk as escalation trigger.
- Add SLA-related timeline events if needed.

Deliverables:
- SLA-to-escalation integration.
- Tests for SLA-triggered escalation.

### Explicit Non-Goals

Member 3 should not:
- Build ML risk scoring.
- Build compliance rules.
- Build import pipelines.
- Build final analytics dashboards or exports.

### Inputs From Others

Member 1 provides:
- urgency
- confidence
- key issue
- resolution validation
- fraud/risk signals if available

Member 2 provides:
- compliance risk
- required action
- regulatory flag

Existing SLA module provides:
- breach risk
- SLA status

Member 3 decides:
- escalation status
- timeline event creation
- operational next state

### AI Agent Rules For Member 3

If an AI coding agent is assigned to Member 3:

1. Own timeline and escalation state. Do not compute ML or compliance scores.
2. Create shared helper `TimelineService.add_event(...)` so other modules do not write timeline rows directly.
3. Escalation rules should consume signals from Member 1, Member 2, and SLA services.
4. Keep workflow statuses centralized in constants/enums.
5. Every escalation action must create a timeline/history event.
6. Add tests for state transitions and event ordering.

## Member 4: Data Import + Analytics + Reporting

### Mission

Own data entry from external sources and manager-level insight/reporting.

Member 4 should answer:

How does real complaint data enter the platform, and what insights/reports can managers generate from it?

### Owned Tasks

#### 1. S3/Athena Import Reliability

Scope:
- Options loading
- Preview
- Safe import
- Default 5 rows
- Max 50 rows
- Failure states:
  - credentials missing
  - Athena timeout
  - table missing
  - no matching rows

Deliverables:
- Stable ingestion service.
- Tests for limits and failure classification.

#### 2. Unified Complaint Aggregation Backend

Scope:
- Normalize external source data into complaint schema.
- Channel normalization.
- Source metadata.
- CFPB/S3 import as one channel.
- Prepare structure for email/web/chat/manual channels.

Deliverables:
- Import normalization helpers.
- Channel metadata contract.

#### 3. Import Audit Logs

Scope:
- Actor
- Filters
- selected rows
- imported rows
- skipped rows
- error code
- timestamps
- Athena execution ID if available

Deliverables:
- Import audit model/service.
- Audit query endpoint if time permits.

#### 4. Trend Analytics APIs

Scope:
- Frequent issues
- Product trends
- Category trends
- Channel trends
- Performance bottlenecks

Deliverables:
- Analytics endpoints or extensions to existing analytics.
- Tests for aggregation logic.

#### 5. Root-Cause Analytics

Scope:
- Recurring issue phrases
- Product spikes
- Channel concentration
- Duplicate cluster themes
- High-urgency drivers

Deliverables:
- Root-cause analytics service/API.
- Evidence examples for top themes.

#### 6. Regulatory Report Export Implementation

Scope:
- Implement report query/export using Member 2's compliance data contract.
- Include evidence from Member 1, Member 2, and Member 3.
- CSV first, PDF if time permits.

Deliverables:
- Regulatory report endpoint.
- CSV/PDF export integration.

#### 7. Business Impact Metrics

Scope:
- Auto-resolution percentage
- First-response time
- Average resolution time
- Agent workload reduction estimate
- SLA breach reduction
- Escalation rate

Deliverables:
- Metrics service/API.
- Manager-ready response schema.

### Explicit Non-Goals

Member 4 should not:
- Build ML scoring logic.
- Build compliance rule logic.
- Build escalation workflow state machine.
- Own timeline event internals.

### Inputs From Others

Member 1 provides:
- category
- sentiment
- severity
- confidence
- key issue
- risk/fraud/resolution validation signals

Member 2 provides:
- compliance risk
- triggered rules
- regulatory evidence

Member 3 provides:
- escalation status
- SLA workflow status
- timeline/action history

Member 4 outputs:
- analytics
- root-cause insight
- regulatory exports
- business metrics

### AI Agent Rules For Member 4

If an AI coding agent is assigned to Member 4:

1. Own ingestion, analytics, and export/report implementation.
2. Do not compute ML/compliance/escalation decisions directly; consume existing module outputs.
3. Keep imports bounded and demo-safe.
4. Reports must include evidence fields from other modules when available.
5. Analytics should be deterministic and explainable.
6. Add tests for import bounds, aggregation, and report filter shape.

## Conflict Map And Resolution

### Possible Conflict 1: Everyone Wants To Edit `Complaint`

Risk:
High.

Resolution:
Do not add every new field to `Complaint`. Use separate owned tables:

- Member 1: decision/intelligence metadata
- Member 2: compliance results
- Member 3: communications and escalations
- Member 4: import audits and analytics queries

### Possible Conflict 2: Multiple Members Touch `processing_service.py`

Risk:
High.

Resolution:
Member 1 owns AI processing internals. Others expose services that can be called from orchestration. Any final wiring into processing should happen in one coordinated integration pass.

### Possible Conflict 3: Timeline Events Needed By All

Risk:
Medium.

Resolution:
Member 3 owns timeline storage and exposes:

```python
TimelineService.add_event(complaint_id, event_type, actor, payload)
```

Other members call the service only.

### Possible Conflict 4: Escalation Depends On ML, SLA, And Compliance

Risk:
Medium.

Resolution:
Member 3 owns escalation decisions. Member 1 and Member 2 only provide signals. Member 3 consumes:

- AI confidence
- urgency
- fraud/risk score
- compliance risk
- SLA breach risk

### Possible Conflict 5: Reports Need Everyone's Data

Risk:
Medium.

Resolution:
Member 4 owns report generation, but does not own all source logic. Reports consume outputs from:

- Member 1: AI/ML metadata
- Member 2: compliance evidence
- Member 3: escalation/timeline status
- Existing modules: SLA, duplicates, feedback

### Possible Conflict 6: Fraud Detection Could Belong To ML Or Compliance

Risk:
Medium.

Resolution:
Fraud scoring belongs to Member 1 if it is an ML/risk engine.
Fraud regulatory interpretation belongs to Member 2.

Example:
- Member 1: `fraud_risk_score = high`
- Member 2: `triggered_rule = unauthorized_transaction_regulatory_review`

### Possible Conflict 7: Root-Cause Analytics Could Use ML Outputs

Risk:
Low.

Resolution:
Member 4 owns root-cause aggregation. Member 1 provides key issues/categories. Member 4 groups and reports them.

## Suggested Development Order

### Step 1: Shared Contracts

All members agree on:

- ML output shape
- Compliance result shape
- Timeline event shape
- Escalation status shape
- Report filter shape

### Step 2: Independent Module Build

Each member builds their module with tests:

- Member 1: intelligence outputs
- Member 2: compliance results
- Member 3: timeline/escalation
- Member 4: import/analytics/reporting

### Step 3: Integration Pass

Wire modules together:

- Import creates timeline event.
- AI processing creates decision metadata.
- Compliance consumes AI/category/signals.
- Escalation consumes AI/SLA/compliance signals.
- Reports consume AI/compliance/escalation/SLA data.

### Step 4: Backend Demo Verification

Verify:

- Import works.
- Complaint has AI outputs.
- Timeline has events.
- Compliance risk can be generated.
- Escalation can be created/resolved.
- Report/analytics endpoint returns useful data.

## Workload Balance Notes

Member 3 and Member 4 have larger implementation scope.

To balance:

- Keep Member 3 focused only on timeline + escalation. Do not give reporting to Member 3.
- Keep Member 4 focused first on import + one report/analytics path. Root-cause and business metrics can come after.
- Member 1 can support Member 4 later by providing key issue/category outputs for root-cause analytics.
- Member 2 can support Member 4 later by defining regulatory report fields, but Member 4 implements exports.

## Final Assignment Summary

Member 1: ML + AI Engines
- Categorization
- Sentiment/severity
- Key issue extraction
- Draft response support
- Next-best action
- AI explainability metadata
- Resolution validation
- Similarity threshold testing

Member 2: Compliance + Regulatory Logic
- Banking compliance engine
- RBI/compliance rules
- Regulatory violation detection
- Compliance evidence
- Compliance reason codes
- Regulatory report data contract
- Future compliance knowledge base

Member 3: Complaint Operations + Workflow
- Communication history
- Timeline API
- 360 workspace backend support
- SLA workflow integration
- Escalation management
- Operations queue API
- Escalation notes/history

Member 4: Data Import + Analytics + Reporting
- S3/Athena import reliability
- Unified aggregation/channel normalization
- Import audit logs
- Trend analytics
- Root-cause analytics
- Business impact metrics
- Regulatory report export

## Final Advice

This split gives the least conflict because each person owns a backend domain:

- Member 1 decides what the complaint means.
- Member 2 decides what the complaint means legally/compliance-wise.
- Member 3 decides what operational workflow should happen.
- Member 4 gets data in and turns system data into reports/insights.

If a feature overlaps, assign the decision logic to the owner above and let other members consume the output.
