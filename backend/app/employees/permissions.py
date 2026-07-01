"""Role capability map for the CustomerPulse admin system.

DESIGN NOTE (Hackathon scope):
    This is intentionally a static, hardcoded map.  In a production system
    this would be backed by a database ``permissions`` / ``role_capabilities``
    table, editable by super-admins via an API, and potentially per-tenant.
    For the hackathon we keep it simple: one source-of-truth dict, evaluated
    at import time, read-only from the API.
"""
from __future__ import annotations

from app.core.constants import Role

# ─── Atomic capability strings ────────────────────────────────────────────────
# Keep names in snake_case and grouped by domain for readability.

_COMPLAINT_CAPS = [
    "view_assigned_complaints",
    "view_team_complaints",
    "view_complaint_monitoring",
]

_AI_CAPS = [
    "use_ai_assistant",
]

_REVIEW_CAPS = [
    "submit_review_feedback",
    "approve_review",
    "resolve_review",
]

_ESCALATION_CAPS = [
    "create_escalation",
    "resolve_escalation",
]

_ANALYTICS_CAPS = [
    "view_analytics",
    "export_reports",
]

_ADMIN_CAPS = [
    "manage_employees",
    "manage_departments",
    "view_audit_logs",
    "manage_compliance_rules",
]

_SUPER_ADMIN_CAPS = [
    "manage_admins",    # can create/promote admin-level employees
    "system_settings",  # access to system-wide configuration
]

# ─── Role → capabilities ──────────────────────────────────────────────────────
#
# NOTE: Audit logs are append-only by design and are NEVER deletable — not even
# by super_admin.  This is intentional for compliance and security audit trails.

ROLE_CAPABILITIES: dict[Role, list[str]] = {
    Role.AGENT: [
        "view_assigned_complaints",
        "use_ai_assistant",
        "submit_review_feedback",
    ],

    Role.MANAGER: [
        "view_assigned_complaints",
        "view_team_complaints",
        "use_ai_assistant",
        "approve_review",
        "resolve_review",
        "view_analytics",
        "create_escalation",
        "resolve_escalation",
        "export_reports",
    ],

    Role.ADMIN: [
        "manage_employees",
        "manage_departments",
        "view_audit_logs",
        "view_analytics",
        "view_complaint_monitoring",
        "export_reports",
        "manage_compliance_rules",
    ],

    Role.SUPER_ADMIN: [
        # All admin capabilities …
        "manage_employees",
        "manage_departments",
        "view_audit_logs",
        "view_analytics",
        "view_complaint_monitoring",
        "export_reports",
        "manage_compliance_rules",
        # … plus elevated super-admin-only capabilities
        "manage_admins",
        "system_settings",
    ],
}


def capabilities_for(role: Role | str) -> list[str]:
    """Return the capability list for the given role (accepts str or Role)."""
    if isinstance(role, str):
        role = Role(role)
    return list(ROLE_CAPABILITIES.get(role, []))


def all_roles_map() -> dict[str, list[str]]:
    """Return the full map keyed by role string (JSON-serialisable)."""
    return {role.value: list(caps) for role, caps in ROLE_CAPABILITIES.items()}
