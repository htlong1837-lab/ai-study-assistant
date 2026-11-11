from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal

from .citation import Citation


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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer_id": self.answer_id,
            "doc_id": self.doc_id,
            "question_id": self.question_id,
            "text": self.text,
            "citations": [
                {"page_num": c.page_num, "evidence_text": c.evidence_text,
                 "confidence": c.confidence}
                for c in self.citations
            ],
            "status": self.status,
            "source": self.source,
            "model_used": self.model_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Answer":
        return cls(
            answer_id=data["answer_id"], doc_id=data["doc_id"],
            question_id=data["question_id"], text=data["text"],
            citations=[Citation(**item) for item in data.get("citations", [])],
            status=data.get("status", "draft"), source=data.get("source", "llm"),
            model_used=data.get("model_used"),
        )
