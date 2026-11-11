import unicodedata

import pytest

from core.contracts import Page, ParsedDocument
from modules.qa.llm_parser import parse_llm_response
from modules.qa.reader.protocol import EventDeduper, parse_event
from modules.qa.reader.selection import locate_selection
from modules.qa.retrieval import rank_pages
from modules.qa.text_normalize import match_type, normalize


def test_normalize_vietnamese_unicode_and_pdf_hyphenation():
    assert normalize(unicodedata.normalize("NFD", "Tiếng Việt")) == "tiếng việt"
    assert normalize("nghi-" + "\n" + " ên cứu") == "nghiên cứu"


def test_normalize_ligatures_quotes_and_whitespace():
    assert normalize("ﬁle  “A”—‘B’") == "file " + chr(34) + "a" + chr(34) + "-'b'"


def test_match_types():
    assert match_type("cơ sở dữ liệu", "Chương về cơ sở dữ liệu") == "exact"
    assert match_type("Alice works in Paris.", "Alice works in Paris") == "fuzzy"
    assert match_type("not here", "some other text") == "none"


def test_parser_handles_fence_prefix_and_trailing_comma():
    result = parse_llm_response(
        "Answer:"
        + "\n```json\n"
        + '{"answer":"ok","citations":[{"page_num":1,"evidence_text":"ok",}],}'
        + "\n```"
    )
    assert result["answer"] == "ok"
    assert result["background_note"] == ""


def test_parser_rejects_invalid_citation_page():
    try:
        parse_llm_response('{"answer":"x","citations":[{"page_num":0}]}')
    except ValueError:
        pass
    else:
        raise AssertionError("invalid page number should be rejected")


@pytest.mark.parametrize(
    "raw",
    [
        '{"answer":"x","can_answer":"yes"}',
        '{"answer":"x","citations":{}}',
        '{"answer":"x","citations":[{"page_num":true}]}',
        '{"answer":"x","citations":[{"page_num":-1}]}',
        '{"answer":"x","citations":[{"page_num":1,"evidence_text":4}]}',
        "not JSON at all",
        "```json\n{bad}\n```",
        '{"answer": []}',
        "[]",
        '{"answer":"x","citations":[null]}',
    ],
)
def test_parser_rejects_malformed_or_invalid_schema(raw):
    with pytest.raises((ValueError, TypeError)):
        parse_llm_response(raw)


def test_selection_matches_nfc_and_neighbor_pages():
    doc = ParsedDocument("doc", "x.pdf", [Page(1, "first"), Page(2, "café and notes")])
    assert locate_selection(doc, 1, unicodedata.normalize("NFD", "café")).page == 2


def test_selection_matches_text_across_adjacent_pages():
    doc = ParsedDocument(
        "doc-cross-page",
        "x.pdf",
        [Page(1, "The first part of a sentence"), Page(2, "continues on this page.")],
    )
    match = locate_selection(doc, 1, "part of a sentence continues on this page")
    assert match.page == 1 and match.match_type == "exact"


def test_selection_unmatched_does_not_raise():
    doc = ParsedDocument("doc", "x.pdf", [Page(1, "first")])
    assert locate_selection(doc, 1, "missing phrase").match_type == "none"


def test_protocol_limits_and_event_dedup():
    event = parse_event(
        {
            "event_id": "e1",
            "type": "ask",
            "action": "explain",
            "page": 1,
            "selected_text": "hello",
        },
        1,
    )
    assert event is not None
    assert (
        parse_event(
            {
                "event_id": "e2",
                "type": "ask",
                "action": "bad",
                "page": 1,
                "selected_text": "hello",
            },
            1,
        )
        is None
    )
    assert (
        parse_event(
            {
                "event_id": "e3",
                "type": "ask",
                "action": "explain",
                "page": 0,
                "selected_text": "hello",
            },
            1,
        )
        is None
    )
    assert (
        parse_event(
            {
                "event_id": "e4",
                "type": "ask",
                "action": "explain",
                "page": 1,
                "selected_text": "x" * 4001,
            },
            1,
        )
        is None
    )
    deduper = EventDeduper(2)
    assert deduper.accept("a") and not deduper.accept("a")


def test_protocol_validates_non_ask_event_payloads():
    assert parse_event({"event_id": "p", "type": "page_changed", "page": 0}, 2) is None
    assert parse_event({"event_id": "t", "type": "open_thread"}, 2) is None
    assert parse_event({"event_id": "n", "type": "need_pdf"}, 2) is None
    assert parse_event({"event_id": "p", "type": "page_changed", "page": 2}, 2)
    assert parse_event({"event_id": "t", "type": "open_thread", "thread_id": "abc"}, 2)
    assert (
        parse_event(
            {
                "event_id": "c",
                "type": "ask",
                "action": "custom",
                "page": 1,
                "selected_text": "text",
            },
            2,
        )
        is None
    )


def test_retrieval_ranks_relevant_page():
    pages = [
        Page(1, "intro unrelated"),
        Page(2, "database primary key uniquely identifies each row"),
        Page(3, "conclusion"),
    ]
    ranked = rank_pages("primary key", pages, limit=1)
    assert any(p.number == 2 for p in ranked)
