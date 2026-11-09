import json

from core.contracts import ParsedDocument, Page
from core.llm_client import LLMResponse
from modules.qa import QAService


class FakeLLMClient:
    model = "fake-model"

    def generate(self, prompt, *, system=None, temperature=0.0, use_cache=True):
        return LLMResponse(json.dumps({
            "answer": "Alice works in Paris.",
            "citations": [{"page_num": 1, "evidence_text": "Alice works in Paris."}],
        }))


def test_qa_service_approves_valid_answer() -> None:
    document = ParsedDocument(
        doc_id="doc-3",
        filename="sample.txt",
        pages=[
            Page(number=1, text="Alice works in Paris. The city is known for its museums."),
            Page(number=2, text="Paris is the capital of France."),
        ],
    )

    service = QAService(FakeLLMClient())
    answer = service.ask_question(document, "What city does Alice work in?")

    assert answer.status == "verified"
    assert answer.citations
    assert answer.citations[0].page_num in {1, 2}
