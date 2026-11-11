from __future__ import annotations

import re
from collections.abc import Sequence

from core.contracts import ParsedDocument

from .models import Answer, Citation
from .text_normalize import match_type, normalize


def _normalize(text: str) -> str:
    return normalize(text)


def verify_citations(
    document: ParsedDocument, citations: Sequence[Citation]
) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    pages = {page.number: page for page in document.pages}
    for citation in citations:
        page = pages.get(citation.page_num)
        if page is None:
            warnings.append(f"Citation references missing page {citation.page_num}.")
        elif match_type(citation.evidence_text, page.text) == "none":
            warnings.append(
                f"Evidence for page {citation.page_num} is not present in source text."
            )
    return not warnings, warnings


def validate_answer(document: ParsedDocument, answer: Answer) -> tuple[bool, list[str]]:
    if not answer.citations:
        return False, ["No page citations were provided for the answer."]
    return verify_citations(document, answer.citations)


def verify_answer_citations(pages_sent, answer: Answer):
    """Verify citations against exactly the page context passed to the model."""
    if not answer.can_answer:
        return True, []
    if not answer.citations:
        return False, ["NO_CITATION"]
    page_map = {p.number: p for p in pages_sent}
    warnings = []
    stop = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "của",
        "là",
        "và",
        "các",
        "những",
        "trong",
        "một",
        "được",
        "cho",
        "từ",
    }
    for citation in answer.citations:
        page = page_map.get(citation.page_num)
        if page is None:
            warnings.append("CITATION_OUTSIDE_CONTEXT")
            continue
        if match_type(citation.evidence_text, page.text) == "none":
            warnings.append("CITATION_NOT_FOUND")
            continue
        evidence_terms = (
            set(re.findall(r"\w+", normalize(citation.evidence_text))) - stop
        )
        answer_terms = set(re.findall(r"\w+", normalize(answer.text))) - stop
        overlap = len(evidence_terms & answer_terms) / max(1, len(answer_terms))
        if answer_terms and overlap < 0.08:
            warnings.append("WEAK_SUPPORT")
    return not warnings, warnings
