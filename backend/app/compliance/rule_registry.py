import json
from functools import lru_cache
from pathlib import Path

from app.compliance.models import ComplianceRule


RULES_PATH = Path(__file__).with_name("rules.json")


@lru_cache(maxsize=1)
def load_rule_registry(path: Path = RULES_PATH) -> tuple[ComplianceRule, ...]:
    raw_rules = json.loads(path.read_text(encoding="utf-8-sig"))
    return tuple(ComplianceRule.model_validate(rule) for rule in raw_rules)
