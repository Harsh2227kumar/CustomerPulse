# backend/app/ai/ml_models/classifier.py

import re

DEFAULT_CATEGORY = "General complaint"

STANDARD_CATEGORIES = [
    "Billing or fees",
    "Fraud or unauthorized activity",
    "Account servicing",
    "Credit reporting",
    "Loan or mortgage issue",
    "Card services",
    "Digital banking or transfers",
    "Insurance or investment",
    "Customer service failure",
    "General complaint",
]

# ---------------------------------------------------
# Category phrase dictionaries
# (15+ phrases each)
# ---------------------------------------------------

CATEGORY_PHRASES = {

    "Billing or fees": {
        "overdraft fee",
        "hidden charges",
        "incorrect fee",
        "annual fee",
        "maintenance fee",
        "extra charges",
        "late fee",
        "billing error",
        "double charged",
        "wrong amount debited",
        "unexpected charge",
        "service fee",
        "processing fee",
        "charged twice",
        "fee deducted",
        "incorrect billing",
    },

    "Fraud or unauthorized activity": {
        "unauthorized debit",
        "unauthorized transaction",
        "fraud transaction",
        "fraud detected",
        "identity theft",
        "account hacked",
        "stolen card",
        "card stolen",
        "unknown transaction",
        "money stolen",
        "scam payment",
        "fake transaction",
        "unauthorized withdrawal",
        "suspicious transaction",
        "account compromised",
        "fraud alert",
    },

    "Account servicing": {
        "account frozen",
        "account blocked",
        "account locked",
        "account closed",
        "statement missing",
        "balance incorrect",
        "incorrect balance",
        "account inaccessible",
        "unable to login",
        "password issue",
        "kyc issue",
        "account not active",
        "account reactivation",
        "account suspended",
        "account unavailable",
        "balance mismatch",
    },

    "Credit reporting": {
        "credit score",
        "credit report",
        "incorrect report",
        "bureau error",
        "inaccurate report",
        "wrong credit score",
        "credit history",
        "report issue",
        "incorrect credit information",
        "credit inquiry",
        "credit dispute",
        "wrong account record",
        "report mismatch",
        "credit bureau",
        "negative report",
        "incorrect information",
    },

    "Loan or mortgage issue": {
        "loan rejected",
        "mortgage issue",
        "loan denied",
        "interest issue",
        "foreclosure notice",
        "emi issue",
        "loan payment",
        "interest calculation",
        "wrong emi",
        "mortgage payment",
        "loan servicing",
        "late payment",
        "loan processing",
        "loan application",
        "loan closure",
        "interest charged",
    },

    "Card services": {
        "credit card blocked",
        "debit card blocked",
        "card declined",
        "card not working",
        "atm issue",
        "atm cash not dispensed",
        "card payment failed",
        "card damaged",
        "replacement card",
        "card expired",
        "wrong card charge",
        "pin issue",
        "transaction declined",
        "card limit issue",
        "card activation",
        "contactless payment issue",
    },

    "Digital banking or transfers": {
        "fund transfer failed",
        "money transfer issue",
        "payment failed",
        "transaction pending",
        "refund pending",
        "upi issue",
        "mobile banking issue",
        "internet banking issue",
        "payment delayed",
        "money not received",
        "bank app issue",
        "digital wallet issue",
        "transfer failed",
        "transaction timeout",
        "payment gateway issue",
        "online banking error",
    },

    "Insurance or investment": {
        "insurance claim",
        "claim denied",
        "policy cancelled",
        "policy expired",
        "investment issue",
        "mutual fund issue",
        "insurance premium",
        "claim rejected",
        "policy issue",
        "stock investment",
        "insurance payment",
        "investment loss",
        "claim processing",
        "coverage issue",
        "insurance fraud",
        "portfolio issue",
    },

    "Customer service failure": {
        "no response from bank",
        "customer support ignored",
        "call not answered",
        "poor customer service",
        "never resolved",
        "issue unresolved",
        "complaint unresolved",
        "support not helpful",
        "ignored complaint",
        "delay in response",
        "unhelpful support",
        "long waiting time",
        "support unavailable",
        "escalation ignored",
        "service not satisfactory",
        "representative rude",
    }
}


# ---------------------------------------------------
# Utility functions
# ---------------------------------------------------

def _clean_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())


def _match_category(text: str):

    text = _clean_text(text)

    scores = {}
    reason_codes = []

    for category, phrases in CATEGORY_PHRASES.items():

        score = 0

        for phrase in phrases:
            if phrase in text:
                score += 2
                reason_codes.append(
                    phrase.replace(" ", "_")
                )

        scores[category] = score

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    if best_score == 0:
        return DEFAULT_CATEGORY, 0.45, []

    confidence = min(
        0.90,
        0.50 + (best_score * 0.05)
    )

    return (
        best_category,
        round(confidence, 2),
        sorted(set(reason_codes))
    )


# ---------------------------------------------------
# CFPB field mapper
# ---------------------------------------------------

def _map_cfpb_field(field_value: str):

    text = _clean_text(field_value)

    best_category = DEFAULT_CATEGORY
    best_score = 0

    for category, phrases in CATEGORY_PHRASES.items():

        hits = 0

        for phrase in phrases:

            words = phrase.split()

            if any(
                word in text
                for word in words
            ):
                hits += 1

        if hits > best_score:
            best_score = hits
            best_category = category

    if best_score >= 3:
        confidence = 0.85
    elif best_score > 0:
        confidence = 0.70
    else:
        confidence = 0.45

    return best_category, confidence


# ---------------------------------------------------
# Main classifier
# ---------------------------------------------------

def classify_category(
    text: str,
    product: str | None = None,
    issue: str | None = None,
    bedrock_category: str | None = None
) -> tuple[str, float, list[str], bool]:

    reason_codes = []

    # -------------------------------
    # CFPB issue has higher priority
    # -------------------------------

    if issue:
        category, confidence = _map_cfpb_field(issue)
        reason_codes.append("cfpb_issue_mapping")

    elif product:
        category, confidence = _map_cfpb_field(product)
        reason_codes.append("cfpb_product_mapping")

    else:
        category, confidence, reasons = (
            _match_category(text)
        )
        reason_codes.extend(reasons)

    # -------------------------------
    # Bedrock disagreement
    # -------------------------------

    conflict = False

    if bedrock_category:

        if (
            category.strip().lower()
            != bedrock_category.strip().lower()
        ):
            conflict = True
            reason_codes.append(
                "category_conflict"
            )

    return (
        category,
        confidence,
        sorted(set(reason_codes)),
        conflict
    )


# ---------------------------------------------------
# Tests
# ---------------------------------------------------

if __name__ == "__main__":

    tests = [

        # 1 Fraud text
        {
            "text":
            "Unauthorized transaction and fraud detected on my account",
        },

        # 2 CFPB issue mapping
        {
            "text":
            "random complaint",
            "issue":
            "Incorrect information on your credit report"
        },

        # 3 CFPB product mapping
        {
            "text":
            "random complaint",
            "product":
            "Credit card services"
        },

        # 4 Bedrock disagreement
        {
            "text":
            "My account frozen and account locked",
            "bedrock_category":
            "Fraud or unauthorized activity"
        },

        # 5 Bedrock agreement
        {
            "text":
            "Unauthorized transaction and account hacked",
            "bedrock_category":
            "Fraud or unauthorized activity"
        },

        # 6 Ambiguous
        {
            "text":
            "I submitted a complaint yesterday"
        }

    ]

    for i, test in enumerate(
        tests,
        start=1
    ):

        result = classify_category(
            text=test.get("text", ""),
            product=test.get("product"),
            issue=test.get("issue"),
            bedrock_category=test.get(
                "bedrock_category"
            )
        )

        print(f"\nTest {i}")
        print("-" * 60)
        print("Input:", test)
        print("Output:", result)
