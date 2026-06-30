from app.intelligence.evidence_service import EvidenceService
from app.schemas.ai_response import DecisionSource, KeyIssueResult


class KeyIssueService:
    def __init__(self, evidence_service: EvidenceService | None = None) -> None:
        self.evidence_service = evidence_service or EvidenceService()

    def extract(
        self,
        narrative: str,
        *,
        product: str | None = None,
        issue: str | None = None,
        category: str | None = None,
    ) -> KeyIssueResult:
        evidence = self.evidence_service.snippets_for_text(narrative, max_snippets=3)
        reason_codes = sorted({snippet.reason_code for snippet in evidence if snippet.reason_code})
        summary = self._summary_from_context(
            narrative,
            product=product,
            issue=issue,
            category=category,
            evidence_text=evidence[0].text if evidence else None,
        )
        confidence = 0.78 if issue and evidence else 0.68 if issue or evidence else 0.52
        return KeyIssueResult(
            summary=summary,
            evidence_snippets=evidence,
            reason_codes=reason_codes,
            confidence=confidence,
            source=DecisionSource(provider="customerpulse", model="deterministic-key-issue-v1"),
        )

    def _summary_from_context(
        self,
        narrative: str,
        *,
        product: str | None,
        issue: str | None,
        category: str | None,
        evidence_text: str | None,
    ) -> str:
        base = issue or category or "Complaint requires review"
        if product:
            base = f"{base} for {product}"
        detail = evidence_text or self._first_sentence(narrative)
        detail = detail.strip()
        if detail:
            return f"{base}: {detail[:180].rstrip()}"
        return base

    def _first_sentence(self, text: str) -> str:
        normalized = " ".join(text.split())
        for mark in (".", "!", "?"):
            index = normalized.find(mark)
            if 0 <= index <= 220:
                return normalized[: index + 1]
        return normalized[:220]

