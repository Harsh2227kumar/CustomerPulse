from app.compliance.explainability.models import RiskJustification, RuleExplanation


SEVERITY_RANK: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


def _severity_for_rule(rule: RuleExplanation) -> str:
    lowered_text = f"{rule.rule_id} {rule.rule_description} {rule.why_triggered}".lower()
    for severity in ("critical", "high", "medium", "low"):
        if severity in lowered_text:
            return severity
    return "low"


def justify_risk(
    rule_explanations: list[RuleExplanation],
    risk_level: str,
) -> RiskJustification:
    if rule_explanations:
        dominant_rule = max(
            rule_explanations,
            key=lambda rule: (SEVERITY_RANK[_severity_for_rule(rule)], rule.rule_id),
        )
        dominant_rule_id = dominant_rule.rule_id
    else:
        dominant_rule_id = "none"

    contributing_factors = [
        f"{rule.rule_id}: {rule.rule_description}" for rule in rule_explanations
    ]
    total_rules = len(rule_explanations)
    reason_summary = (
        f"Overall compliance risk is {risk_level} because {total_rules} rule(s) "
        f"triggered, with {dominant_rule_id} as the dominant rule."
    )

    return RiskJustification(
        overall_risk_level=risk_level,
        reason_summary=reason_summary,
        contributing_factors=contributing_factors,
        dominant_rule_id=dominant_rule_id,
    )
