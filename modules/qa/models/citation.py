from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Citation:
    page_num: int
    evidence_text: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.page_num < 1:
            raise ValueError("page_num must be at least 1")
        if not self.evidence_text.strip():
            raise ValueError("evidence_text must not be empty")
