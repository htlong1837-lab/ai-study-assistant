import pytest
import subprocess

from core.contracts import Page, ParsedDocument
from modules.qa import document_parser
from modules.qa import loader


def test_load_text_file_and_generate_stable_document_id():
    first = loader.load_document_bytes("notes.txt", "hello world".encode())
    second = loader.load_document_bytes("notes.txt", "hello world".encode())
    assert first.pages[0].text == "hello world"
    assert first.doc_id == second.doc_id
    assert first.filename == "notes.txt"


@pytest.mark.parametrize("filename,data", [("bad.exe", b"x"), ("empty.txt", b"")])
def test_rejects_unsupported_or_empty_upload(filename, data):
    with pytest.raises(ValueError):
        loader.load_document_bytes(filename, data)


def test_rejects_pdf_with_wrong_magic_bytes():
    with pytest.raises(ValueError, match="không phải PDF"):
        loader.load_document_bytes("fake.pdf", b"not a pdf")


def test_missing_pdf_library_fails_explicitly(tmp_path, monkeypatch):
    monkeypatch.setattr(document_parser, "fitz", None)
    with pytest.raises(RuntimeError, match="PyMuPDF"):
        loader.load_document_bytes("fake.pdf", b"%PDF-1.7")


def test_rejects_document_over_page_limit(monkeypatch):
    pages = [Page(number, "text") for number in range(1, loader.MAX_PAGES + 2)]
    parsed = ParsedDocument("many", "many.pdf", pages)
    monkeypatch.setattr(
        loader, "_parse_pdf_with_timeout", lambda *args, **kwargs: parsed
    )
    with pytest.raises(ValueError, match="1000 trang"):
        loader.load_document_bytes("many.pdf", b"%PDF-1.7")


def test_pdf_parser_timeout_is_reported(monkeypatch, tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.7")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(loader.subprocess, "run", timeout)
    with pytest.raises(TimeoutError, match="đã bị dừng"):
        loader._parse_pdf_with_timeout(str(source), "slow", 1)


def test_valid_pdf_is_parsed_in_isolated_worker():
    fitz = pytest.importorskip("fitz")
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "A sample page with enough readable words.")
    raw = pdf.tobytes()
    pdf.close()
    document = loader.load_document_bytes("sample.pdf", raw)
    assert "sample page" in document.pages[0].text
