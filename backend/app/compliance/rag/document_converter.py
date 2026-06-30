from dataclasses import dataclass
from pathlib import Path


class RegulatoryDocumentConversionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConvertedDocument:
    markdown: str
    conversion_tool: str
    warnings: list[str]


def convert_document_to_markdown(file_path: str | Path) -> ConvertedDocument:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".md":
        return ConvertedDocument(
            markdown=path.read_text(encoding="utf-8"),
            conversion_tool="native-markdown",
            warnings=[],
        )
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8")
        return ConvertedDocument(
            markdown=_plain_text_to_markdown(text),
            conversion_tool="plain-text",
            warnings=[],
        )
    if suffix == ".pdf":
        return convert_pdf_to_markdown(path)
    if suffix in {".doc", ".docx"}:
        return convert_docx_to_markdown(path)
    raise RegulatoryDocumentConversionError(f"Unsupported regulatory document type: {suffix}")


def split_markdown_pages(markdown: str) -> list[str]:
    marker = "<!-- page:"
    if marker not in markdown:
        cleaned = markdown.strip()
        return [cleaned] if cleaned else []

    pages: list[str] = []
    current: list[str] = []
    for line in markdown.splitlines():
        if line.strip().startswith(marker) and current:
            page = "\n".join(current).strip()
            if page:
                pages.append(page)
            current = [line]
        else:
            current.append(line)
    page = "\n".join(current).strip()
    if page:
        pages.append(page)
    return pages


def clean_extracted_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines() if line.strip())


def _plain_text_to_markdown(text: str) -> str:
    return clean_extracted_text(text)


def convert_pdf_to_markdown(file_path: str | Path) -> ConvertedDocument:
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RegulatoryDocumentConversionError(
            "PDF conversion requires pymupdf4llm; install backend requirements."
        ) from exc
    markdown = pymupdf4llm.to_markdown(str(file_path))
    return ConvertedDocument(
        markdown=markdown,
        conversion_tool="pymupdf4llm",
        warnings=[],
    )


def convert_docx_to_markdown(file_path: str | Path) -> ConvertedDocument:
    try:
        import mammoth
    except ImportError as exc:
        raise RegulatoryDocumentConversionError(
            "DOC/DOC/DOCX conversion requires mammoth; install backend requirements."
        ) from exc
    with Path(file_path).open("rb") as docx_file:
        result = mammoth.convert_to_markdown(docx_file)
    return ConvertedDocument(
        markdown=result.value,
        conversion_tool="mammoth",
        warnings=[message.message for message in result.messages],
    )
