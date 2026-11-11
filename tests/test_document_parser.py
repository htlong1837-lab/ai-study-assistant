from pathlib import Path

from modules.qa.document_parser import parse_document


def test_parse_document_from_text_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Alpha\n\nBeta\n\nGamma", encoding="utf-8")

    document = parse_document(str(file_path), "doc-1")

    assert document.doc_id == "doc-1"
    assert document.filename == "sample.txt"
    assert len(document.pages) == 1
    assert "Alpha" in document.pages[0].text
    assert "Gamma" in document.pages[0].text
