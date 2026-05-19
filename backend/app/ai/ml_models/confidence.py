def combine_confidence(*values: float) -> float:
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return 0.0
    return round(sum(valid_values) / len(valid_values), 3)
