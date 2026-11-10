from __future__ import annotations

import re
from typing import Sequence

from core.contracts import ParsedDocument
from .models import Answer, Citation


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def verify_citations(document: ParsedDocument, citations: Sequence[Citation]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    pages = {page.number: page for page in document.pages}
    for citation in citations:
        page = pages.get(citation.page_num)
        if page is None:
            warnings.append(f"Citation references missing page {citation.page_num}.")
        elif _normalize(citation.evidence_text) not in _normalize(page.text):
            warnings.append(f"Evidence for page {citation.page_num} is not present in source text.")
    return not warnings, warnings


def validate_answer(document: ParsedDocument, answer: Answer) -> tuple[bool, list[str]]:
    if not answer.citations:
        return False, ["No page citations were provided for the answer."]
    return verify_citations(document, answer.citations)
