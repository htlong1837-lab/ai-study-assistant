from __future__ import annotations

from typing import Any, Dict, List, Sequence

from citation_verifier import verify_citations
from document_parser import parse_document
from models.citation import Citation
from models.document import ParsedDocument
from qa_service import QAService


DEFAULT_BENCHMARK = [
    "What is the main topic of the document?",
    "What is the document’s primary claim?",
    "Which page provides the supporting evidence?",
    "What conclusion can be drawn from the source content?",
    "What conditions are described in the document?",
] + [f"Benchmark question {index}" for index in range(6, 31)]


def _simple_questions() -> List[str]:
    return DEFAULT_BENCHMARK[:30]


def run_evaluation(document: ParsedDocument, questions: Sequence[str] | None = None, reference_material: bool = True) -> Dict[str, Any]:
    qa_service = QAService()
    entries: List[Dict[str, Any]] = []
    for question in questions or _simple_questions():
        try:
            answer = qa_service.ask_question(document, question, reference_material=reference_material)
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
    valid_count = sum(1 for entry in entries if entry["citation_valid"])
    return {
        "reference_material": reference_material,
        "total_questions": len(entries),
        "valid_citations": valid_count,
        "citation_accuracy": round(valid_count / len(entries), 2) if entries else 0.0,
        "entries": entries,
    }
