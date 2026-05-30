# backend/app/ai/ml_models/confidence.py

def combine_confidence(
    local_confidence: float,
    bedrock_confidence: float | None = None,
    *extra_signals: float
) -> tuple[float, bool, str]:

    # ---------------------------------------
    # Local only case
    # ---------------------------------------

    if bedrock_confidence is None:
        return (
            round(local_confidence, 3),
            False,
            "local_only"
        )

    conflict_detected = False

    # ---------------------------------------
    # Conflict detection
    # ---------------------------------------

    confidence_gap = abs(
        local_confidence
        - bedrock_confidence
    )

    if confidence_gap > 0.25:

        conflict_detected = True

        final_confidence = min(
            local_confidence,
            bedrock_confidence
        )

        confidence_note = (
            "conflict_detected_using_lower"
        )

    # ---------------------------------------
    # Weighted combination
    # ---------------------------------------

    else:

        final_confidence = (
            (local_confidence * 0.4)
            + (bedrock_confidence * 0.6)
        )

        confidence_note = (
            "weighted_average"
        )

    # ---------------------------------------
    # Extra signal blending
    # ---------------------------------------

    valid_extra = [
        value
        for value in extra_signals
        if value is not None
    ]

    if valid_extra:

        extra_avg = (
            sum(valid_extra)
            / len(valid_extra)
        )

        final_confidence = (
            (final_confidence * 0.8)
            + (extra_avg * 0.2)
        )

        confidence_note += (
            "_with_extra_blend"
        )

    # ---------------------------------------
    # Final safety
    # ---------------------------------------

    final_confidence = max(
        0.0,
        min(
            1.0,
            final_confidence
        )
    )

    return (
        round(
            final_confidence,
            3
        ),
        conflict_detected,
        confidence_note
    )


# ------------------------------------------------------
# Tests
# ------------------------------------------------------

if __name__ == "__main__":

    tests = [

        # 1 Local only
        (
            "Local only",
            combine_confidence(
                0.82
            )
        ),

        # 2 Agreement
        (
            "Agreement",
            combine_confidence(
                0.80,
                0.75
            )
        ),

        # 3 Local high / Bedrock low
        (
            "Conflict high-low",
            combine_confidence(
                0.90,
                0.30
            )
        ),

        # 4 Local low / Bedrock high
        (
            "Conflict low-high",
            combine_confidence(
                0.25,
                0.70
            )
        ),

        # 5 Extra signals
        (
            "Extra signals",
            combine_confidence(
                0.75,
                0.80,
                0.70,
                0.85,
                0.65
            )
        )

    ]

    for name, result in tests:

        print("\n" + "=" * 50)
        print(name)
        print("=" * 50)

        print(
            "Output:",
            result
        )
