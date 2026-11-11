from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from .citation import Citation


class RejectionReason(str, Enum):
    NO_CITATION = "NO_CITATION"
    CITATION_NOT_FOUND = "CITATION_NOT_FOUND"
    CITATION_OUTSIDE_CONTEXT = "CITATION_OUTSIDE_CONTEXT"
    WEAK_SUPPORT = "WEAK_SUPPORT"
    EMPTY_PAGE = "EMPTY_PAGE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    INVALID_INPUT = "INVALID_INPUT"

    def __str__(self) -> str:
        return self.value


@dataclass
class Answer:
    answer_id: str
    doc_id: str
    question_id: str
    text: str
    citations: list[Citation] = field(default_factory=list)
    status: str = "draft"
    source: Literal["llm", "cache", "local_fallback"] = "llm"
    model_used: str | None = None
    rejection_reason: RejectionReason | str | None = None
    warnings: list[str] = field(default_factory=list)
    can_answer: bool = True
    background_note: str = ""
    selection_verified: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.rejection_reason, str):
            try:
                self.rejection_reason = RejectionReason(self.rejection_reason)
            except ValueError:
                pass  # retain unknown values when reading older/future serialized data

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_id": self.answer_id,
            "doc_id": self.doc_id,
            "question_id": self.question_id,
            "text": self.text,
            "citations": [
                {
                    "page_num": c.page_num,
                    "evidence_text": c.evidence_text,
                    "confidence": c.confidence,
                }
                for c in self.citations
            ],
            "status": self.status,
            "source": self.source,
            "model_used": self.model_used,
            "rejection_reason": str(self.rejection_reason)
            if self.rejection_reason
            else None,
            "warnings": list(self.warnings),
            "can_answer": self.can_answer,
            "background_note": self.background_note,
            "selection_verified": self.selection_verified,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Answer:
        return cls(
            answer_id=data["answer_id"],
            doc_id=data["doc_id"],
            question_id=data["question_id"],
            text=data["text"],
            citations=[Citation(**item) for item in data.get("citations", [])],
            status=data.get("status", "draft"),
            source=data.get("source", "llm"),
            model_used=data.get("model_used"),
            rejection_reason=data.get("rejection_reason"),
            warnings=data.get("warnings", []),
            can_answer=data.get("can_answer", True),
            background_note=data.get("background_note", ""),
            selection_verified=data.get("selection_verified", True),
        )
