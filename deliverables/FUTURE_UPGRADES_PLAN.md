# CustomerPulse Major Future Upgrades Plan

## Immediate Hardening
- Keep S3/Athena import demo-safe with a default of 5 rows and a controlled-test cap of 50 rows.
- Add an import health endpoint that checks AWS credentials, S3 object access, Athena catalog access, output bucket access, and a one-row preview query.
- Store import attempts in an audit table with actor, filters, selected rows, imported rows, failures, and Athena execution IDs.

## Product Scope
- Build the 360-degree complaint workspace with complaint details, AI reasoning, SLA risk, duplicate groups, communication history, response draft, and escalation status in one screen.
- Add normalized communication history for web form, email, call-center notes, chat/social placeholders, CFPB imports, and reviewer comments.
- Add escalation states for manager review, compliance review, regulatory risk, resolved, and closed.

## Regulatory And Reporting
- Create a regulatory report preset covering high severity, unresolved SLA breaches, fraud or unauthorized activity, human-review outcomes, duplicate groups, product, company, and channel.
- Include audit evidence in every export: processing run, reviewer, timestamps, AI status, confidence, escalation reason, and source channel.
- Add scheduled report generation for demo and production workflows.

## Analytics Intelligence
- Add deterministic root-cause aggregation for recurring phrases, product spikes, channel concentration, duplicate cluster themes, and high-urgency drivers.
- Add manager-facing root-cause summaries after deterministic evidence is computed, keeping the evidence visible.
- Track trend deltas over time so emerging complaint themes can be separated from already-known high-volume issues.

## Production Readiness
- Move long-running imports and AI processing into durable background jobs with retries, progress events, and cancellation.
- Add migrations for every schema change instead of relying on startup table creation.
- Add role-specific audit logs for import, review, escalation, export, and response approval actions.
- Add deployment smoke tests for `/api/health`, S3/Athena import options, a one-row preview, and authenticated import authorization.
