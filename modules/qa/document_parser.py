from __future__ import annotations

from pathlib import Path

from core.contracts import Page, ParsedDocument

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None


def parse_document(file_path: str, doc_id: str, source_email_id: str | None = None) -> ParsedDocument:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Document does not exist: {file_path}")

    if path.suffix.lower() == ".pdf":
        if fitz is None:
            raise RuntimeError("PyMuPDF is required to read PDF documents.")
        pages: list[Page] = []
        with fitz.open(path) as document:
            for index, page in enumerate(document, start=1):
                pages.append(Page(number=index, text=page.get_text("text").strip()))
    else:
        pages = [Page(number=1, text=path.read_text(encoding="utf-8", errors="replace").strip())]
    return ParsedDocument(doc_id=doc_id, filename=path.name, pages=pages)
