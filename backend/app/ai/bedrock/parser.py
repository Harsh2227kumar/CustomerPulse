import json
import re
from typing import Any


JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_object(raw_text: str) -> dict[str, Any]:
    stripped = raw_text.strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        match = JSON_OBJECT_RE.search(stripped)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Bedrock response must be a JSON object")
    return value
