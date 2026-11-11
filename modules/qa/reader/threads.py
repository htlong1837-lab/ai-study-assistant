from __future__ import annotations

from collections.abc import Mapping

from ..models import PassageThread
from ..models.thread import passage_thread_id


def make_thread_id(doc_id: str, page_num: int, selected_text: str) -> str:
    """Return a stable ID for the same normalized passage in one document."""
    return passage_thread_id(doc_id, page_num, selected_text)


class ThreadStore:
    """Small session-scoped store; pass the owning session's dict to the constructor."""

    def __init__(self, threads: dict[str, PassageThread] | None = None):
        self.threads = threads if threads is not None else {}

    def get_or_create(
        self,
        doc_id: str,
        page_num: int,
        selected_text: str,
        rects: list[dict] | None = None,
    ) -> PassageThread:
        thread_id = make_thread_id(doc_id, page_num, selected_text)
        thread = self.threads.get(thread_id)
        if thread is None:
            thread = PassageThread(
                doc_id=doc_id,
                page_num=page_num,
                selected_text=selected_text,
                thread_id=thread_id,
                rects=list(rects or []),
            )
            self.threads[thread_id] = thread
        elif rects and not thread.rects:
            thread.rects = list(rects)
        return thread


def export_markdown(filename: str, threads: Mapping[str, PassageThread]) -> str:
    lines = [f"# {filename}", ""]
    for thread in threads.values():
        lines.extend([f"## Trang {thread.page_num}", f"> {thread.selected_text}", ""])
        for question, answer in zip(thread.questions, thread.answers):
            lines.extend([f"**Bạn:** {question}", "", f"**Trợ lý:** {answer.text}", ""])
            if answer.background_note:
                lines.extend(
                    ["**Kiến thức bổ sung của AI:**", answer.background_note, ""]
                )
            for citation in answer.citations:
                lines.append(
                    f"> Nguồn (trang {citation.page_num}): {citation.evidence_text}"
                )
            if answer.citations:
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"
