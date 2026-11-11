from core.contracts import ParsedDocument, Page
from modules.qa.citation_verifier import verify_citations
from modules.qa.models import Citation


def test_verify_citations_rejects_missing_evidence() -> None:
    document = ParsedDocument(
        doc_id="doc-2",
        filename="sample.txt",
        pages=[Page(number=1, text="Alice works in Paris. The city is known for its museums.")],
    )

    citations = [Citation(page_num=1, evidence_text="Alice studied in London.")]
    valid, warnings = verify_citations(document, citations)

    assert valid is False
    assert any("not present" in warning for warning in warnings)
