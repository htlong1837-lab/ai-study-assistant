"""Unit tests verifying unique answer_id generation and stable question_id hashing."""
from __future__ import annotations

import unicodedata
from models.document import Page, ParsedDocument
from qa_service import QAService


def test_different_questions_produce_different_answer_ids() -> None:
    doc = ParsedDocument(
        doc_id="doc-42",
        file_path="/tmp/test.txt",
        pages=[Page(page_num=1, text="The quick brown fox jumps over the lazy dog.")],
    )
    service = QAService(api_key="test-key")

    ans1 = service.ask_question(doc, "What does the fox do?")
    ans2 = service.ask_question(doc, "What color is the fox?")

    assert ans1.answer_id != ans2.answer_id, "answer_id collision detected!"
    assert ans1.question_id != ans2.question_id


def test_same_question_produces_identical_question_id() -> None:
    doc = ParsedDocument(
        doc_id="doc-42",
        file_path="/tmp/test.txt",
        pages=[Page(page_num=1, text="Vietnam is in Southeast Asia.")],
    )
    service = QAService(api_key="test-key")

    ans1 = service.ask_question(doc, "Where is Vietnam?")
    ans2 = service.ask_question(doc, "   where is vietnam?   ")

    assert ans1.question_id == ans2.question_id, "Normalized question_id should be identical!"


def test_vietnamese_unicode_nfc_nfd_produces_identical_question_id() -> None:
    # NFC (precomposed) vs NFD (decomposed) Vietnamese characters
    q_nfc = unicodedata.normalize("NFC", "Trần Quốc Toản bóp nát quả cam")
    q_nfd = unicodedata.normalize("NFD", "Trần Quốc Toản bóp nát quả cam")

    # Raw strings have different byte lengths and code points
    assert q_nfc != q_nfd

    id_nfc = QAService._make_question_id(q_nfc)
    id_nfd = QAService._make_question_id(q_nfd)

    assert id_nfc == id_nfd, "NFC and NFD questions should result in the exact same question_id!"
