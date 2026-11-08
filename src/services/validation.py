from __future__ import annotations

from typing import List

from models.answer import Answer
from models.document import ParsedDocument


def validate_question(question: str) -> bool:
    return bool(question and question.strip())


def validate_parsed_document(document: ParsedDocument) -> List[str]:
    warnings: List[str] = []
    if not document.doc_id:
        warnings.append("Document id is missing.")
    if not document.file_path:
        warnings.append("Document path is missing.")
    if not document.pages:
        warnings.append("Document contains no parsed pages.")
    for page in document.pages:
        if page.page_num < 1:
            warnings.append(f"Invalid page number {page.page_num}.")
    return warnings


def validate_answer(answer: Answer) -> List[str]:
    warnings: List[str] = []
    if not answer.answer_id:
        warnings.append("Answer id is missing.")
    if not answer.text:
        warnings.append("Answer text is missing.")
    if answer.status not in {"draft", "verified", "rejected"}:
        warnings.append(f"Unsupported status: {answer.status}")
    return warnings
