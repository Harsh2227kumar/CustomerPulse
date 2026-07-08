from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.storage_models import ComplianceRuleRecord, ReasonCodeRecord

BASELINE_EFFECTIVE_FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)

BASELINE_REASON_CODES = [
    {
        "code": "SLA_BREACHED",
        "description": "Complaint handling SLA has been breached.",
        "severity": "high",
        "status": "active",
    },
    {
        "code": "SLA_WARNING",
        "description": "Complaint is approaching its configured SLA deadline.",
        "severity": "medium",
        "status": "active",
    },
    {
        "code": "KYC_UPDATE_OVERDUE",
        "description": "Customer KYC update is overdue under the applicable policy.",
        "severity": "high",
        "status": "active",
    },
    {
        "code": "KYC_DATA_MISSING",
        "description": "Mandatory KYC information is missing from the customer record.",
        "severity": "high",
        "status": "active",
    },
    {
        "code": "KYC_VERIFICATION_FAILED",
        "description": "KYC verification failed and requires remediation.",
        "severity": "critical",
        "status": "active",
    },
    {
        "code": "FRAUD_REPORT_DELAYED",
        "description": "Fraud reporting was delayed beyond the configured threshold.",
        "severity": "critical",
        "status": "active",
    },
    {
        "code": "REGULATORY_REPORT_MISSING",
        "description": "Required regulatory report is missing.",
        "severity": "critical",
        "status": "active",
    },
    {
        "code": "CUSTOMER_NOTIFICATION_DELAYED",
        "description": "Customer notification was delayed beyond the applicable obligation.",
        "severity": "medium",
        "status": "active",
    },
    {
        "code": "CUSTOMER_PROTECTION_BREACH",
        "description": "Customer protection obligation appears to be breached.",
        "severity": "critical",
        "status": "active",
    },
    {
        "code": "DOCUMENTATION_INCOMPLETE",
        "description": "Complaint documentation is incomplete.",
        "severity": "medium",
        "status": "active",
    },
    {
        "code": "MISSING_MANDATORY_DOCUMENT",
        "description": "A mandatory supporting document is missing.",
        "severity": "high",
        "status": "active",
    },
    {
        "code": "EVIDENCE_INSUFFICIENT",
        "description": "Investigation evidence is insufficient for audit readiness.",
        "severity": "high",
        "status": "active",
    },
    {
        "code": "ESCALATION_DELAYED",
        "description": "Complaint escalation was delayed beyond the configured SLA.",
        "severity": "high",
        "status": "active",
    },
]

BASELINE_RBI_RULES = [
    {
        "rule_id": "RBI-SLA-RESOLUTION-001",
        "rule_name": "Complaint Resolution SLA",
        "regulator": "RBI",
        "domain": "sla_compliance",
        "version": "1.0.0",
        "status": "active",
        "description": "Validate complaint resolution against the configured RBI resolution SLA.",
        "evaluation_type": "duration_threshold",
        "severity": "high",
        "reason_code": "SLA_BREACHED",
    },
    {
        "rule_id": "RBI-SLA-ESCALATION-001",
        "rule_name": "Escalation SLA",
        "regulator": "RBI",
        "domain": "sla_compliance",
        "version": "1.0.0",
        "status": "active",
        "description": "Validate complaint escalation completion against configured RBI escalation timelines.",
        "evaluation_type": "duration_threshold",
        "severity": "high",
        "reason_code": "ESCALATION_DELAYED",
    },
    {
        "rule_id": "RBI-SLA-FIRST-RESPONSE-001",
        "rule_name": "First Response SLA",
        "regulator": "RBI",
        "domain": "sla_compliance",
        "version": "1.0.0",
        "status": "active",
        "description": "Validate first customer response against configured RBI acknowledgement timelines.",
        "evaluation_type": "duration_threshold",
        "severity": "medium",
        "reason_code": "SLA_WARNING",
    },
    {
        "rule_id": "RBI-KYC-UPDATE-001",
        "rule_name": "KYC Update Overdue",
        "regulator": "RBI",
        "domain": "kyc_compliance",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag customer accounts where periodic KYC update is overdue.",
        "evaluation_type": "date_threshold",
        "severity": "high",
        "reason_code": "KYC_UPDATE_OVERDUE",
    },
    {
        "rule_id": "RBI-KYC-MISSING-001",
        "rule_name": "Missing KYC Information",
        "regulator": "RBI",
        "domain": "kyc_compliance",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag records missing mandatory KYC attributes.",
        "evaluation_type": "required_field",
        "severity": "high",
        "reason_code": "KYC_DATA_MISSING",
    },
    {
        "rule_id": "RBI-KYC-VERIFY-001",
        "rule_name": "KYC Verification Failure",
        "regulator": "RBI",
        "domain": "kyc_compliance",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag failed KYC verification outcomes for remediation.",
        "evaluation_type": "status_match",
        "severity": "critical",
        "reason_code": "KYC_VERIFICATION_FAILED",
    },
    {
        "rule_id": "RBI-FRAUD-DELAY-001",
        "rule_name": "Fraud Report Delay",
        "regulator": "RBI",
        "domain": "fraud_reporting",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag fraud cases where reporting is delayed beyond regulatory timelines.",
        "evaluation_type": "duration_threshold",
        "severity": "critical",
        "reason_code": "FRAUD_REPORT_DELAYED",
    },
    {
        "rule_id": "RBI-FRAUD-MISSING-001",
        "rule_name": "Missing Fraud Report",
        "regulator": "RBI",
        "domain": "fraud_reporting",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag confirmed or suspected fraud cases missing required fraud reports.",
        "evaluation_type": "required_document",
        "severity": "critical",
        "reason_code": "REGULATORY_REPORT_MISSING",
    },
    {
        "rule_id": "RBI-FRAUD-REG-REPORT-001",
        "rule_name": "Regulatory Reporting Violation",
        "regulator": "RBI",
        "domain": "fraud_reporting",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag fraud complaints that violate regulatory reporting obligations.",
        "evaluation_type": "policy_condition",
        "severity": "critical",
        "reason_code": "REGULATORY_REPORT_MISSING",
    },
    {
        "rule_id": "RBI-CUST-NOTIFY-001",
        "rule_name": "Customer Notification Delay",
        "regulator": "RBI",
        "domain": "customer_protection",
        "version": "1.0.0",
        "status": "active",
        "description": "Validate customer notifications against configured customer protection timelines.",
        "evaluation_type": "duration_threshold",
        "severity": "medium",
        "reason_code": "CUSTOMER_NOTIFICATION_DELAYED",
    },
    {
        "rule_id": "RBI-CUST-UNRESOLVED-001",
        "rule_name": "Unresolved Complaint Beyond Threshold",
        "regulator": "RBI",
        "domain": "customer_protection",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag unresolved complaints beyond the configured customer protection threshold.",
        "evaluation_type": "duration_threshold",
        "severity": "high",
        "reason_code": "CUSTOMER_PROTECTION_BREACH",
    },
    {
        "rule_id": "RBI-CUST-SERVICE-001",
        "rule_name": "Customer Service Obligation Breach",
        "regulator": "RBI",
        "domain": "customer_protection",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag breaches of customer service obligations configured for protected workflows.",
        "evaluation_type": "policy_condition",
        "severity": "critical",
        "reason_code": "CUSTOMER_PROTECTION_BREACH",
    },
    {
        "rule_id": "RBI-DOC-MANDATORY-001",
        "rule_name": "Missing Mandatory Documents",
        "regulator": "RBI",
        "domain": "documentation_validation",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag complaint records missing mandatory supporting documents.",
        "evaluation_type": "required_document",
        "severity": "high",
        "reason_code": "MISSING_MANDATORY_DOCUMENT",
    },
    {
        "rule_id": "RBI-DOC-INCOMPLETE-001",
        "rule_name": "Incomplete Complaint Record",
        "regulator": "RBI",
        "domain": "documentation_validation",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag incomplete complaint records that are not audit ready.",
        "evaluation_type": "required_field",
        "severity": "medium",
        "reason_code": "DOCUMENTATION_INCOMPLETE",
    },
    {
        "rule_id": "RBI-DOC-EVIDENCE-001",
        "rule_name": "Missing Investigation Evidence",
        "regulator": "RBI",
        "domain": "documentation_validation",
        "version": "1.0.0",
        "status": "active",
        "description": "Flag complaint investigations with missing or insufficient evidence.",
        "evaluation_type": "required_document",
        "severity": "high",
        "reason_code": "EVIDENCE_INSUFFICIENT",
    },
]


async def seed_compliance_knowledge_base(db: AsyncSession) -> None:
    for values in BASELINE_REASON_CODES:
        exists = await db.execute(select(ReasonCodeRecord.id).where(ReasonCodeRecord.code == values["code"]))
        if exists.scalar_one_or_none() is None:
            db.add(ReasonCodeRecord(**values))

    for values in BASELINE_RBI_RULES:
        exists = await db.execute(
            select(ComplianceRuleRecord.id).where(
                ComplianceRuleRecord.rule_id == values["rule_id"],
                ComplianceRuleRecord.version == values["version"],
            )
        )
        if exists.scalar_one_or_none() is None:
            db.add(ComplianceRuleRecord(**values, effective_from=BASELINE_EFFECTIVE_FROM))

    await db.commit()
