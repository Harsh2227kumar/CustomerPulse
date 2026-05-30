from app.core.constants import Sentiment
import re

# ----------------------------
# BFSI Phrase Dictionaries
# ----------------------------

NEGATIVE_PHRASES = {
    "account frozen": "account_frozen",
    "account blocked": "account_blocked",
    "account locked": "account_locked",
    "transaction declined": "transaction_declined",
    "payment failed": "payment_failed",
    "payment declined": "payment_declined",
    "unauthorized debit": "unauthorized_transaction",
    "unauthorized transaction": "unauthorized_transaction",
    "unauthorized withdrawal": "unauthorized_transaction",
    "fraud transaction": "fraud_transaction",
    "fraud detected": "fraud_detected",
    "wrong amount debited": "wrong_amount_debited",
    "incorrect amount debited": "wrong_amount_debited",
    "double charged": "double_charge",
    "over charged": "overcharged",
    "overcharged": "overcharged",
    "late payment processing": "late_processing",
    "payment not received": "payment_missing",
    "money not received": "money_missing",
    "fund transfer failed": "transfer_failed",
    "bank not responding": "no_bank_response",
    "no response from bank": "no_bank_response",
    "customer support ignored": "support_ignored",
    "issue unresolved": "issue_unresolved",
    "complaint unresolved": "complaint_unresolved",
    "loan rejected": "loan_rejected",
    "loan denied": "loan_denied",
    "claim rejected": "claim_rejected",
    "claim denied": "claim_denied",
    "policy cancelled": "policy_cancelled",
    "policy expired unexpectedly": "policy_issue",
    "credit card blocked": "card_blocked",
    "debit card blocked": "card_blocked",
    "card not working": "card_failure",
    "atm cash not dispensed": "atm_failure",
    "incorrect balance": "balance_error",
    "missing transaction": "missing_transaction",
    "delayed refund": "refund_delay",
    "refund not received": "refund_missing",
    "service unavailable": "service_unavailable",
    "technical issue": "technical_issue",
}

POSITIVE_PHRASES = {
    "case resolved": "issue_resolved",
    "issue resolved": "issue_resolved",
    "complaint resolved": "complaint_resolved",
    "problem fixed": "problem_fixed",
    "issue fixed": "issue_fixed",
    "successfully credited": "amount_credited",
    "successfully refunded": "refund_processed",
    "refund received": "refund_received",
    "payment successful": "payment_success",
    "account restored": "account_restored",
    "account reactivated": "account_restored",
    "customer support helpful": "support_helpful",
    "satisfied with service": "customer_satisfied",
    "thank you for support": "gratitude",
    "case closed": "issue_resolved",
}

NEGATIVE_TERMS = {
    "angry",
    "awful",
    "bad",
    "denied",
    "disappointed",
    "error",
    "failed",
    "fraud",
    "ignored",
    "incorrect",
    "late",
    "lost",
    "missing",
    "overcharged",
    "problem",
    "refused",
    "scam",
    "terrible",
    "unauthorized",
    "unfair",
    "unresolved",
    "wrong",
    "declined",
    "blocked",
    "frozen",
    "locked",
}

POSITIVE_TERMS = {
    "resolved",
    "helpful",
    "satisfied",
    "thank",
    "thanks",
    "corrected",
    "fixed",
    "successful",
    "restored",
    "credited",
    "refunded",
}

NEGATION_WORDS = {"not", "never", "no"}


def _clean_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())


def _tokenize(text: str) -> list[str]:
    return _clean_text(text).split()


def _has_negation(tokens: list[str], index: int) -> bool:
    """
    Detect negation within previous 2-word window.
    Example:
    not helpful
    never resolved
    no satisfied
    """
    start = max(0, index - 2)

    return any(
        token in NEGATION_WORDS
        for token in tokens[start:index]
    )


def predict_sentiment(
    text: str,
) -> tuple[Sentiment, float, list[str]]:

    cleaned = _clean_text(text)
    tokens = _tokenize(text)

    negative_score = 0
    positive_score = 0
    reason_codes = set()

    # ----------------------------
    # Phrase-level detection
    # ----------------------------

    for phrase, code in NEGATIVE_PHRASES.items():
        if phrase in cleaned:
            negative_score += 2
            reason_codes.add(code)

    for phrase, code in POSITIVE_PHRASES.items():
        if phrase in cleaned:
            positive_score += 2
            reason_codes.add(code)

    # ----------------------------
    # Word-level detection
    # with negation support
    # ----------------------------

    for idx, word in enumerate(tokens):

        negated = _has_negation(tokens, idx)

        if word in NEGATIVE_TERMS:
            if negated:
                positive_score += 1
                reason_codes.add("negation_detected")
            else:
                negative_score += 1

        elif word in POSITIVE_TERMS:
            if negated:
                negative_score += 1
                reason_codes.add("negation_detected")
            else:
                positive_score += 1

    # ----------------------------
    # Sentiment decision
    # ----------------------------

    if negative_score > positive_score:
        confidence = min(
            0.95,
            0.55 + (negative_score * 0.06)
        )
        sentiment = Sentiment.NEGATIVE

    elif positive_score > negative_score:
        confidence = min(
            0.90,
            0.55 + (positive_score * 0.06)
        )
        sentiment = Sentiment.POSITIVE

    else:
        confidence = 0.5
        sentiment = Sentiment.NEUTRAL

    return (
        sentiment,
        round(confidence, 2),
        sorted(reason_codes)
    )


# -------------------------------------
# Simple Tests
# -------------------------------------

if __name__ == "__main__":

    test_cases = [

        # 1. Pure negative BFSI complaint
        "My account frozen and unauthorized debit happened. No response from bank.",

        # 2. Negation case
        "Customer support was not helpful and issue never resolved.",

        # 3. Ambiguous / neutral
        "I submitted a complaint yesterday and waiting for an update.",

        # 4. Positive resolution case
        "My case resolved successfully and refund received. Thanks for support.",

        # 5. Mixed signals
        "Payment failed initially but issue resolved and customer support helpful.",
    ]

    for i, text in enumerate(test_cases, start=1):
        result = predict_sentiment(text)

        print(f"\nTest {i}")
        print("-" * 50)
        print("Input:", text)
        print("Output:", result)