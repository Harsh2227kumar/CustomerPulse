from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RegulatoryChunk:
    chunk_index: int
    chunk_text: str
    section_reference: str | None
    page_start: int | None
    page_end: int | None
    keywords: list[str]


def chunk_markdown_pages(
    pages: list[str],
    *,
    max_words: int = 650,
    overlap_words: int = 80,
) -> list[RegulatoryChunk]:
    if max_words < 100:
        raise ValueError("max_words must be at least 100")
    if overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("overlap_words must be non-negative and smaller than max_words")

    units: list[tuple[int, str]] = []
    for page_number, page in enumerate(pages, start=1):
        for block in _split_blocks(page):
            units.append((page_number, block))

    chunks: list[RegulatoryChunk] = []
    current: list[tuple[int, str]] = []
    current_words = 0
    for page_number, block in units:
        block_words = _word_count(block)
        if current and current_words + block_words > max_words:
            chunks.append(_build_chunk(len(chunks), current))
            current = _overlap_tail(current, overlap_words)
            current_words = sum(_word_count(text) for _, text in current)
        current.append((page_number, block))
        current_words += block_words
    if current:
        chunks.append(_build_chunk(len(chunks), current))
    return chunks


def _split_blocks(markdown: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", markdown) if block.strip()]
    return blocks or ([markdown.strip()] if markdown.strip() else [])


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _build_chunk(index: int, blocks: list[tuple[int, str]]) -> RegulatoryChunk:
    text = "\n\n".join(block for _, block in blocks).strip()
    pages = [page for page, _ in blocks]
    return RegulatoryChunk(
        chunk_index=index,
        chunk_text=text,
        section_reference=_first_heading(text),
        page_start=min(pages) if pages else None,
        page_end=max(pages) if pages else None,
        keywords=_keywords(text),
    )


def _overlap_tail(blocks: list[tuple[int, str]], overlap_words: int) -> list[tuple[int, str]]:
    if overlap_words == 0:
        return []
    kept: list[tuple[int, str]] = []
    total = 0
    for page, block in reversed(blocks):
        kept.append((page, block))
        total += _word_count(block)
        if total >= overlap_words:
            break
    return list(reversed(kept))


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned.startswith("#"):
            return cleaned.lstrip("#").strip()[:255] or None
        if re.match(r"^(section|chapter|part)\s+[0-9A-Za-z.,-]+", cleaned, flags=re.IGNORECASE):
            return cleaned[:255]
    return None


def _keywords(text: str) -> list[str]:
    candidates = {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z-]{3,}", text)}
    stop_words = {"that", "this", "with", "from", "shall", "must", "have", "been", "were", "where", "there"}
    return sorted(word for word in candidates if word not in stop_words)[:20]
