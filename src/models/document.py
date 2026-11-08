from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DocumentInput:
    doc_id: str
    file_path: str
    source_email_id: Optional[str] = None
    document_type: str = "pdf"


@dataclass
class Page:
    page_num: int
    text: str
    source_hash: Optional[str] = None

    def __post_init__(self) -> None:
        if self.page_num < 1:
            raise ValueError("page_num must be at least 1")


@dataclass
class ParsedDocument:
    doc_id: str
    file_path: str
    pages: List[Page] = field(default_factory=list)
    source_email_id: Optional[str] = None

    def page_by_number(self, page_num: int) -> Optional[Page]:
        for page in self.pages:
            if page.page_num == page_num:
                return page
        return None

    def page_texts(self) -> List[dict]:
        return [{"page_num": page.page_num, "text": page.text} for page in self.pages]
