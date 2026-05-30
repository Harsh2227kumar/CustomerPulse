from dataclasses import dataclass


@dataclass(frozen=True)
class ComplaintSignals:
    has_escalation_terms: bool
    has_legal_terms: bool
    has_financial_harm_terms: bool
    has_waiting_terms: bool


ESCALATION_TERMS = {"complaint", "supervisor", "manager", "escalate", "cfpb", "ombudsman"}
LEGAL_TERMS = {"lawsuit", "legal", "attorney", "fraud", "unauthorized", "dispute"}
FINANCIAL_HARM_TERMS = {"fee", "fees", "charged", "loss", "refund", "debt", "foreclosure", "overdraft"}
WAITING_TERMS = {"waiting", "weeks", "months", "delayed", "ignored", "unresolved", "pending"}


def extract_signals(text: str) -> ComplaintSignals:
    words = {word.strip(".,!?;:()[]{}\"'").lower() for word in text.split()}
    return ComplaintSignals(
        has_escalation_terms=bool(words & ESCALATION_TERMS),
        has_legal_terms=bool(words & LEGAL_TERMS),
        has_financial_harm_terms=bool(words & FINANCIAL_HARM_TERMS),
        has_waiting_terms=bool(words & WAITING_TERMS),
    )
