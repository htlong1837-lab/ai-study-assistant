from __future__ import annotations

from document_parser import parse_document
from models.document import DocumentInput, ParsedDocument


def load_document(document_input: DocumentInput) -> ParsedDocument:
    """Load a secure document through the parser and preserve the source metadata."""
    return parse_document(
        file_path=document_input.file_path,
        doc_id=document_input.doc_id,
        source_email_id=document_input.source_email_id,
    )
