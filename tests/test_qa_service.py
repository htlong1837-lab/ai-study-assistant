from src.models.document import ParsedDocument, Page
from src.qa_service import QAService


def test_qa_service_approves_valid_answer() -> None:
    document = ParsedDocument(
        doc_id="doc-3",
        file_path="/tmp/sample.txt",
        pages=[
            Page(page_num=1, text="Alice works in Paris. The city is known for its museums."),
            Page(page_num=2, text="Paris is the capital of France."),
        ],
    )

    service = QAService(api_key="fake-test-key-for-unit-test")
    answer = service.ask_question(document, "What city does Alice work in?")

    assert answer.status == "verified"
    assert answer.citations
    assert answer.citations[0].page_num in {1, 2}
