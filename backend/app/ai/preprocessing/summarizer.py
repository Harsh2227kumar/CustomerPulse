def compress_for_prompt(text: str, max_words: int = 900) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    head_count = int(max_words * 0.7)
    tail_count = max_words - head_count
    head = words[:head_count]
    tail = words[-tail_count:]
    return " ".join(head + ["[...middle omitted for token control...]"] + tail)
