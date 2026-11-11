from __future__ import annotations

import base64
from pathlib import Path

import streamlit.components.v1 as components

from .protocol import parse_event

_component = components.declare_component(
    "qa_pdf_reader", path=str(Path(__file__).with_name("frontend"))
)


def render_reader(
    document,
    *,
    ask_enabled: bool,
    pdf_bytes: bytes | None = None,
    session_state=None,
    goto=None,
    highlights=None,
    key="qa_reader",
):
    sent_key = "qa_reader_sent_doc_id"
    payload = None
    if pdf_bytes is not None:
        if len(pdf_bytes) > 30 * 1024 * 1024:
            raise ValueError("PDF reader hiện giới hạn 30 MB.")
        if session_state is None:
            raise ValueError("session_state is required for PDF reader transport")
        if session_state.get(sent_key) != document.doc_id:
            payload = base64.b64encode(pdf_bytes).decode("ascii")
            session_state[sent_key] = document.doc_id
    value = _component(
        doc_id=document.doc_id,
        pages=[{"number": p.number, "text": p.text} for p in document.pages],
        filename=document.filename,
        pdf_b64=payload,
        ask_enabled=ask_enabled,
        goto=goto,
        highlights=highlights or [],
        key=key,
        default=None,
        height=680,
    )
    if not value:
        return None
    event = parse_event(value, len(document.pages))
    if event is None:
        return None
    if event.type == "need_pdf" and event.payload.get("doc_id") != document.doc_id:
        return None
    if event.type == "open_thread" and session_state is not None:
        if event.payload.get("thread_id") not in session_state.get("qa_threads", {}):
            return None
    if session_state is not None:
        seen = session_state.setdefault("qa_seen_events", [])
        if event.event_id in seen:
            return None
        seen.append(event.event_id)
        del seen[:-500]
    if event.type == "need_pdf" and session_state is not None:
        session_state.pop(sent_key, None)
    return event
