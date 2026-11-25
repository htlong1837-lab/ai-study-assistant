"""Chuyển hội thoại theo đoạn văn (``PassageThread``) sang JSON và ngược lại, để giữ lại giữa các phiên."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .models.answer import Answer
from .models.thread import PassageThread


def thread_to_dict(t: PassageThread) -> dict[str, Any]:
    return {
        "doc_id": t.doc_id, "page_num": t.page_num, "selected_text": t.selected_text,
        "thread_id": t.thread_id, "created_at": t.created_at.isoformat(), "rects": list(t.rects),
        "answers": [a.to_dict() for a in t.answers], "history": [list(h) for h in t.history],
        "questions": list(t.questions), "selection_verified": t.selection_verified,
    }


def thread_from_dict(d: dict[str, Any]) -> PassageThread:
    t = PassageThread(doc_id=d["doc_id"], page_num=int(d["page_num"]), selected_text=d["selected_text"],
                      thread_id=d.get("thread_id", ""), rects=list(d.get("rects", [])),
                      answers=[Answer.from_dict(a) for a in d.get("answers", [])],
                      history=[tuple(h) for h in d.get("history", [])], questions=list(d.get("questions", [])),
                      selection_verified=bool(d.get("selection_verified", False)))
    try:
        t.created_at = datetime.fromisoformat(d["created_at"])
    except (KeyError, TypeError, ValueError):
        pass
    return t


def threads_to_json(threads: dict[str, PassageThread]) -> list[dict[str, Any]]:
    return [thread_to_dict(t) for t in threads.values()]


def threads_from_json(items: list[dict[str, Any]] | None) -> dict[str, PassageThread]:
    out = {}
    for item in items or []:
        try:
            t = thread_from_dict(item)
        except (KeyError, TypeError, ValueError):
            continue  # bỏ qua bản ghi hỏng, giữ phần còn lại
        out[t.thread_id] = t
    return out
