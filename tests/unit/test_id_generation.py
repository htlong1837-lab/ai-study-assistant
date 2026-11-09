"""Unit tests verifying unique answer_id generation and stable question_id hashing."""
from __future__ import annotations

import unicodedata
from core.contracts import Page, ParsedDocument
from modules.qa import QAService


def test_different_questions_produce_different_answer_ids() -> None:
    doc = ParsedDocument(
        doc_id="doc-42",
        filename="test.txt",
        pages=[Page(number=1, text="The quick brown fox jumps over the lazy dog.")],
    )
    assert QAService._question_id("What does the fox do?") != QAService._question_id("What color is the fox?")


def test_same_question_produces_identical_question_id() -> None:
    doc = ParsedDocument(
        doc_id="doc-42",
        filename="test.txt",
        pages=[Page(number=1, text="Vietnam is in Southeast Asia.")],
    )
    assert QAService._question_id("Where is Vietnam?") == QAService._question_id("   where is vietnam?   ")


def test_vietnamese_unicode_nfc_nfd_produces_identical_question_id() -> None:
    # NFC (precomposed) vs NFD (decomposed) Vietnamese characters
    q_nfc = unicodedata.normalize("NFC", "Trần Quốc Toản bóp nát quả cam")
    q_nfd = unicodedata.normalize("NFD", "Trần Quốc Toản bóp nát quả cam")

    # Raw strings have different byte lengths and code points
    assert q_nfc != q_nfd

    id_nfc = QAService._question_id(q_nfc)
    id_nfd = QAService._question_id(q_nfd)

    assert id_nfc == id_nfd, "NFC and NFD questions should result in the exact same question_id!"
