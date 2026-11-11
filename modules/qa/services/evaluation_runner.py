from __future__ import annotations

from typing import Any, Sequence

from core.contracts import ParsedDocument
from core.llm_client import LLMClient

from ..citation_verifier import verify_citations
from ..qa_service import QAService


DEFAULT_BENCHMARK = [
    "What is the main topic of the document?",
    "What is the document's primary claim?",
    "Which page provides supporting evidence?",
    "What conclusion is supported by the source?",
    "What conditions are described in the document?",
]


def run_evaluation(
    document: ParsedDocument,
    questions: Sequence[str] | None = None,
    reference_material: bool = True,
    *,
    llm_client: LLMClient | None = None,
) -> dict[str, Any]:
    """Evaluate citation validity for caller-supplied questions using the shared client."""
    service = QAService(llm_client)
    entries: list[dict[str, Any]] = []
    for question in questions or DEFAULT_BENCHMARK:
        try:
            answer = service.ask_question(
                document, question, reference_material=reference_material
            )
            valid, warnings = verify_citations(document, answer.citations)
            entries.append({
                "question": question,
                "answer_status": answer.status,
                "citation_valid": valid,
                "warnings": warnings,
            })
        except ValueError as exc:
            entries.append({
                "question": question,
                "answer_status": "rejected",
                "citation_valid": False,
                "warnings": [str(exc)],
            })
    valid_count = sum(bool(item["citation_valid"]) for item in entries)
    return {
        "reference_material": reference_material,
        "total_questions": len(entries),
        "valid_citations": valid_count,
        "citation_accuracy": round(valid_count / len(entries), 2) if entries else 0.0,
        "entries": entries,
    }
