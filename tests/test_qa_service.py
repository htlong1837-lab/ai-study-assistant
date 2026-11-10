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


import pytest


class _ScriptedClient:
    model = "fake-model"

    def __init__(self, text: str) -> None:
        self.text = text

    def generate(self, prompt, *, system=None, temperature=0.0, use_cache=True):
        return LLMResponse(self.text)


def _deadline_doc() -> ParsedDocument:
    return ParsedDocument(
        doc_id="doc-deadline",
        filename="de-bai.pdf",
        pages=[
            Page(number=1, text="Hạn nộp bài tập lớn là 15/11."),
            Page(number=2, text="Chương 2 nói về tìm kiếm."),
        ],
    )


@pytest.mark.parametrize("citations", [
    [{"page_num": 1}],                        # có trang, thiếu câu trích
    [{"page_num": 1, "evidence_text": ""}],   # câu trích rỗng
    [1],                                      # chỉ có số trang
])
def test_citation_without_evidence_is_rejected(citations) -> None:
    """Trích dẫn không có câu trích thì không được tự điền bằng chứng để qua kiểm tra."""
    payload = json.dumps({"answer": "Hạn nộp là 30/12.", "citations": citations})
    with pytest.raises(ValueError):
        QAService(_ScriptedClient(payload)).ask_question(_deadline_doc(), "Hạn nộp khi nào?")


def test_evidence_not_in_page_is_rejected() -> None:
    payload = json.dumps({"answer": "Hạn nộp là 30/12.",
                          "citations": [{"page_num": 1, "evidence_text": "Hạn nộp là 30/12."}]})
    with pytest.raises(ValueError):
        QAService(_ScriptedClient(payload)).ask_question(_deadline_doc(), "Hạn nộp khi nào?")


@pytest.mark.parametrize("wrap", [
    "```json\n{}\n```",
    "```\n{}\n```",
    "Đây là kết quả:\n{}",
])
def test_json_wrapped_by_llm_is_parsed(wrap: str) -> None:
    """Gemini hay bọc JSON trong ```json ... ```; vẫn phải đọc được."""
    body = json.dumps({"answer": "15/11",
                       "citations": [{"page_num": 1, "evidence_text": "Hạn nộp bài tập lớn là 15/11."}]},
                      ensure_ascii=False)
    answer = QAService(_ScriptedClient(wrap.replace("{}", body))).ask_question(
        _deadline_doc(), "Hạn nộp khi nào?")
    assert answer.status == "verified"
    assert answer.citations[0].page_num == 1


def test_non_json_response_is_rejected() -> None:
    with pytest.raises(ValueError):
        QAService(_ScriptedClient("[fake] không phải JSON")).ask_question(
            _deadline_doc(), "Hạn nộp khi nào?")
