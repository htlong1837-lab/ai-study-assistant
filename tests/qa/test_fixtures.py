from core.contracts import ParsedDocument
from modules.qa.qa_service import QAService


def test_shared_qa_fixtures_work(fake_llm, sample_pdf, vietnamese_pages):
    assert sample_pdf.is_file()
    assert len(vietnamese_pages) == 2
    document = ParsedDocument("fixture-doc", "sample.txt", vietnamese_pages)
    answer = QAService(fake_llm).ask_question(document, "Nội dung mẫu là gì?")
    assert answer.status == "verified"
