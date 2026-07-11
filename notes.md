# Notes: Member 3 — Complaint Operations & Workflow

This document summarizes the architecture, database schema, API endpoints, business logic, and test coverage for the features implemented by Member 3, covering **Phase 8 + Phase 9 (Complaint Operations & Workflow)** entirely.

---

## 1. Communication History & Timeline
Tracks all interactions, notes, system events, and escalation actions associated with a complaint.

### Database Schema (`communication_history` Table)
Defined in [communications/models.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/communications/models.py):
* `id` (VARCHAR(64), PK): Unique UUID for the history entry.
* `complaint_pk` (VARCHAR(64), FK): Foreign key referencing `complaints.id` (with cascade deletion).
* `entry_type` (VARCHAR(32)): Entry classification constraint (`'system'`, `'note'`, or `'escalation'`).
* `event_code` (VARCHAR(64), Optional): Unique code representing system event types (e.g., `"status_finalized"`).
* `message` (TEXT): Description/content of the entry.
* `actor` (VARCHAR(128), Optional): Author/initiator (e.g., user identifier or `"system"`).
* `context` (JSONB, Optional): Additional event metadata.
* `created_at` (TIMESTAMP WITH TIME ZONE): Server-default creation timestamp.

**Constraints & Indexes**:
* `ck_communication_history_entry_type`: Validates allowed types.
* `ix_communication_history_complaint_created_at`: Composite index on `(complaint_pk, created_at)` for quick chronological timeline sorting.
* `ix_communication_history_event_code`: Index for searching by event codes.

### API Endpoints
Defined in [communications/router.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/communications/router.py):
* `GET /api/complaints/{complaint_id}/timeline`: Retrieve the chronological timeline of events for a complaint. (Accessible by: AGENT, MANAGER, ADMIN)
* `POST /api/complaints/{complaint_id}/timeline`: Add a manual agent note. (Accessible by: AGENT, MANAGER, ADMIN)

### Service Layer Logic
Defined in [communications/service.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/communications/service.py):
* `record_system_event`: Helper to write automated system logs to the history table (e.g., transition logs).
* `add_note`: Helper to append agent comments.
* `add_escalation_note`: Specialized helper to document escalation and resolution events (uses type `"escalation"`).

---

## 2. Escalations Management
Implements the workflow to flag and track critical complaints for managers.

### Database Schema (`escalations` Table)
Defined in [escalations/models.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/escalations/models.py):
* `id` (VARCHAR(64), PK): Unique UUID for the escalation.
* `complaint_pk` (VARCHAR(64), FK): References `complaints.id` (cascade delete).
* `status` (VARCHAR(32)): `'open'` or `'resolved'`.
* `trigger_type` (VARCHAR(16)): `'auto'` or `'manual'`.
* `reason` (TEXT): Explanation for the escalation.
* `urgency_score_snapshot` (INTEGER): Snapshot of the complaint's urgency score at escalation time.
* `churn_risk_snapshot` (VARCHAR(32)): Snapshot of churn risk.
* `ai_confidence_snapshot` (FLOAT): Snapshot of AI confidence.
* `escalated_by` (VARCHAR(128)): Actor who escalated (for manual triggers).
* `escalated_at` (TIMESTAMP): Escalation date.
* `resolved_by` (VARCHAR(128)): Actor who resolved the escalation.
* `resolved_at` (TIMESTAMP): Date of resolution.
* `resolution_notes` (TEXT): Resolution explanation.
* `created_at` / `updated_at` (TIMESTAMP)

**Constraints & Indexes**:
* `ck_escalations_status`: Checks status is `'open'` or `'resolved'`.
* `ck_escalations_trigger_type`: Checks trigger type is `'auto'` or `'manual'`.
* `ix_escalations_complaint_pk_status`: Index on `(complaint_pk, status)` for fast lookup of active escalations.

### Auto-Escalation Engine
Implemented in [escalations/service.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/escalations/service.py#L202):
Evaluates processing outcomes upon completion and auto-escalates if any of the following rules are met:
1. **Critical Priority**: `urgency_score >= 90` (threshold defined by `HIGH_URGENCY_REVIEW_THRESHOLD`) AND `churn_risk == ChurnRisk.HIGH`.
2. **Critical Human Review**: Complaint is flagged with review reasons `HIGH_RISK_HIGH_URGENCY` or `BEDROCK_UNAVAILABLE_AFTER_RETRIES`.
3. **SLA Breach**: Complaint is classified as breach risk (computed dynamically via `SLAService().is_breach_risk`).

* **Dependencies**: Urgency, Churn Risk, Review Reason, and SLA breach outputs are consumed as read-only fields/calls without duplicating their logic.
* **Workflow Hook**: Triggered automatically inside `ProcessingService` in [processing_service.py:151](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/services/processing_service.py#L151) when AI finalization completes.

### API Endpoints
Defined in [escalations/router.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/escalations/router.py):
* `GET /api/escalations`: List/filter all escalations. (Accessible by: MANAGER, ADMIN)
* `GET /api/escalations/{escalation_id}`: Retrieve a single escalation. (Accessible by: MANAGER, ADMIN)
* `POST /api/escalations/{escalation_id}/resolve`: Mark an escalation as resolved with resolution notes. (Accessible by: MANAGER, ADMIN)
* `POST /api/complaints/{complaint_id}/escalate`: Manually escalate a complaint. (Accessible by: AGENT, MANAGER, ADMIN)

---

## 3. Operations Queue
An agent-facing queue used to prioritize actionable work.

### Filtering & Prioritizing
Defined in [operations/repository.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/operations/repository.py):
The queue returns complaints that require manual review or immediate agent action. A complaint qualifies if:
1. `ai_status == "human_review"`
2. `urgency_score >= 90`
3. It has an active, open escalation (`status == "open"` in `escalations` table).

**Ordering Rules**:
1. Sorted by `urgency_score` descending (nulls last).
2. Tied scores are sorted by `created_at` ascending (FIFO).

### API Endpoint
Defined in [operations/router.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/operations/router.py):
* `GET /api/operations/queue`: Returns paginated queue items containing snapshots of the complaint details, urgency score, review status, and active escalation references. (Accessible by: AGENT, MANAGER, ADMIN)

---

## 4. 360-Degree Complaint View
Consolidates all related details for a complaint into a single aggregated snapshot.

### API Endpoint
Defined in [communications/workspace.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/app/communications/workspace.py):
* `GET /api/complaints/{complaint_id}/360`: Consolidates data from multiple modules without mutating them:
  * **Complaint details**: `ComplaintDetail` via `ComplaintService().get_detail`
  * **Interaction history**: `TimelineResponse` via `CommunicationService().get_timeline`
  * **Duplicate detection**: Checks if the complaint is part of a duplicate group; if yes, fetches status and overall group member counts.
  * **Active Escalation**: Returns details of any open escalation (id, trigger type, escalated time, and reason).
  * Accessible by: AGENT, MANAGER, ADMIN.

---

## 5. Test Coverage
Verifies that all workflows behave correctly under unit test simulations.

* **Communications Tests**:
  * [test_communications.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/tests/communications/test_communications.py): Checks recording manual notes and timeline retrieval.
  * [test_workspace_360.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/tests/communications/test_workspace_360.py): Verifies compilation of core complaint, timeline, duplicates, and escalation parts.
* **Escalations Tests**:
  * [test_escalations.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/tests/escalations/test_escalations.py): Tests manual escalation constraints, resolution updates, and auto-escalation trigger logic (clean checks, high urgency/high churn rules, existing open escalations, and status guards).
* **Operations Tests**:
  * [test_operations_queue.py](file:///Users/yashkhadgi/Downloads/Test%20Customer/CustomerPulse/backend/tests/operations/test_operations_queue.py): Validates queue inclusion for human review, high urgency, and active open escalations, and verifies sorting and normal complaint exclusion.
