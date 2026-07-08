from app.compliance.reporting.models import ComplianceReportField


REPORT_FIELD_REGISTRY: list[ComplianceReportField] = [
    ComplianceReportField(
        field_key="complaint_id",
        display_label="Complaint ID",
        field_type="string",
        required_for_regulatory=True,
        source_module="compliance_engine",
        notes="Stable complaint identifier used to reconcile the export with source records.",
    ),
    ComplianceReportField(
        field_key="evaluated_at",
        display_label="Evaluated At",
        field_type="datetime",
        required_for_regulatory=True,
        source_module="compliance_engine",
        notes="Timestamp when compliance evaluation was completed.",
    ),
    ComplianceReportField(
        field_key="compliance_risk_level",
        display_label="Compliance Risk Level",
        field_type="string",
        required_for_regulatory=True,
        source_module="compliance_engine",
        notes="Final compliance severity assigned to the complaint.",
    ),
    ComplianceReportField(
        field_key="dominant_rule_id",
        display_label="Dominant Rule ID",
        field_type="string",
        required_for_regulatory=True,
        source_module="compliance_engine",
        notes="Highest-priority rule used to explain the primary compliance outcome.",
    ),
    ComplianceReportField(
        field_key="rules_triggered",
        display_label="Rules Triggered",
        field_type="list",
        required_for_regulatory=True,
        source_module="compliance_engine",
        notes="Rule identifiers fired during compliance evaluation.",
    ),
    ComplianceReportField(
        field_key="required_actions",
        display_label="Required Actions",
        field_type="list",
        required_for_regulatory=True,
        source_module="compliance_engine",
        notes="Plain-English remediation actions required by triggered rules.",
    ),
    ComplianceReportField(
        field_key="regulatory_breach",
        display_label="Regulatory Breach",
        field_type="boolean",
        required_for_regulatory=True,
        source_module="compliance_engine",
        notes="True when at least one critical rule was triggered.",
    ),
    ComplianceReportField(
        field_key="sla_compliance_status",
        display_label="SLA Compliance Status",
        field_type="string",
        required_for_regulatory=True,
        source_module="sla",
        notes="SLA status supplied by Member 3 for reporting segmentation.",
    ),
    ComplianceReportField(
        field_key="evidence_summary",
        display_label="Evidence Summary",
        field_type="list",
        required_for_regulatory=True,
        source_module="explainability",
        notes="Flattened evidence snippets supporting the compliance decision.",
    ),
    ComplianceReportField(
        field_key="audit_trail",
        display_label="Audit Trail",
        field_type="string",
        required_for_regulatory=True,
        source_module="compliance_engine",
        notes="Version and timing metadata flattened into audit-prefixed export columns.",
    ),
    ComplianceReportField(
        field_key="export_flags",
        display_label="Export Flags",
        field_type="string",
        required_for_regulatory=False,
        source_module="compliance_engine",
        notes="Report preset eligibility flags flattened into flag-prefixed export columns.",
    ),
    ComplianceReportField(
        field_key="category",
        display_label="Category",
        field_type="string",
        required_for_regulatory=False,
        source_module="member_1",
        notes="Complaint category from Member 1 used for report filtering.",
    ),
]


def get_required_fields() -> list[ComplianceReportField]:
    return [field for field in REPORT_FIELD_REGISTRY if field.required_for_regulatory]


def get_all_fields() -> list[ComplianceReportField]:
    return list(REPORT_FIELD_REGISTRY)


def get_fields_by_source(source_module: str) -> list[ComplianceReportField]:
    return [field for field in REPORT_FIELD_REGISTRY if field.source_module == source_module]
