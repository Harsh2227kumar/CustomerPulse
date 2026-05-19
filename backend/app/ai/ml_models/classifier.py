DEFAULT_CATEGORY = "General complaint"


CATEGORY_TERMS = {
    "Billing or fees": {"fee", "fees", "charged", "charge", "overdraft", "billing"},
    "Fraud or unauthorized activity": {"fraud", "unauthorized", "identity", "scam", "stolen"},
    "Account servicing": {"account", "closed", "servicing", "statement", "balance"},
    "Credit reporting": {"credit", "report", "score", "bureau", "inaccurate"},
    "Loan or mortgage issue": {"loan", "mortgage", "foreclosure", "payment", "interest"},
}


def classify_category(text: str, product: str | None = None, issue: str | None = None) -> tuple[str, float]:
    if issue:
        return issue, 0.8
    if product:
        return product, 0.7
    words = {word.strip(".,!?;:()[]{}\"'").lower() for word in text.split()}
    best_category = DEFAULT_CATEGORY
    best_hits = 0
    for category, terms in CATEGORY_TERMS.items():
        hits = len(words & terms)
        if hits > best_hits:
            best_category = category
            best_hits = hits
    confidence = min(0.85, 0.5 + best_hits * 0.1) if best_hits else 0.45
    return best_category, confidence
