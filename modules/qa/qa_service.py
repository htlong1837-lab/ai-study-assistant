from __future__ import annotations

import hashlib
import json
import unicodedata
from uuid import uuid4

from core.contracts import ParsedDocument
from core.llm_client import LLMClient, LLMResponse, get_client

from .citation_verifier import validate_answer
from .models import Answer, Citation


def _parse_json(text: str | None) -> dict:
    """Đọc JSON từ phản hồi LLM, chấp nhận khối ```json ... ``` bao quanh."""
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else ""
        raw = raw.rsplit("```", 1)[0].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("LLM response was not valid JSON.") from None
        try:
            payload = json.loads(raw[start:end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response was not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("LLM response was not a JSON object.")
    return payload


class QAService:
    """Create document-grounded answers through the shared core LLM client."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or get_client()

    @staticmethod
    def _question_id(question: str) -> str:
        normalized = " ".join(unicodedata.normalize("NFC", question.strip().lower()).split())
        return "q-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _prompt(document: ParsedDocument, question: str, reference_material: bool) -> str:
        pages = "\n\n".join(f"[Page {p.number}]\n{p.text}" for p in document.pages)
        guidance = (
            "Synthesize relevant facts across the source pages when useful."
            if reference_material
            else "Answer only the specific question from the supplied pages; do not add broader context."
        )
        return (
            "Answer only from the source pages. " + guidance + " "
            "Return valid JSON with keys answer and citations. "
            "citations must be a list of objects with page_num and evidence_text; evidence_text "
            "must be copied exactly from that page. If the document does not support an answer, "
            "say so.\n\nQuestion: " + question + "\n\nSource pages:\n" + pages
        )

    def ask_question(self, document: ParsedDocument, question: str,
                     reference_material: bool = True) -> Answer:
        if not question.strip():
            raise ValueError("Question text cannot be empty.")
        if not document.pages:
            raise ValueError("Document contains no parsed pages.")

        response: LLMResponse = self.llm_client.generate(
            self._prompt(document, question, reference_material),
            system="You are a careful document analyst. Do not invent facts or citations.",
        )
        payload = _parse_json(response.text)
        answer_text = str(payload.get("answer", "")).strip()
        if not answer_text:
            raise ValueError("LLM response did not contain an answer.")

        citations: list[Citation] = []
        for item in payload.get("citations", []):
            if not isinstance(item, dict):
                continue  # chỉ có số trang, không có câu trích → không kiểm chứng được
            number = int(item.get("page_num", 0))
            # Không tự điền bằng chứng: thiếu evidence_text thì bỏ trích dẫn này,
            # nếu không còn trích dẫn nào thì validate_answer sẽ từ chối câu trả lời.
            evidence = str(item.get("evidence_text", "")).strip()
            if number > 0 and evidence:
                citations.append(Citation(number, evidence, float(item.get("confidence", 1.0))))

        answer = Answer(
            answer_id=f"answer-{document.doc_id}-{uuid4().hex[:12]}",
            doc_id=document.doc_id,
            question_id=self._question_id(question),
            text=answer_text,
            citations=citations,
            source="cache" if response.cached else "llm",
            model_used=self.llm_client.model,
        )
        valid, warnings = validate_answer(document, answer)
        if not valid:
            answer.status = "rejected"
            raise ValueError("Unsupported citations were found: " + "; ".join(warnings))
        answer.status = "verified"
        return answer
