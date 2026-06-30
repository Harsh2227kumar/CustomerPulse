# CustomerPulse Priority Roadmap

## High Priority

These tasks matter most for the live demo, PS alignment, and judge confidence.

### Fix And Prove S3/Athena Import Reliability

Keep the S3/Athena import path demo-safe and reliable.

Scope:
- Failure states should be clear: credentials missing, Athena timeout, table missing, and no matching rows.

Acceptance:
- User sees a specific status panel when S3/Athena fails.

### Build The 360-Degree Complaint Workspace

Create one complete complaint workspace instead of scattering information across screens.

Scope:
- Complaint summary
- Product, category, severity, sentiment
- AI reasoning and extracted issues
- SLA status and breach risk
- Duplicate and related complaints
- Draft response
- Next-best action
- Review and escalation status
- Full communication and system timeline

Acceptance:
- One complaint detail page gives agents and managers the full context needed to act.

### Add Communication History

Unify every customer and system touchpoint into one timeline.

Scope:
- Web form messages
- Email messages
- Call-center/manual notes
- Chat/social placeholder
- CFPB/S3 import events
- AI processing events
- Review and escalation events

Acceptance:
- `GET /api/complaints/{id}/timeline` returns ordered complaint events.
- Frontend renders an empty, loading, error, and populated timeline state.

### Add Escalation Management

Support manager and compliance workflows for risky complaints.

Scope:
- Escalation states: none, manager review, compliance review, regulatory risk, resolved.
- Escalation reasons based on urgency, sentiment, SLA breach risk, fraud/legal keywords, duplicates, and low AI confidence.
- Operations queue for escalated cases.
- Notes, approve, resolve, and rerun actions.

Acceptance:
- High-risk complaints can be escalated, tracked, and resolved from an operations queue.

### Add Explainability Layer

Make every AI and workflow decision auditable.

Scope:
- Confidence score
- Rule triggered
- Similarity score
- Evidence source
- AI reasoning
- Reviewer action
- Escalation reason

Acceptance:
- Every AI/review/escalation decision can explain why it happened.

### Add Human Feedback Learning Loop

Make the system improve when agents correct it.

Scope:
- Store accepted, edited, rejected, and escalated AI outputs.
- Store final human response and action.
- Capture correction reason and reviewer notes.
- Build feedback dataset for future model evaluation and retraining.

Acceptance:
- Agent corrections become reusable feedback data instead of disappearing.

### Add Banking Compliance Engine

Make CustomerPulse banking-specific, not a generic complaint helpdesk.

Scope:
- RBI/compliance rule checks
- SLA deadline tracking
- Escalation deadline tracking
- Regulatory violation flags
- Compliance evidence for reports

Acceptance:
- Complaints can be flagged for compliance risk with clear rule evidence.

### Add Proprietary Risk Intelligence Modules

Reduce overdependence on Claude and make CustomerPulse the decision-maker.

Scope:
- Escalation risk scoring
- Complaint risk scoring
- Fraud risk scoring
- Resolution recommendation baseline
- Compliance validation baseline

Acceptance:
- CustomerPulse can generate risk and escalation signals before asking Claude to draft or summarize.

## Medium Priority

These tasks make the system more defensible, measurable, and production-ready after the core demo gaps are closed.

### Add Regulatory Report Preset

Create compliance-friendly exports and report filters.

Scope:
- High-severity complaints
- Unresolved SLA breaches
- Fraud or unauthorized activity
- Complaints by product, company, and channel
- Human-review outcomes
- Duplicate complaint groups
- Audit evidence in every report

Acceptance:
- A regulatory report can be exported with filters and evidence.

### Add Root-Cause Analytics

Show manager-level intelligence across complaint trends.

Scope:
- Recurring issue phrases
- Product-level complaint spikes
- Channel concentration
- Duplicate cluster themes
- High-urgency drivers
- Emerging complaint themes

Acceptance:
- Dashboard shows top root causes and emerging themes from real DB data.

### Add Fraud Detection Engine

Identify complaints involving unauthorized activity or suspicious patterns.

Scope:
- Keyword and rule baseline first
- Unauthorized transaction detection
- Identity theft detection
- Account takeover indicators
- Repeated suspicious complaint patterns
- Future trainable model using feedback labels

Acceptance:
- Fraud-risk complaints are flagged and routed for escalation/review.

### Add Resolution Validation Layer

Prevent similar-case reuse from applying the wrong resolution.

Scope:
- Validate candidate resolution against complaint facts.
- Check risk flags and compliance rules.
- Detect missing evidence.
- Escalate mismatches.

Acceptance:
- High-similarity matches are reused only after validation.

### Run Similarity Threshold Optimization

Make vector-search thresholds data-driven.

Scope:
- Test thresholds such as 0.80, 0.85, 0.90, and 0.95.
- Measure accuracy, precision, recall, and false-positive risk.
- Choose threshold based on evidence.

Acceptance:
- Similarity threshold has a measured justification instead of looking arbitrary.

### Add Business Impact Metrics

Show executive value clearly.

Scope:
- Auto-resolution rate
- First-response time
- Average resolution time
- Agent workload reduction
- SLA breach reduction
- Cost-saving estimate

Acceptance:
- Dashboard shows measurable business KPIs and trend changes.

### Add Durable Background Import Jobs

Make larger controlled imports more reliable.

Scope:
- Async import job
- Progress status
- Retry handling
- Cancellation
- Operation logs

Acceptance:
- Import can continue outside request timeout and report progress clearly.

### Add Customer-Facing Intelligence

Make the customer portal smarter than basic ticket tracking.

Scope:
- Risk-aware complaint status
- Expected resolution timeline
- Next-step guidance
- Sentiment-aware updates
- Clear status reasons

Acceptance:
- Customer portal explains progress and next steps intelligently.

## Low Priority

These are valuable long-term upgrades, but they should come after the core PS and demo gaps.

### Add Deployment Smoke Tests

Catch live AWS and deployment regressions quickly.

Scope:
- `/api/health`
- S3/Athena import options
- One-row preview
- Authenticated import check

Acceptance:
- One command verifies EC2/backend import readiness.

### Add Database Migrations

Replace startup-only schema changes with controlled upgrades.

Scope:
- Alembic or equivalent migration workflow
- Migration files for schema changes
- Production-safe upgrade path

Acceptance:
- New environments and production upgrades use repeatable migration commands.

### Add Scheduled Reporting

Support production-style recurring compliance exports.

Scope:
- Scheduled CSV/PDF reports
- Saved report filters
- Delivery hooks

Acceptance:
- Admin can generate recurring reports for selected regulatory filters.

### Build Compliance Knowledge Graph

Create a stronger long-term moat for banking complaint intelligence.

Scope:
- Products
- Complaint issues
- Regulations
- SLA rules
- Risk indicators
- Evidence links

Acceptance:
- Risk and compliance decisions can cite structured knowledge relationships.

### Add Agent Copilot

Improve agent productivity after the core compliance and risk foundations are stable.

Scope:
- Suggested response edits
- Missing information prompts
- Policy references
- Agent checklist
- Similar-case hints

Acceptance:
- Agents receive context-aware assistance while keeping final approval human-controlled.

### Add Model Retraining Workflow

Turn feedback data into improving proprietary models.

Scope:
- Dataset export
- Evaluation split
- Retraining scripts
- Model comparison
- Model registry notes

Acceptance:
- New model versions can be trained and compared against previous performance.

## Strategic Analysis

The highest-priority work should prove the live demo works with real AWS data, then show that CustomerPulse is more than a wrapper around Claude.

The strongest story is:

**Claude drafts and assists, but CustomerPulse decides, validates, explains, learns, and audits.**

That means the most important product direction is:

1. Reliable real-data import.
2. 360-degree complaint workspace.
3. Communication timeline.
4. Escalation and compliance workflows.
5. Explainability and feedback learning.
6. Proprietary risk, fraud, compliance, and resolution intelligence.

The medium-priority tasks make the product more defensible and measurable. The low-priority tasks are strong production upgrades, but they should not distract from the demo-critical and PS-critical work.
