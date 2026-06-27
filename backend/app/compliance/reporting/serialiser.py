from datetime import datetime
from typing import Any

from app.compliance.reporting.field_registry import get_all_fields
from app.compliance.reporting.models import ComplianceReportRecord


BASE_EXPORT_HEADERS = [
    "complaint_id",
    "evaluated_at",
    "compliance_risk_level",
    "dominant_rule_id",
    "rules_triggered",
    "required_actions",
    "regulatory_breach",
    "sla_compliance_status",
    "evidence_summary",
    "category",
]

DEFAULT_AUDIT_KEYS = ["engine_version", "rule_set_version", "evaluated_at"]
DEFAULT_EXPORT_FLAG_KEYS = ["rbi_monthly", "cfpb_quarterly"]


def serialise_record(record: ComplianceReportRecord) -> dict[str, str | bool | float]:
    output: dict[str, str | bool | float] = {
        "complaint_id": record.complaint_id,
        "evaluated_at": record.evaluated_at.isoformat(),
        "compliance_risk_level": record.compliance_risk_level,
        "dominant_rule_id": record.dominant_rule_id,
        "rules_triggered": "|".join(record.rules_triggered),
        "required_actions": _numbered_list(record.required_actions),
        "regulatory_breach": record.regulatory_breach,
        "sla_compliance_status": record.sla_compliance_status,
        "evidence_summary": "; ".join(record.evidence_summary),
        "category": record.category or "",
    }

    output.update(_flatten_prefixed("audit", record.audit_trail))
    output.update(_flatten_prefixed("flag", record.export_flags))
    return output


def serialise_records(records: list[ComplianceReportRecord]) -> list[dict[str, str | bool | float]]:
    return [serialise_record(record) for record in records]


def get_export_headers() -> list[str]:
    registry_headers = [
        field.field_key
        for field in get_all_fields()
        if field.field_key not in {"audit_trail", "export_flags"}
    ]
    headers = [header for header in BASE_EXPORT_HEADERS if header in registry_headers]
    headers.extend(f"audit_{key}" for key in DEFAULT_AUDIT_KEYS)
    headers.extend(f"flag_{key}" for key in DEFAULT_EXPORT_FLAG_KEYS)
    return headers


def _numbered_list(values: list[str]) -> str:
    return " ".join(f"{index}. {value}" for index, value in enumerate(values, start=1))


def _flatten_prefixed(prefix: str, values: dict[str, Any]) -> dict[str, str | bool | float]:
    flattened: dict[str, str | bool | float] = {}
    for key, value in values.items():
        flattened[f"{prefix}_{key}"] = _to_flat_value(value)
    return flattened


def _to_flat_value(value: Any) -> str | bool | float:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)
