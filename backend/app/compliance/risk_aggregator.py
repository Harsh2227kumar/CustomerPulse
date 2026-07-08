from app.compliance.models import ComplianceRiskLevel, TriggeredRule


RISK_ORDER = {
    ComplianceRiskLevel.LOW: 0,
    ComplianceRiskLevel.MEDIUM: 1,
    ComplianceRiskLevel.HIGH: 2,
    ComplianceRiskLevel.CRITICAL: 3,
}


def aggregate_risk(triggered_rules: list[TriggeredRule]) -> ComplianceRiskLevel:
    if not triggered_rules:
        return ComplianceRiskLevel.LOW

    if any(rule.severity == ComplianceRiskLevel.CRITICAL for rule in triggered_rules):
        return ComplianceRiskLevel.CRITICAL

    high_count = sum(1 for rule in triggered_rules if rule.severity == ComplianceRiskLevel.HIGH)
    mandatory_count = sum(1 for rule in triggered_rules if rule.mandatory_action)
    rule_families = {rule.rule_id.split("-")[1] for rule in triggered_rules if "-" in rule.rule_id}
    if len(rule_families) > 1 and (high_count >= 2 or (high_count >= 1 and mandatory_count >= 2)):
        return ComplianceRiskLevel.CRITICAL

    highest = max(triggered_rules, key=lambda rule: RISK_ORDER[ComplianceRiskLevel(rule.severity)])
    if highest.severity == ComplianceRiskLevel.HIGH:
        return ComplianceRiskLevel.HIGH
    if len(triggered_rules) >= 2:
        return ComplianceRiskLevel.HIGH
    return ComplianceRiskLevel(highest.severity)
