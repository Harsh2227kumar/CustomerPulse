# backend/app/ai/ml_models/classifier.py

import re

DEFAULT_CATEGORY = "General complaint"

STANDARD_CATEGORIES = [
    "Billing or fees",
    "Fraud or unauthorized activity",
    "Account servicing",
    "Credit reporting",
    "Loan or mortgage issue",
    "Debt collection issue",
    "Account issue",
    "Card services",
    "Payment or transfer issue",
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

    "Debt collection issue": {
        "debt collection",
        "debt collector",
        "collect debt",
        "debt not owed",
        "written notification about debt",
        "false statements",
        "communication tactics",
        "validation of debt",
        "fdcpa",
        "collection notice",
        "debt validation",
        "disclosure verification",
        "threatened to take",
        "debt collector contacted",
        "attempts to collect",
        "owed",
    },

    "Account issue": {
        "checking account",
        "savings account",
        "bank account",
        "managing an account",
        "opening an account",
        "closing an account",
        "account opening",
        "account closing",
        "deposits and withdrawals",
        "account hold",
        "joint account",
        "checking",
        "savings",
        "deposit account",
        "funds being low",
        "overdraft",
    },

    "Payment or transfer issue": {
        "money transfer",
        "virtual currency",
        "money service",
        "mobile wallet",
        "digital wallet",
        "cash app",
        "zelle",
        "wire transfer",
        "electronic transfer",
        "unauthorized transactions",
        "transaction problem",
        "money was not available",
        "trouble accessing funds",
        "payment app",
        "fund transfer failed",
        "transfer failed",
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


PRODUCT_CATEGORY_OVERRIDES = (
    (("debt collection",), "Debt collection issue", "cfpb_product_debt_collection"),
    (("checking or savings", "bank account or service"), "Account issue", "cfpb_product_account"),
    (("money transfer", "virtual currency", "money service"), "Payment or transfer issue", "cfpb_product_payment_transfer"),
    (("mortgage", "student loan", "vehicle loan", "consumer loan", "payday loan", "personal loan"), "Loan or mortgage issue", "cfpb_product_loan_mortgage"),
    (("credit card", "prepaid card"), "Card services", "cfpb_product_card"),
    (("credit reporting", "consumer reports", "credit repair"), "Credit reporting", "cfpb_product_credit_reporting"),
)

ISSUE_CATEGORY_OVERRIDES = (
    (("attempts to collect", "written notification about debt", "false statements", "communication tactics", "verification of debt", "debt not owed", "threatened to take"), "Debt collection issue", "cfpb_issue_debt_collection"),
    (("managing an account", "opening an account", "closing an account", "deposits and withdrawals", "funds being low", "charging your account"), "Account issue", "cfpb_issue_account"),
    (("fraud or scam", "other transaction problem", "unauthorized transactions", "money was not available", "mobile wallet", "money transfer"), "Payment or transfer issue", "cfpb_issue_payment_transfer"),
    (("trouble during payment process", "struggling to pay mortgage", "loan servicing", "dealing with your lender", "managing the loan", "getting a loan", "repossession"), "Loan or mortgage issue", "cfpb_issue_loan_mortgage"),
    (("getting a credit card", "problem when making payments", "purchase shown on your statement", "fees or interest", "trouble using your card", "closing your account"), "Card services", "cfpb_issue_card"),
    (("incorrect information on your report", "improper use of your report", "investigation into an existing problem", "unable to get your credit report", "fraud alerts or security freezes"), "Credit reporting", "cfpb_issue_credit_reporting"),
)


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

def _override_match(field_value: str | None, overrides):
    text = _clean_text(field_value or "")
    if not text:
        return None
    for phrases, category, reason_code in overrides:
        if any(phrase in text for phrase in phrases):
            return category, 0.88, reason_code
    return None


def _map_cfpb_context(product: str | None, issue: str | None):
    issue_match = _override_match(issue, ISSUE_CATEGORY_OVERRIDES)
    product_match = _override_match(product, PRODUCT_CATEGORY_OVERRIDES)
    if product_match and issue_match:
        product_category, _, product_reason = product_match
        issue_category, _, issue_reason = issue_match
        if product_category == issue_category:
            return product_category, 0.92, [product_reason, issue_reason]
        if product_category in {"Debt collection issue", "Account issue", "Payment or transfer issue", "Loan or mortgage issue"}:
            return product_category, 0.86, [product_reason, "product_override_prevents_credit_card_drift"]
        return issue_category, 0.84, [issue_reason]
    if product_match:
        category, confidence, reason = product_match
        return category, confidence, [reason]
    if issue_match:
        category, confidence, reason = issue_match
        return category, confidence, [reason]
    field_value = issue or product or ""
    return (*_map_cfpb_field(field_value), ["cfpb_field_mapping"])


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

    if issue or product:
        category, confidence, mapping_reasons = _map_cfpb_context(product, issue)
        reason_codes.extend(mapping_reasons)

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
