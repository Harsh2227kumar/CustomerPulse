import re

from app.intelligence.reason_codes import ReasonCodeHit, detect_reason_code_hits
from app.schemas.ai_response import EvidenceSnippet


class EvidenceService:
    def snippets_for_text(
        self,
        text: str,
        *,
        max_snippets: int = 6,
    ) -> list[EvidenceSnippet]:
        hits = detect_reason_code_hits(text)
        snippets: list[EvidenceSnippet] = []
        seen: set[tuple[str, str]] = set()
        for hit in hits:
            snippet = self._sentence_containing(text, hit)
            key = (hit.reason_code, snippet.lower())
            if key in seen:
                continue
            seen.add(key)
            snippets.append(
                EvidenceSnippet(
                    text=snippet,
                    reason_code=hit.reason_code,
                    matched_phrase=hit.matched_phrase,
                    start_char=hit.start,
                    end_char=hit.end,
                    source="narrative",
                )
            )
            if len(snippets) >= max_snippets:
                break
        return snippets

    def snippet_for_phrase(
        self,
        text: str,
        phrase: str,
        *,
        reason_code: str | None = None,
    ) -> EvidenceSnippet | None:
        match = re.search(re.escape(phrase), text, flags=re.IGNORECASE)
        if not match:
            return None
        return EvidenceSnippet(
            text=self._sentence_containing(
                text,
                ReasonCodeHit(
                    reason_code=reason_code or "supporting_evidence",
                    matched_phrase=text[match.start() : match.end()],
                    start=match.start(),
                    end=match.end(),
                ),
            ),
            reason_code=reason_code,
            matched_phrase=text[match.start() : match.end()],
            start_char=match.start(),
            end_char=match.end(),
            source="narrative",
        )

    def _sentence_containing(self, text: str, hit: ReasonCodeHit) -> str:
        left_candidates = [text.rfind(mark, 0, hit.start) for mark in (".", "!", "?", "\n")]
        right_candidates = [text.find(mark, hit.end) for mark in (".", "!", "?", "\n")]
        left = max(left_candidates) + 1
        positive_right = [index for index in right_candidates if index >= 0]
        right = min(positive_right) + 1 if positive_right else min(len(text), hit.end + 220)
        snippet = " ".join(text[left:right].split())
        if len(snippet) > 360:
            snippet = snippet[:357].rstrip() + "..."
        return snippet

