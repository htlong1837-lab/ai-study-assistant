from src.citation_verifier import verify_citations
from src.models.citation import Citation
from src.models.document import ParsedDocument, Page


def test_verify_citations_rejects_missing_evidence() -> None:
    document = ParsedDocument(
        doc_id="doc-2",
        file_path="/tmp/sample.txt",
        pages=[Page(page_num=1, text="Alice works in Paris. The city is known for its museums.")],
    )

    citations = [Citation(page_num=1, evidence_text="Alice studied in London.")]
    valid, warnings = verify_citations(document, citations)

    assert valid is False
    assert any("does not appear" in warning for warning in warnings)
