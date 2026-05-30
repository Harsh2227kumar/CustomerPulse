# backend/app/ai/ml_models/urgency.py

from app.ai.preprocessing.extractor import ComplaintSignals


# -------------------------------------------------------
# Phrase dictionaries
# -------------------------------------------------------

FRAUD_PHRASES = {
    "unauthorized transaction",
    "fraud detected",
    "identity theft",
    "account hacked",
    "card stolen",
    "money stolen",
}

FINANCIAL_LOSS_PHRASES = {
    "money debited",
    "wrong amount",
    "double charged",
    "incorrect deduction",
    "lost money",
    "funds missing",
}

BLOCKED_ACCESS_PHRASES = {
    "account frozen",
    "account blocked",
    "account locked",
    "card blocked",
    "access denied",
}

LEGAL_PHRASES = {
    "legal action",
    "attorney",
    "lawsuit",
    "file complaint",
    "regulatory",
    "report to cfpb",
    "escalate",
}

FAILED_PAYMENT_PHRASES = {
    "payment failed",
    "transaction failed",
    "transfer failed",
    "payment declined",
}

REPEAT_CONTACT_PHRASES = {
    "called multiple times",
    "third time contacting",
    "already complained",
    "still unresolved",
    "multiple attempts",
}


# -------------------------------------------------------
# Utility
# -------------------------------------------------------

def _find_matches(text: str, phrases: set[str]) -> bool:
    return any(
        phrase in text
        for phrase in phrases
    )


# -------------------------------------------------------
# Main function
# -------------------------------------------------------

def estimate_urgency(
    text: str,
    signals: ComplaintSignals
) -> tuple[int, float, list[str], str, str]:

    lowered = text.lower()

    score = 25
    reason_codes = []

    fraud = False
    legal = False
    financial = False
    blocked = False
    failed_payment = False
    repeat_contact = False

    signal_count = 0

    # -------------------------------------------
    # Fraud
    # -------------------------------------------

    if _find_matches(lowered, FRAUD_PHRASES):
        score += 25
        signal_count += 1
        fraud = True
        reason_codes.append(
            "fraud_indicator"
        )

    # -------------------------------------------
    # Financial loss
    # -------------------------------------------

    if _find_matches(
        lowered,
        FINANCIAL_LOSS_PHRASES
    ):
        score += 20
        signal_count += 1
        financial = True
        reason_codes.append(
            "financial_loss"
        )

    # -------------------------------------------
    # Account access issues
    # -------------------------------------------

    if _find_matches(
        lowered,
        BLOCKED_ACCESS_PHRASES
    ):
        score += 20
        signal_count += 1
        blocked = True
        reason_codes.append(
            "blocked_access"
        )

    # -------------------------------------------
    # Legal
    # -------------------------------------------

    if _find_matches(
        lowered,
        LEGAL_PHRASES
    ):
        score += 20
        signal_count += 1
        legal = True
        reason_codes.append(
            "legal_escalation"
        )

    # -------------------------------------------
    # Payment failure
    # -------------------------------------------

    if _find_matches(
        lowered,
        FAILED_PAYMENT_PHRASES
    ):
        score += 15
        signal_count += 1
        failed_payment = True
        reason_codes.append(
            "payment_failure"
        )

    # -------------------------------------------
    # Repeat contact
    # -------------------------------------------

    if _find_matches(
        lowered,
        REPEAT_CONTACT_PHRASES
    ):
        score += 15
        signal_count += 1
        repeat_contact = True
        reason_codes.append(
            "repeat_contact"
        )

    # -------------------------------------------
    # Existing extractor signals
    # -------------------------------------------

    if signals.has_waiting_terms:
        score += 10
        signal_count += 1
        reason_codes.append(
            "waiting_delay"
        )

    if signals.has_escalation_terms:
        score += 10
        signal_count += 1
        reason_codes.append(
            "escalation_signal"
        )

    if signals.has_legal_terms:
        score += 20
        signal_count += 1

        if "legal_escalation" not in reason_codes:
            reason_codes.append(
                "legal_escalation"
            )

    if signals.has_financial_harm_terms:
        score += 20
        signal_count += 1

        if "financial_loss" not in reason_codes:
            reason_codes.append(
                "financial_loss"
            )

    # -------------------------------------------
    # Score limit
    # -------------------------------------------

    score = max(
        0,
        min(
            100,
            score
        )
    )

    # -------------------------------------------
    # Confidence
    # -------------------------------------------

    confidence = min(
        0.95,
        round(
            0.50 + (signal_count * 0.06),
            2
        )
    )

    # -------------------------------------------
    # FIXED CASE RISK LOGIC
    # Strict score-based
    # -------------------------------------------

    if (
        score >= 85
        or (fraud and legal)
    ):

        case_risk = "Critical"

        if fraud and legal:
            risk_reason = (
                "Critical urgency due to fraud "
                "indicator with legal escalation."
            )
        else:
            risk_reason = (
                "Critical urgency due to "
                "very high complaint severity score."
            )

    elif score >= 65:

        case_risk = "High"

        risk_reason = (
            "High urgency due to multiple "
            "high-impact complaint indicators."
        )

    elif score >= 40:

        case_risk = "Medium"

        reasons = []

        if financial:
            reasons.append("financial loss")

        if blocked:
            reasons.append("account access blocked")

        if failed_payment:
            reasons.append("failed payment")

        if repeat_contact:
            reasons.append("repeat contact")

        if not reasons:
            reasons.append(
                "moderate issue severity"
            )

        risk_reason = (
            "Medium risk — "
            + " with ".join(reasons)
        )

    else:

        case_risk = "Low"

        risk_reason = (
            "Low urgency due to "
            "minor issue indicators."
        )

    return (
        score,
        confidence,
        sorted(set(reason_codes)),
        case_risk,
        risk_reason
    )


# -------------------------------------------------------
# Tests
# -------------------------------------------------------

if __name__ == "__main__":

    empty = ComplaintSignals(
        has_escalation_terms=False,
        has_legal_terms=False,
        has_financial_harm_terms=False,
        has_waiting_terms=False
    )

    waiting = ComplaintSignals(
        has_escalation_terms=False,
        has_legal_terms=False,
        has_financial_harm_terms=False,
        has_waiting_terms=True
    )

    tests = [

        (
            "Unauthorized transaction and "
            "identity theft. I will take "
            "legal action and report to CFPB.",
            empty
        ),

        (
            "Wrong amount money debited "
            "and funds missing.",
            empty
        ),

        (
            "My account blocked and "
            "payment failed.",
            empty
        ),

        (
            "This is my third time contacting. "
            "Already complained and still unresolved.",
            empty
        ),

        (
            "Waiting for response "
            "from bank for many days.",
            waiting
        ),

        (
            "Need statement copy.",
            empty
        )
    ]

    for i, (text, signal) in enumerate(
        tests,
        start=1
    ):

        result = estimate_urgency(
            text,
            signal
        )

        print(f"\nTest {i}")
        print("-" * 60)
        print("Input:")
        print(text)

        print("\nOutput:")
        print(result)