# CustomerPulse Detailed Priority Execution Plan

## Goal

Build CustomerPulse toward a stronger Banking Complaint Intelligence Platform.

The plan is sorted by importance:

1. High priority: demo-critical and PS-critical work.
2. Medium priority: defensibility, analytics, and reliability upgrades.
3. Low priority: long-term production maturity and moat-building.

The strategic direction is:

**Claude drafts and assists, but CustomerPulse decides, validates, explains, learns, and audits.**

## High Priority Plan

High-priority tasks should be completed first because they directly affect the live demo, problem-statement fit, and judge confidence.

### 1. Fix And Prove S3/Athena Import Reliability

Purpose:
Make sure the Import page can safely use real AWS data without breaking the demo.

Detailed steps:
- Confirm backend S3/Athena environment variables on EC2.
- Verify `/api/ingestion/s3/options` loads real filter values.
- Verify `/api/ingestion/s3/preview` returns real CFPB complaints.
- Verify `/api/ingestion/s3/import` imports 1-5 rows into PostgreSQL.
- Show clear frontend states for:
  - credentials missing
  - Athena timeout
  - Athena table missing
  - no matching rows
  - generic source unavailable
- Add operation logs for import success/failure.

Dependencies:
- AWS credentials configured on EC2.
- S3 bucket and CFPB source key available.
- Athena database, table, workgroup, and output location configured.
- PostgreSQL reachable.

Acceptance checks:
- Import page loads filter dropdowns from Athena.
- Preview shows real complaints.
- Import saves complaints.
- Failure status is understandable without reading backend logs.

Suggested demo proof:
- Open Import page.
- Show Athena/Parquet source.
- Select a product filter.
- Import rows.
- Open dashboard and show imported complaints.

### 2. Build The 360-Degree Complaint Workspace

Purpose:
Give agents and managers one complete view of a complaint.

Detailed steps:
- Extend complaint detail API response with missing operational fields.
- Add a dedicated complaint workspace page.
- Show complaint metadata:
  - complaint ID
  - product
  - sub-product
  - issue
  - company
  - channel
  - date received
  - timely response
- Show AI outputs:
  - sentiment
  - category
  - urgency
  - churn risk
  - confidence
  - reasoning
  - draft response
  - next action
- Show operational context:
  - SLA status
  - breach risk
  - duplicate groups
  - similar cases
  - review status
  - escalation status
- Add action buttons:
  - approve response
  - edit response
  - rerun AI
  - escalate
  - resolve review

Dependencies:
- Existing complaint detail API.
- Existing AI processing data.
- SLA and duplicate modules.
- Review and feedback modules.

Acceptance checks:
- Agent can understand a complaint without switching pages.
- Manager can see risk, review, escalation, and response context.
- Empty states are shown where data is unavailable.

Suggested build order:
1. Backend response shape.
2. Frontend workspace layout.
3. SLA/duplicates/review panels.
4. Action buttons.
5. Tests and polish.

### 3. Add Communication History

Purpose:
Turn the complaint detail page into a true timeline of all touchpoints.

Detailed steps:
- Create communication/history model.
- Support event types:
  - customer message
  - agent note
  - CFPB import event
  - AI processing event
  - review action
  - escalation action
  - SLA event
- Add `GET /api/complaints/{id}/timeline`.
- Add `POST /api/communications`.
- Add timeline UI to complaint workspace.
- Show source/channel badge for each event.
- Sort events by timestamp.
- Include system-generated events automatically after import, processing, review, and escalation.

Dependencies:
- Complaint model.
- Review and processing run data.
- Future escalation model.

Acceptance checks:
- Timeline works for complaints with no communication history.
- Timeline shows imported/processed/reviewed events.
- Manual communication notes can be added.
- Events are ordered correctly.

Suggested build order:
1. Data model and schema.
2. Timeline API.
3. Timeline UI.
4. Auto-events from existing processing/review flows.
5. Tests for ordering and empty states.

### 4. Add Escalation Management

Purpose:
Create a real operations workflow for risky complaints.

Detailed steps:
- Add escalation fields or escalation table:
  - status
  - reason
  - severity
  - assigned owner
  - notes
  - created_at
  - resolved_at
- Define statuses:
  - none
  - manager_review
  - compliance_review
  - regulatory_risk
  - resolved
- Build escalation rules:
  - high urgency
  - negative sentiment
  - SLA breach risk
  - fraud or legal keywords
  - duplicate complaint cluster
  - low AI confidence
  - compliance risk
- Add endpoints:
  - `GET /api/escalations`
  - `POST /api/complaints/{id}/escalate`
  - `POST /api/complaints/{id}/escalation/resolve`
- Add Operations queue filters.
- Add escalation notes and action history.

Dependencies:
- Complaint processing results.
- SLA risk.
- Duplicate groups.
- Explainability metadata.
- Compliance/risk modules.

Acceptance checks:
- High-risk complaints are escalated automatically or manually.
- Operations queue shows escalated cases.
- Manager can resolve escalation with notes.
- Escalation appears in complaint timeline.

Suggested build order:
1. Escalation schema/model.
2. Manual escalation API.
3. Operations queue UI.
4. Rule-based auto-escalation.
5. Timeline integration.

### 5. Add Explainability Layer

Purpose:
Make the system auditable and trustworthy.

Detailed steps:
- Define decision metadata schema.
- Capture:
  - decision type
  - confidence score
  - rule triggered
  - similarity score
  - evidence source
  - AI reasoning
  - risk flags
  - reviewer action
  - escalation reason
- Store metadata for:
  - AI classification
  - draft response
  - similar-case retrieval
  - escalation
  - compliance flag
  - fraud flag
  - review decision
- Show explainability panel in complaint workspace.
- Include metadata in regulatory exports.

Dependencies:
- AI processing pipeline.
- Similarity/retrieval service.
- Escalation and compliance modules.

Acceptance checks:
- Every major decision has visible evidence.
- Reviewer can see why a complaint was escalated.
- Similar-case reuse shows similarity score and evidence.
- Export includes decision evidence.

Suggested build order:
1. Metadata schema.
2. Capture existing AI/retrieval metadata.
3. UI explainability panel.
4. Add escalation/compliance evidence.
5. Export/report integration.

### 6. Add Human Feedback Learning Loop

Purpose:
Make agent corrections reusable.

Detailed steps:
- Extend feedback capture to store:
  - original AI response
  - edited/final response
  - feedback action
  - correction reason
  - reviewer notes
  - final outcome
  - useful/not useful similar cases
- Add feedback analytics:
  - accepted count
  - edited count
  - rejected count
  - escalation count
  - common correction reasons
- Build dataset export for later model evaluation.
- Add feedback signals into future prompt/rule tuning.

Dependencies:
- Existing feedback module.
- Review workflow.
- Complaint workspace actions.

Acceptance checks:
- Human corrections are persisted.
- Feedback can be listed/exported.
- Dashboard shows feedback outcome trends.
- Future retraining dataset can be produced.

Suggested build order:
1. Review existing feedback schema.
2. Add missing correction fields.
3. Capture feedback from workspace actions.
4. Add analytics/export.
5. Document retraining dataset shape.

### 7. Add Banking Compliance Engine

Purpose:
Make CustomerPulse specific to banking complaint workflows.

Detailed steps:
- Define initial compliance rules.
- Start with deterministic rules:
  - SLA deadline risk
  - unauthorized transaction keywords
  - fraud keywords
  - identity theft keywords
  - legal/regulatory keywords
  - missing required response fields
  - high urgency plus untimely response
- Add compliance result object:
  - risk level
  - triggered rules
  - evidence snippets
  - required action
  - escalation recommendation
- Integrate compliance checks into processing pipeline.
- Show compliance panel in complaint workspace.
- Include compliance evidence in regulatory report.

Dependencies:
- Complaint text and metadata.
- SLA module.
- Escalation module.
- Explainability layer.

Acceptance checks:
- Compliance-risk complaints are flagged.
- Each flag has a clear rule and evidence.
- Compliance flags can trigger escalation.
- Regulatory report can filter by compliance risk.

Suggested build order:
1. Rule definitions.
2. Compliance service.
3. API fields.
4. Workspace UI panel.
5. Escalation/report integration.

### 8. Add Proprietary Risk Intelligence Modules

Purpose:
Reduce dependence on Claude and make CustomerPulse own key decisions.

Detailed steps:
- Build deterministic baseline modules first:
  - escalation risk engine
  - complaint risk engine
  - fraud risk engine
  - compliance validation engine
  - resolution recommendation baseline
- Each module should return:
  - score
  - risk level
  - reason codes
  - evidence snippets
  - recommended action
- Run modules before Claude draft generation.
- Pass module results into Claude as context, not as the source of truth.
- Store module outputs for analytics and explainability.

Dependencies:
- Explainability metadata.
- Compliance engine.
- Feedback labels.
- Processing pipeline.

Acceptance checks:
- Risk/escalation/fraud/compliance scores exist even if Claude is unavailable.
- Claude output references platform-generated signals.
- Module outputs are visible and auditable.

Suggested build order:
1. Rule-based complaint risk score.
2. Escalation risk score.
3. Fraud risk score.
4. Resolution recommendation baseline.
5. Pipeline and UI integration.

## Medium Priority Plan

Medium-priority tasks improve the platform after the main PS and demo gaps are covered.

### 1. Add Regulatory Report Preset

Detailed steps:
- Add report filters for:
  - high severity
  - unresolved SLA breaches
  - fraud risk
  - compliance risk
  - product
  - company
  - channel
  - human-review outcome
  - duplicate group
- Add regulatory report endpoint.
- Add CSV export.
- Add PDF export if time permits.
- Include audit evidence:
  - processing run
  - reviewer
  - timestamps
  - AI status
  - confidence
  - escalation reason
  - compliance rule

Acceptance checks:
- Manager can generate regulatory report from filtered data.
- Report includes evidence, not only complaint rows.

### 2. Add Root-Cause Analytics

Detailed steps:
- Extract recurring issue phrases.
- Group by product, issue, company, and channel.
- Track week-over-week or month-over-month deltas.
- Identify duplicate cluster themes.
- Identify high-urgency drivers.
- Add dashboard cards:
  - Top Root Causes
  - Emerging Complaint Themes
  - Product Spikes
  - Channel Concentration

Acceptance checks:
- Analytics use real DB data.
- Themes are explainable and include counts/evidence.

### 3. Add Fraud Detection Engine

Detailed steps:
- Start with keyword/rule detection.
- Detect:
  - unauthorized transaction
  - account takeover
  - identity theft
  - suspicious repeated complaints
  - chargeback or dispute patterns
- Add fraud risk score.
- Route high fraud risk to escalation.
- Store evidence snippets.

Acceptance checks:
- Fraud-risk complaints are flagged and explainable.
- Fraud flag can trigger escalation and reporting.

### 4. Add Resolution Validation Layer

Detailed steps:
- Validate reused similar-case resolutions.
- Check whether complaint facts match candidate resolution.
- Check if fraud/compliance/escalation flags make reuse unsafe.
- Escalate if mismatch or missing evidence.
- Store validator result.

Acceptance checks:
- Semantic cache does not blindly reuse risky resolutions.
- Validator explains approve/escalate decision.

### 5. Run Similarity Threshold Optimization

Detailed steps:
- Create labeled complaint-pair dataset.
- Test thresholds:
  - 0.80
  - 0.85
  - 0.90
  - 0.95
- Measure:
  - precision
  - recall
  - false positives
  - false negatives
- Choose threshold based on risk tolerance.
- Document results.

Acceptance checks:
- Similarity threshold has measured justification.
- Results can be shown to judges as evidence.

### 6. Add Business Impact Metrics

Detailed steps:
- Track:
  - auto-resolution percentage
  - first-response time
  - average resolution time
  - human-review percentage
  - escalation percentage
  - SLA breach reduction
  - agent workload reduction estimate
- Add dashboard KPIs.
- Add before/after demo numbers using seed/imported data.

Acceptance checks:
- Dashboard communicates business value in one glance.

### 7. Add Durable Background Import Jobs

Detailed steps:
- Convert import into queued job for larger batches.
- Store job status:
  - queued
  - running
  - completed
  - failed
  - cancelled
- Add progress counts.
- Add retry support.
- Add operation log.

Acceptance checks:
- Import does not depend on HTTP request duration.
- User can see progress and failure reason.

### 8. Add Customer-Facing Intelligence

Detailed steps:
- Add customer-friendly complaint status.
- Show expected response timeline.
- Show next required action.
- Show status reason without exposing internal risk details.
- Add sentiment-aware update copy.

Acceptance checks:
- Portal feels smarter than basic ticket tracking.

## Low Priority Plan

Low-priority tasks are valuable but should not delay the demo-critical and PS-critical work.

### 1. Add Deployment Smoke Tests

Detailed steps:
- Add script for:
  - backend health
  - auth check
  - S3 options
  - one-row preview
  - protected import authorization
- Run it after EC2 deploy.

Acceptance checks:
- One command confirms live deployment readiness.

### 2. Add Database Migrations

Detailed steps:
- Introduce Alembic or equivalent.
- Create baseline migration.
- Create migrations for new communication, escalation, compliance, and audit tables.
- Document upgrade command.

Acceptance checks:
- Schema changes are repeatable and production-safe.

### 3. Add Scheduled Reporting

Detailed steps:
- Save report filters.
- Add report schedule model.
- Generate CSV/PDF on schedule.
- Add delivery hook placeholder.

Acceptance checks:
- Admin can configure recurring regulatory reports.

### 4. Build Compliance Knowledge Graph

Detailed steps:
- Model relationships between:
  - products
  - issues
  - regulations
  - SLA rules
  - risk indicators
  - required evidence
- Use it to enrich compliance decisions.

Acceptance checks:
- Compliance/risk decisions can cite structured rule relationships.

### 5. Add Agent Copilot

Detailed steps:
- Suggest response edits.
- Show missing information checklist.
- Suggest policy references.
- Suggest similar-case response snippets.
- Keep human approval required.

Acceptance checks:
- Agent gets useful assistance without losing control.

### 6. Add Model Retraining Workflow

Detailed steps:
- Export feedback dataset.
- Split train/eval data.
- Add evaluation metrics.
- Add retraining script.
- Compare new model version against old version.

Acceptance checks:
- Feedback data can improve future proprietary models.

## Recommended Build Sequence

### Sprint 1: Demo Reliability

Focus:
- S3/Athena import reliability
- Failure status panel
- Live EC2 import verification

Outcome:
- Real data can be loaded and imported safely.

### Sprint 2: Complaint Workspace

Focus:
- 360-degree complaint workspace
- Communication timeline
- SLA, duplicate, review, and AI panels

Outcome:
- Agents can operate from one complete complaint view.

### Sprint 3: Escalation And Explainability

Focus:
- Escalation model/API/UI
- Explainability metadata
- Operations queue

Outcome:
- High-risk complaints are traceable, explainable, and actionable.

### Sprint 4: Compliance And Feedback Learning

Focus:
- Banking compliance engine
- Feedback learning loop
- Compliance evidence in timeline/workspace

Outcome:
- CustomerPulse becomes banking-specific and starts learning from humans.

### Sprint 5: Proprietary Intelligence

Focus:
- Risk scoring
- Fraud scoring
- Resolution recommendation baseline
- Resolution validation

Outcome:
- CustomerPulse owns more intelligence; Claude becomes a supporting layer.

### Sprint 6: Reporting And Analytics

Focus:
- Regulatory reports
- Root-cause analytics
- Business impact metrics

Outcome:
- Managers and judges can see measurable operational value.

## Success Criteria

CustomerPulse is successful when it can demonstrate:

- Real complaint import from S3/Athena.
- Full complaint context in one workspace.
- Communication and system event timeline.
- Escalation workflow for high-risk cases.
- Explainable AI and rule-based decisions.
- Human feedback captured for learning.
- Banking compliance intelligence.
- Proprietary risk/fraud/compliance modules.
- Regulatory reporting with audit evidence.
- Business metrics showing operational impact.

## Problem Statement Objective Coverage

This section maps the plan directly to the 12 objectives. The purpose is to make clear where each objective is satisfied and which priority task owns it.

### Objective 1: Unified Complaint Aggregation

Requirement:
Collect and consolidate complaints from multiple channels such as email, chat, and web forms into one centralized platform.

How the plan satisfies it:
- High Priority: Add Communication History
- High Priority: Build The 360-Degree Complaint Workspace
- High Priority: Fix And Prove S3/Athena Import Reliability

Implementation direction:
- Keep the CFPB/S3 import as one intake channel.
- Add normalized channel support for web, email, call-center/manual entry, and chat/social placeholders.
- Store channel metadata while exposing one unified complaint schema.
- Show channel badges and filters in queue/detail views.

Expected proof:
- Complaints from different channels appear in the same complaint queue.
- Agents can filter by channel.
- Each complaint detail page shows source/channel context.

Coverage status:
Partially satisfied now through CFPB/S3 import and complaint queue. Fully satisfied after multi-channel communication/intake model is added.

### Objective 2: Intelligent Complaint Categorization

Requirement:
Use NLP and Gen-AI to classify complaints, identify products/services, sentiment, and severity.

How the plan satisfies it:
- High Priority: Add Proprietary Risk Intelligence Modules
- High Priority: Add Explainability Layer
- Medium Priority: Add Fraud Detection Engine
- Medium Priority: Add Business Impact Metrics

Implementation direction:
- Continue using the current AI pipeline for category, sentiment, urgency, churn risk, confidence, and draft response.
- Add platform-owned deterministic/local risk modules before Claude.
- Store confidence and reasoning metadata for every classification.

Expected proof:
- Complaint detail shows category, product, sentiment, urgency/severity, and AI confidence.
- Explainability panel shows why the complaint was categorized that way.

Coverage status:
Mostly satisfied now through the AI processing pipeline. Strengthened by proprietary risk modules and explainability.

### Objective 3: Key Issue Extraction

Requirement:
Extract the core issue from lengthy complaint text so agents do not need to read the full message.

How the plan satisfies it:
- High Priority: Build The 360-Degree Complaint Workspace
- High Priority: Add Explainability Layer
- High Priority: Add Proprietary Risk Intelligence Modules

Implementation direction:
- Use existing AI issue/category extraction.
- Add a visible "Key Issue" or "Core Issue" field in the 360 workspace.
- Store extracted issue phrases/evidence snippets as decision metadata.

Expected proof:
- Complaint workspace displays a short core issue summary.
- Agents can see supporting evidence snippets from the original complaint.

Coverage status:
Partially satisfied now through AI category/issue output. Fully satisfied when the 360 workspace explicitly displays key issue extraction.

### Objective 4: Duplicate And Similar Complaint Detection

Requirement:
Use embeddings/vector search to identify duplicate or related complaints.

How the plan satisfies it:
- High Priority: Build The 360-Degree Complaint Workspace
- High Priority: Add Explainability Layer
- Medium Priority: Add Resolution Validation Layer
- Medium Priority: Run Similarity Threshold Optimization
- Medium Priority: Add Root-Cause Analytics

Implementation direction:
- Continue using embeddings/pgvector and duplicate detection.
- Show duplicate groups and similar cases in complaint workspace.
- Add similarity score and evidence into explainability.
- Validate similar-case resolution reuse before applying it.
- Test thresholds so similarity logic is defensible.

Expected proof:
- Complaint detail shows duplicate/related complaints.
- Duplicate groups can be reviewed.
- Similarity scores are visible.

Coverage status:
Already substantially satisfied through duplicate and similarity modules. Future work improves trust, validation, and threshold justification.

### Objective 5: AI-Powered Response Suggestions

Requirement:
Generate draft responses, resolution templates, and next-best action recommendations.

How the plan satisfies it:
- High Priority: Build The 360-Degree Complaint Workspace
- High Priority: Add Human Feedback Learning Loop
- High Priority: Add Proprietary Risk Intelligence Modules
- Medium Priority: Add Resolution Validation Layer
- Low Priority: Add Agent Copilot

Implementation direction:
- Continue using Gen-AI for draft response and next-best action.
- Show draft response and next action in the workspace.
- Capture accepted/edited/rejected responses as feedback.
- Add validation before reusing template/similar-case resolutions.

Expected proof:
- Agent sees AI draft response and next-best action.
- Agent can approve/edit/reject.
- Feedback is stored for future improvement.

Coverage status:
Already mostly satisfied through current AI draft/next-action flow. Feedback and validation make it stronger.

### Objective 6: 360-Degree Complaint View

Requirement:
Provide a comprehensive complaint view including customer details, complaint history, previous interactions, and AI insights.

How the plan satisfies it:
- High Priority: Build The 360-Degree Complaint Workspace
- High Priority: Add Communication History
- High Priority: Add Explainability Layer
- High Priority: Add Escalation Management

Implementation direction:
- Build one complaint workspace page.
- Combine complaint metadata, AI insights, SLA, duplicates, reviews, escalations, communications, and timeline.

Expected proof:
- One screen gives the agent full context.
- Workspace includes AI insights and history.

Coverage status:
Partially satisfied by existing detail/review/dashboard data. Fully satisfied by the planned 360 workspace.

### Objective 7: Communication History Tracking

Requirement:
Maintain a complete timeline of customer/support interactions.

How the plan satisfies it:
- High Priority: Add Communication History
- High Priority: Build The 360-Degree Complaint Workspace
- High Priority: Add Escalation Management

Implementation direction:
- Add communication table/model.
- Add `GET /api/complaints/{id}/timeline`.
- Add `POST /api/communications`.
- Include customer messages, agent notes, import events, AI processing, reviews, escalation, and SLA events.

Expected proof:
- Complaint detail page shows chronological timeline.
- Manual notes and system events appear together.

Coverage status:
Not fully satisfied yet. This is one of the most important High Priority gaps.

### Objective 8: SLA Monitoring And Management

Requirement:
Track SLA deadlines, highlight breaches or risks, and improve accountability.

How the plan satisfies it:
- High Priority: Build The 360-Degree Complaint Workspace
- High Priority: Add Escalation Management
- High Priority: Add Banking Compliance Engine
- Medium Priority: Add Regulatory Report Preset

Implementation direction:
- Use existing SLA module.
- Show SLA status and breach risk inside complaint workspace.
- Use SLA breach risk as an escalation trigger.
- Include unresolved SLA breaches in regulatory reports.

Expected proof:
- Dashboard/workspace shows SLA status.
- Breach-risk complaints are visible and escalatable.

Coverage status:
Already significantly satisfied by existing SLA features. Plan integrates SLA into workspace, escalation, and reporting.

### Objective 9: Escalation Management System

Requirement:
Automatically escalate unresolved or critical complaints to higher-level support.

How the plan satisfies it:
- High Priority: Add Escalation Management
- High Priority: Add Banking Compliance Engine
- High Priority: Add Proprietary Risk Intelligence Modules
- Medium Priority: Add Fraud Detection Engine

Implementation direction:
- Add escalation statuses and reasons.
- Add escalation API and operations queue.
- Add rule-based escalation triggers using urgency, sentiment, SLA, fraud/legal keywords, duplicate clusters, compliance risk, and low confidence.

Expected proof:
- High-risk complaint appears in Operations queue.
- Manager can resolve or update escalation.
- Escalation event appears in timeline.

Coverage status:
Partially satisfied by review flow. Full escalation workflow is High Priority.

### Objective 10: Trend Analysis And Insights

Requirement:
Analyze complaint data for frequent issues, category trends, and bottlenecks using dashboards.

How the plan satisfies it:
- Medium Priority: Add Root-Cause Analytics
- Medium Priority: Add Business Impact Metrics
- Medium Priority: Add Regulatory Report Preset

Implementation direction:
- Use analytics dashboard for product/category/channel trends.
- Add high-urgency drivers, performance bottlenecks, and review/escalation trends.
- Add business metrics such as first-response time, workload reduction, and SLA breach reduction.

Expected proof:
- Dashboard shows complaint trends and operational bottlenecks.
- Managers can identify frequent issues and high-risk areas.

Coverage status:
Partially satisfied now through analytics. Medium Priority work deepens insight quality.

### Objective 11: Root Cause Identification

Requirement:
Use AI and analytics to identify underlying causes of recurring complaints.

How the plan satisfies it:
- Medium Priority: Add Root-Cause Analytics
- Medium Priority: Add Resolution Validation Layer
- High Priority: Add Proprietary Risk Intelligence Modules

Implementation direction:
- Extract recurring issue phrases.
- Group by product, issue, channel, company, and duplicate cluster.
- Identify product spikes and emerging complaint themes.
- Add evidence-backed root-cause cards to dashboard.

Expected proof:
- Dashboard shows "Top Root Causes" and "Emerging Complaint Themes."
- Root-cause items include counts and example complaints.

Coverage status:
Not fully satisfied yet. This is a Medium Priority product-intelligence gap.

### Objective 12: Regulatory Reporting

Requirement:
Generate structured reports for compliance, internal audits, and performance evaluation.

How the plan satisfies it:
- Medium Priority: Add Regulatory Report Preset
- High Priority: Add Explainability Layer
- High Priority: Add Banking Compliance Engine
- Low Priority: Add Scheduled Reporting

Implementation direction:
- Add report filters for high severity, SLA breaches, fraud, product, company, channel, review outcomes, and duplicates.
- Include audit evidence:
  - processing run
  - reviewer
  - timestamps
  - AI status
  - confidence
  - escalation reason
  - compliance rule
- Keep CSV/PDF export support.

Expected proof:
- Manager can export a regulatory report with evidence.
- Report supports compliance and audit review.

Coverage status:
Partially satisfied through existing exports. Full regulatory preset is Medium Priority.

## Objective Priority Summary

High priority objectives:
- Objective 1: Unified Complaint Aggregation
- Objective 3: Key Issue Extraction
- Objective 6: 360-Degree Complaint View
- Objective 7: Communication History Tracking
- Objective 8: SLA Monitoring And Management
- Objective 9: Escalation Management System

Medium priority objectives:
- Objective 10: Trend Analysis And Insights
- Objective 11: Root Cause Identification
- Objective 12: Regulatory Reporting

Already substantially covered but needs polish/defensibility:
- Objective 2: Intelligent Complaint Categorization
- Objective 4: Duplicate And Similar Complaint Detection
- Objective 5: AI-Powered Response Suggestions

## Gap Analysis Against Objectives

Strongest existing coverage:
- Intelligent categorization
- Duplicate/similar complaint detection
- AI draft responses
- SLA analytics
- Basic exports
- S3/CFPB intake

Biggest remaining gaps:
- Unified multi-channel communication history
- Full 360-degree complaint workspace
- Structured escalation management
- Regulatory report preset
- Root-cause dashboard
- Explainability and feedback learning

Recommended order to satisfy the PS fastest:

1. Live S3/Athena import reliability.
2. Communication history and timeline.
3. 360-degree complaint workspace.
4. Escalation management.
5. Explainability layer.
6. Regulatory report preset.
7. Root-cause analytics.

## Final Positioning

Current risk:

CustomerPulse may be seen as a workflow app that relies heavily on Claude.

Target position:

CustomerPulse is a Banking Complaint Intelligence Platform where:

- CustomerPulse owns risk decisions.
- CustomerPulse validates resolutions.
- CustomerPulse explains every action.
- CustomerPulse learns from human correction.
- Claude helps with drafting and summarization.
