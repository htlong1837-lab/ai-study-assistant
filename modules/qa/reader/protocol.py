from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass


@dataclass
class ReaderEvent:
    event_id: str
    type: str
    payload: dict


def parse_event(raw, n_pages: int):
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("event_id"), str)
        or not raw["event_id"].strip()
        or len(raw["event_id"]) > 80
        or type(n_pages) is not int
        or n_pages < 1
    ):
        return None
    kind = raw.get("type")
    if not isinstance(kind, str):
        return None
    if kind == "ask":
        page, action = raw.get("page"), raw.get("action")
        text = raw.get("selected_text", "")
        if (
            type(page) is not int
            or not 1 <= page <= n_pages
            or not isinstance(action, str)
            or action not in {"explain", "simplify", "translate", "define", "custom"}
        ):
            return None
        if not isinstance(text, str) or len(text) > 4000 or not text.strip():
            return None
        question = raw.get("question", "")
        if not isinstance(question, str) or len(question) > 1000:
            return None
        if action == "custom" and not question.strip():
            return None
        question = re.sub(r"[\x00-\x1f\x7f]", " ", question).strip()
        rects = raw.get("rects", [])
        if not isinstance(rects, list) or len(rects) > 50:
            return None
        for rect in rects:
            if (
                not isinstance(rect, dict)
                or type(rect.get("page")) is not int
                or not 1 <= rect["page"] <= n_pages
            ):
                return None
            if any(
                type(rect.get(k)) not in (int, float) or not 0 <= rect[k] <= 1
                for k in ("x", "y", "w", "h")
            ):
                return None
            if rect["x"] + rect["w"] > 1 or rect["y"] + rect["h"] > 1:
                return None
        return ReaderEvent(
            raw["event_id"],
            kind,
            {
                **raw,
                "question": question,
                "selected_text": re.sub(
                    r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text
                ).strip(),
            },
        )
    if kind == "page_changed":
        page = raw.get("page")
        if type(page) is not int or not 1 <= page <= n_pages:
            return None
        return ReaderEvent(raw["event_id"], kind, dict(raw))
    if kind == "need_pdf":
        if not isinstance(raw.get("doc_id"), str) or not raw["doc_id"].strip():
            return None
        return ReaderEvent(raw["event_id"], kind, dict(raw))
    if kind == "open_thread":
        if not isinstance(raw.get("thread_id"), str) or not raw["thread_id"].strip():
            return None
        return ReaderEvent(raw["event_id"], kind, dict(raw))
    return None


class EventDeduper:
    def __init__(self, max_events: int = 500):
        self.ids = deque(maxlen=max_events)

    def accept(self, event_id: str) -> bool:
        if event_id in self.ids:
            return False
        self.ids.append(event_id)
        return True
