from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .answer import Answer
from ..text_normalize import normalize


def passage_thread_id(doc_id: str, page_num: int, selected_text: str) -> str:
    normalized = normalize(selected_text)
    raw = f"{doc_id}|{page_num}|{normalized}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


@dataclass
class PassageThread:
    doc_id: str
    page_num: int
    selected_text: str
    thread_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rects: list[dict] = field(default_factory=list)
    answers: list[Answer] = field(default_factory=list)
    history: list[tuple[str, str]] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    selection_verified: bool = False

    def __post_init__(self) -> None:
        if not self.thread_id:
            self.thread_id = passage_thread_id(
                self.doc_id, self.page_num, self.selected_text
            )
