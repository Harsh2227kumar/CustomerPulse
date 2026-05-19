def cosine_similarity_score(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance))
