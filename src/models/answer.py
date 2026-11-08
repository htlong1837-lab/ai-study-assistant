from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal

from .citation import Citation


@dataclass
class Answer:
    answer_id: str
    doc_id: str
    question_id: str
    text: str
    citations: List[Citation] = field(default_factory=list)
    status: str = "draft"
    # Task 0.5: source label for transparency
    source: Literal["llm", "cache", "local_fallback"] = "llm"
    model_used: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer_id": self.answer_id,
            "doc_id": self.doc_id,
            "question_id": self.question_id,
            "text": self.text,
            "citations": [
                {
                    "page_num": citation.page_num,
                    "evidence_text": citation.evidence_text,
                    "confidence": citation.confidence,
                }
                for citation in self.citations
            ],
            "status": self.status,
            "source": self.source,
            "model_used": self.model_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Answer":
        return cls(
            answer_id=data["answer_id"],
            doc_id=data["doc_id"],
            question_id=data["question_id"],
            text=data["text"],
            citations=[
                Citation(
                    page_num=item["page_num"],
                    evidence_text=item["evidence_text"],
                    confidence=item.get("confidence", 1.0),
                )
                for item in data.get("citations", [])
            ],
            status=data.get("status", "draft"),
            # Backwards-compatible defaults for older serialised payloads
            source=data.get("source", "llm"),
            model_used=data.get("model_used"),
        )
