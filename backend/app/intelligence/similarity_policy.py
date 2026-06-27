RETRIEVAL_THRESHOLD = 0.80
SAFE_REUSE_THRESHOLD = 0.92
REASON_CODE_OVERLAP_SAFE_MIN = 0.60
REASON_CODE_OVERLAP_REVIEW_MIN = 0.30
EVIDENCE_STRENGTH_SAFE_MIN = 0.70
EVIDENCE_STRENGTH_REVIEW_MIN = 0.40

SIMILARITY_POLICY_SOURCE = {
    "method": "tfidf_cosine_plus_hybrid_validation",
    "sample_rows": 64931,
    "candidate_pairs": 159766,
    "source_file": "collab/customerpulse_profile/similarity_threshold_summary.json",
    "backend_rule": (
        "Similarity finds candidates. Validation decides reuse. "
        "Safe reuse requires similarity, category/product/issue family, "
        "reason-code overlap, evidence strength, and risk checks to agree."
    ),
}

