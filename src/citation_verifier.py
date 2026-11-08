from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

from models.answer import Answer
from models.citation import Citation
from models.document import ParsedDocument


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def verify_citations(document: ParsedDocument, citations: Sequence[Citation]) -> Tuple[bool, List[str]]:
    warnings: List[str] = []
    for citation in citations:
        page = document.page_by_number(citation.page_num)
        if page is None:
            warnings.append(f"Citation references page {citation.page_num}, which does not exist in the source document.")
            continue
        normalized = _normalize(citation.evidence_text)
        if not normalized:
            warnings.append(f"Citation for page {citation.page_num} is missing evidence text.")
            continue
        page_text = _normalize(page.text)
        if normalized not in page_text:
            warnings.append(
                f"Evidence for page {citation.page_num} does not appear in the extracted source text: {citation.evidence_text}"
            )
    return len(warnings) == 0, warnings


def validate_answer(document: ParsedDocument, answer: Answer) -> Tuple[bool, List[str]]:
    if not answer.citations:
        return False, ["No page citations were provided for the answer."]
    return verify_citations(document, answer.citations)
