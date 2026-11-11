from core.contracts import ParsedDocument
from modules.qa.api import get_current_document


def test_public_api_returns_document_from_session_state():
    document = ParsedDocument("d", "x.txt")
    assert get_current_document({"qa_document": document}) is document
    assert get_current_document({}) is None
