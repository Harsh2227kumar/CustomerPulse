import re
from dataclasses import dataclass


_WHITESPACE_RE = re.compile(r"\s+")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")


@dataclass(frozen=True)
class CleanedText:
    original: str
    cleaned: str
    token_estimate: int


def clean_complaint_text(text: str) -> CleanedText:
    cleaned = _CONTROL_RE.sub(" ", text)
    cleaned = _URL_RE.sub("[URL]", cleaned)
    cleaned = _EMAIL_RE.sub("[EMAIL]", cleaned)
    cleaned = _PHONE_RE.sub("[PHONE]", cleaned)
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    token_estimate = max(1, len(cleaned.split()))
    return CleanedText(original=text, cleaned=cleaned, token_estimate=token_estimate)
