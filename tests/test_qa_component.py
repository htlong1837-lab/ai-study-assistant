import base64

import pytest

from core.contracts import Page, ParsedDocument
from modules.qa.reader import component


DOC = ParsedDocument(
    "doc-component", "x.pdf", [Page(1, "This is a readable sample document page.")]
)


def test_component_sends_pdf_once_per_document(monkeypatch):
    calls = []
    monkeypatch.setattr(
        component, "_component", lambda **kwargs: calls.append(kwargs) or None
    )
    state = {}
    component.render_reader(
        DOC, ask_enabled=True, pdf_bytes=b"%PDF-123", session_state=state
    )
    component.render_reader(
        DOC, ask_enabled=True, pdf_bytes=b"%PDF-123", session_state=state
    )
    assert calls[0]["pdf_b64"] == base64.b64encode(b"%PDF-123").decode("ascii")
    assert calls[1]["pdf_b64"] is None


def test_component_responds_to_reload_request(monkeypatch):
    monkeypatch.setattr(
        component,
        "_component",
        lambda **kwargs: {
            "event_id": "need-1",
            "type": "need_pdf",
            "doc_id": DOC.doc_id,
        },
    )
    state = {"qa_reader_sent_doc_id": DOC.doc_id}
    event = component.render_reader(
        DOC, ask_enabled=False, pdf_bytes=b"%PDF-123", session_state=state
    )
    assert event.type == "need_pdf"
    assert "qa_reader_sent_doc_id" not in state


def test_component_parses_ask_event_and_rejects_invalid_event(monkeypatch):
    monkeypatch.setattr(
        component,
        "_component",
        lambda **kwargs: {
            "event_id": "e1",
            "type": "ask",
            "action": "explain",
            "page": 1,
            "selected_text": "Alice",
        },
    )
    assert component.render_reader(DOC, ask_enabled=True).type == "ask"
    monkeypatch.setattr(
        component, "_component", lambda **kwargs: {"type": "ask", "page": 1}
    )
    assert component.render_reader(DOC, ask_enabled=True) is None


def test_component_deduplicates_events_in_session(monkeypatch):
    monkeypatch.setattr(
        component,
        "_component",
        lambda **kwargs: {
            "event_id": "same-event",
            "type": "ask",
            "action": "explain",
            "page": 1,
            "selected_text": "Alice",
        },
    )
    state = {}
    assert component.render_reader(DOC, ask_enabled=True, session_state=state)
    assert component.render_reader(DOC, ask_enabled=True, session_state=state) is None
    assert state["qa_seen_events"] == ["same-event"]


def test_component_enforces_pdf_size_cap():
    with pytest.raises(ValueError, match="30 MB"):
        component.render_reader(
            DOC,
            ask_enabled=False,
            pdf_bytes=b"x" * (30 * 1024 * 1024 + 1),
            session_state={},
        )


def test_component_transports_thread_highlights_and_rejects_stale_events(monkeypatch):
    calls = []
    monkeypatch.setattr(
        component,
        "_component",
        lambda **kwargs: (
            calls.append(kwargs)
            or {
                "event_id": "stale",
                "type": "need_pdf",
                "doc_id": "another-document",
            }
        ),
    )
    state = {"qa_reader_sent_doc_id": DOC.doc_id}
    highlights = [
        {
            "thread_id": "thread-1",
            "rects": [{"page": 1, "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1}],
        }
    ]
    assert (
        component.render_reader(
            DOC, ask_enabled=True, session_state=state, highlights=highlights
        )
        is None
    )
    assert calls[0]["highlights"] == highlights


def test_component_rejects_open_thread_not_in_session(monkeypatch):
    monkeypatch.setattr(
        component,
        "_component",
        lambda **kwargs: {
            "event_id": "open-missing",
            "type": "open_thread",
            "thread_id": "missing",
        },
    )
    assert component.render_reader(DOC, ask_enabled=True, session_state={}) is None
