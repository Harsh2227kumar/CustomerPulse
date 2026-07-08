from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ReasonCodeHit:
    reason_code: str
    matched_phrase: str
    start: int
    end: int


REASON_CODE_PHRASES: dict[str, tuple[str, ...]] = {
    "credit_reporting_issue": (
        "credit report",
        "credit score",
        "consumer report",
        "credit bureau",
        "inaccurate information",
        "incorrect information on my report",
        "fair credit reporting act",
        "fcra",
        "15 usc 1681",
    ),
    "legal_or_fraud_language": (
        "legal action",
        "attorney",
        "lawsuit",
        "illegal",
        "regulatory",
        "cfpb",
        "fraud",
        "fraudulent",
        "deceptive",
    ),
    "escalation_language": (
        "escalate",
        "supervisor",
        "manager",
        "formal complaint",
        "file a complaint",
        "reopen the case",
    ),
    "financial_harm": (
        "financial harm",
        "money stolen",
        "lost money",
        "funds missing",
        "holding my money",
        "water was turned off",
        "unable to pay",
    ),
    "high_urgency_language": (
        "urgent",
        "immediately",
        "as soon as possible",
        "emergency",
        "demand",
        "grave",
    ),
    "fee_dispute": (
        "fee",
        "fees",
        "charged",
        "charge",
        "overdraft",
        "interest",
        "late fee",
        "stop payment fee",
    ),
    "delayed_response": (
        "no response",
        "not received a response",
        "never received",
        "waiting",
        "several attempts",
        "multiple attempts",
        "over 30 days",
    ),
    "unauthorized_transaction": (
        "unauthorized transaction",
        "unauthorized charge",
        "unauthorized charges",
        "not authorized",
        "without my authorization",
        "without my knowledge or consent",
        "did not authorize",
    ),
    "identity_theft_signal": (
        "identity theft",
        "stolen my identity",
        "social security number",
        "accounts that are not mine",
        "information belongs to someone else",
    ),
    "loan_or_mortgage_issue": (
        "mortgage",
        "loan",
        "servicer",
        "foreclosure",
        "escrow",
        "vehicle loan",
        "student loan",
    ),
    "refund_dispute": (
        "refund",
        "refunded",
        "credit will still exist",
        "provisional credit",
    ),
    "account_access_issue": (
        "account frozen",
        "account hold",
        "account locked",
        "account closed",
        "unable to access",
        "unable to login",
    ),
    "duplicate_charge": (
        "charged twice",
        "double charged",
        "duplicate charge",
        "same charge",
    ),
    "debt_collection_issue": (
        "debt collection",
        "debt collector",
        "collect debt",
        "debt not owed",
        "validation of debt",
        "fdcpa",
    ),
    "payment_or_transfer_issue": (
        "money transfer",
        "wire transfer",
        "zelle",
        "cash app",
        "mobile wallet",
        "payment failed",
        "transaction problem",
    ),
}


def detect_reason_code_hits(text: str) -> list[ReasonCodeHit]:
    hits: list[ReasonCodeHit] = []
    lowered = text.lower()
    for reason_code, phrases in REASON_CODE_PHRASES.items():
        for phrase in phrases:
            pattern = re.escape(phrase.lower())
            for match in re.finditer(pattern, lowered):
                hits.append(
                    ReasonCodeHit(
                        reason_code=reason_code,
                        matched_phrase=text[match.start() : match.end()],
                        start=match.start(),
                        end=match.end(),
                    )
                )
    return sorted(hits, key=lambda hit: (hit.start, hit.reason_code, hit.matched_phrase))


def detect_reason_codes(text: str) -> list[str]:
    return sorted({hit.reason_code for hit in detect_reason_code_hits(text)})

