from __future__ import annotations

from pathlib import Path
from typing import Optional

from models.document import Page, ParsedDocument

try:
    import fitz
except ImportError:  # pragma: no cover - optional dependency in some environments
    fitz = None


def parse_document(file_path: str, doc_id: str, source_email_id: Optional[str] = None) -> ParsedDocument:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document does not exist: {file_path}")

    if path.suffix.lower() == ".pdf" and fitz is not None:
        pages = []
        document = fitz.open(path)
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            pages.append(Page(page_num=index, text=text))
        document.close()
        return ParsedDocument(doc_id=doc_id, file_path=str(path), pages=pages, source_email_id=source_email_id)

    content = path.read_text(encoding="utf-8", errors="ignore")
    return ParsedDocument(
        doc_id=doc_id,
        file_path=str(path),
        pages=[Page(page_num=1, text=content.strip() or "No readable text was found.")],
        source_email_id=source_email_id,
    )
