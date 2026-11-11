from __future__ import annotations

import hashlib
import time
import unicodedata
from uuid import uuid4

from core.contracts import ParsedDocument
from core.llm_client import LLMClient, LLMResponse, get_client

from .citation_verifier import verify_answer_citations
from .llm_parser import parse_llm_response
from .models import Answer, Citation
from .prompt import (
    PROMPT_VERSION,
    build_doc_prompt,
    build_repair_prompt,
    build_selection_prompt,
)
from .reader.actions import build_instruction
from .reader.selection import locate_selection
from .retrieval import rank_pages
from .structured_logging import log_qa_error, log_qa_event


class QAService:
    """Create document-grounded answers through the shared core LLM client."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        response_cache: dict[str, dict] | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.llm_client = llm_client or get_client()
        self.response_cache = response_cache
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _question_id(question: str) -> str:
        normalized = " ".join(
            unicodedata.normalize("NFC", question.strip().lower()).split()
        )
        return "q-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]

    def _log_answer(
        self, document: ParsedDocument, question: str, answer: Answer, started: float
    ) -> Answer:
        log_qa_event(
            doc_id=document.doc_id,
            question_id=answer.question_id,
            model_used=answer.model_used,
            source=answer.source,
            latency_ms=(time.perf_counter() - started) * 1000,
            status=answer.status,
        )
        return answer

    def _generate(
        self,
        document: ParsedDocument,
        question: str,
        prompt: str,
        system: str,
        started: float,
    ) -> LLMResponse:
        for attempt in range(3):
            try:
                return self.llm_client.generate(
                    prompt,
                    system=system,
                    use_cache=False,
                    timeout=self.timeout_seconds,
                )
            except Exception as exc:
                if self._is_retryable(exc) and attempt < 2:
                    time.sleep(0.5 * (2**attempt))
                    continue
                log_qa_error(
                    doc_id=document.doc_id,
                    question_id=self._question_id(question),
                    model_used=self.llm_client.model,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    error=exc,
                )
                raise

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        names = " ".join(cls.__name__.lower() for cls in type(error).__mro__)
        if any(
            token in names
            for token in (
                "timeout",
                "deadline",
                "connection",
                "transport",
                "servererror",
                "serviceunavailable",
            )
        ):
            return True
        status = getattr(error, "status_code", getattr(error, "code", None))
        try:
            return int(status) in {408, 429, 500, 502, 503, 504}
        except (TypeError, ValueError):
            return False

    def _parse_with_repair(self, response, document, question, system, started):
        try:
            return parse_llm_response(response.text)
        except (TypeError, ValueError) as first_error:
            repair_prompt = build_repair_prompt(response.text, str(first_error))
            repaired = self._generate(
                document, question, repair_prompt, system, started
            )
            try:
                return parse_llm_response(repaired.text)
            except (TypeError, ValueError) as second_error:
                raise ValueError(
                    f"LLM response remained invalid after one repair attempt: {second_error}"
                ) from second_error

    def _cache_key(self, document: ParsedDocument, prompt: str, system: str) -> str:
        value = "\0".join(
            (document.doc_id, PROMPT_VERSION, self.llm_client.model, system, prompt)
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _cached_answer(self, key: str | None) -> Answer | None:
        if key is None or self.response_cache is None:
            return None
        payload = self.response_cache.get(key)
        if payload is None:
            return None
        answer = Answer.from_dict(payload)
        answer.answer_id = f"answer-{answer.doc_id}-{uuid4().hex[:12]}"
        answer.source = "cache"
        return answer

    def _store_answer(self, key: str | None, answer: Answer) -> None:
        if (
            key is None
            or self.response_cache is None
            or answer.status != "verified"
            or answer.source == "local_fallback"
        ):
            return
        if len(self.response_cache) >= 200:
            self.response_cache.pop(next(iter(self.response_cache)))
        payload = answer.to_dict()
        payload["source"] = "llm"
        self.response_cache[key] = payload

    def ask_question(
        self, document: ParsedDocument, question: str, reference_material: bool = True
    ) -> Answer:
        if not question.strip():
            raise ValueError("Question text cannot be empty.")
        if not document.pages:
            raise ValueError("Document contains no parsed pages.")

        started = time.perf_counter()
        readable_pages = [
            p
            for p in document.pages
            if len(unicodedata.normalize("NFC", p.text).strip()) >= 20
        ]
        if not readable_pages:
            return self._log_answer(
                document,
                question,
                self._rejected(
                    document,
                    question,
                    "EMPTY_PAGE",
                    ["Không tìm thấy lớp văn bản có thể đọc; PDF có thể là bản scan."],
                ),
                started,
            )
        context = (
            rank_pages(question, readable_pages, limit=8)
            if reference_material
            else readable_pages[:8]
        )
        prompt = build_doc_prompt(question, context)
        system = "You are a careful document analyst. Do not invent facts or citations."
        cache_key = (
            self._cache_key(document, prompt, system)
            if self.response_cache is not None
            else None
        )
        cached = self._cached_answer(cache_key)
        if cached is not None:
            return self._log_answer(document, question, cached, started)
        response = self._generate(document, question, prompt, system, started)
        try:
            payload = self._parse_with_repair(
                response, document, question, system, started
            )
        except (TypeError, ValueError) as exc:
            return self._log_answer(
                document,
                question,
                self._rejected(document, question, "LLM_UNAVAILABLE", [str(exc)]),
                started,
            )
        answer_text = payload["answer"].strip()
        if not payload["can_answer"]:
            answer = Answer(
                answer_id=f"answer-{document.doc_id}-{uuid4().hex[:12]}",
                doc_id=document.doc_id,
                question_id=self._question_id(question),
                text=answer_text or "Tài liệu chưa đủ thông tin để trả lời.",
                status="verified",
                rejection_reason=None,
                can_answer=False,
                source="cache" if response.cached else "llm",
                model_used=self.llm_client.model,
                background_note=payload["background_note"],
            )
            return self._log_answer(document, question, answer, started)
        if not answer_text:
            return self._log_answer(
                document,
                question,
                self._rejected(
                    document,
                    question,
                    "INVALID_INPUT",
                    ["Mô hình trả về câu trả lời trống."],
                ),
                started,
            )

        citations: list[Citation] = []
        for item in payload.get("citations", []):
            if isinstance(item, int):
                item = {"page_num": item, "evidence_text": ""}
            if not isinstance(item, dict):
                continue
            number = int(item.get("page_num", 0))
            evidence = str(item.get("evidence_text", "")).strip()
            if number > 0 and evidence:
                citations.append(
                    Citation(number, evidence, float(item.get("confidence", 1.0)))
                )

        answer = Answer(
            answer_id=f"answer-{document.doc_id}-{uuid4().hex[:12]}",
            doc_id=document.doc_id,
            question_id=self._question_id(question),
            text=answer_text,
            citations=citations,
            source="cache" if response.cached else "llm",
            model_used=self.llm_client.model,
            background_note=payload["background_note"],
        )
        valid, warnings = verify_answer_citations(context, answer)
        if not valid:
            answer.status = "rejected"
            answer.rejection_reason = warnings[0]
            answer.warnings = warnings
            return self._log_answer(document, question, answer, started)
        answer.status = "verified"
        self._store_answer(cache_key, answer)
        return self._log_answer(document, question, answer, started)

    @staticmethod
    def _rejected(document, question, reason, warnings):
        return Answer(
            answer_id=f"answer-{document.doc_id}-{uuid4().hex[:12]}",
            doc_id=document.doc_id,
            question_id=QAService._question_id(question),
            text="Chưa thể tạo câu trả lời đáng tin cậy.",
            status="rejected",
            rejection_reason=reason,
            warnings=warnings,
            can_answer=False,
        )

    def ask_about_selection(
        self,
        document: ParsedDocument,
        page_num: int,
        selected_text: str,
        action: str = "explain",
        custom_question: str = "",
        thread_history=(),
        thread_id: str | None = None,
    ) -> Answer:
        if page_num not in {p.number for p in document.pages}:
            raise ValueError("Page number is outside the current document.")
        if not selected_text.strip() or len(selected_text) > 4000:
            raise ValueError("Đoạn chọn trống hoặc dài quá giới hạn.")
        started = time.perf_counter()
        match = locate_selection(document, page_num, selected_text)
        instruction = build_instruction(action, custom_question)
        nearby = [
            p
            for p in document.pages
            if abs(p.number - match.page) <= 1 and len(p.text.strip()) >= 20
        ]
        if not nearby:
            return self._log_answer(
                document,
                instruction,
                self._rejected(
                    document,
                    instruction,
                    "EMPTY_PAGE",
                    ["Trang này không có lớp văn bản có thể đọc."],
                ),
                started,
            )
        prompt = build_selection_prompt(
            instruction, selected_text, nearby, thread_history[-12:]
        )
        system = "You explain documents accurately in Vietnamese."
        cache_key = (
            self._cache_key(document, prompt, system)
            if self.response_cache is not None
            else None
        )
        cached = self._cached_answer(cache_key)
        if cached is not None:
            return self._log_answer(document, instruction, cached, started)
        response = self._generate(document, instruction, prompt, system, started)
        try:
            payload = self._parse_with_repair(
                response, document, instruction, system, started
            )
        except (TypeError, ValueError) as exc:
            return self._log_answer(
                document,
                instruction,
                self._rejected(document, instruction, "LLM_UNAVAILABLE", [str(exc)]),
                started,
            )
        if not payload["can_answer"]:
            return self._log_answer(
                document,
                instruction,
                Answer(
                    answer_id=f"answer-{document.doc_id}-{uuid4().hex[:12]}",
                    doc_id=document.doc_id,
                    question_id=self._question_id(instruction + selected_text),
                    text=payload["answer"] or "Tài liệu chưa đủ thông tin để trả lời.",
                    status="verified",
                    can_answer=False,
                    source="cache" if response.cached else "llm",
                    model_used=self.llm_client.model,
                    background_note=payload["background_note"],
                ),
                started,
            )
        citations = [
            Citation(
                int(c["page_num"]), c["evidence_text"], float(c.get("confidence", 1))
            )
            for c in payload["citations"]
            if c.get("evidence_text")
        ]
        answer = Answer(
            answer_id=f"answer-{document.doc_id}-{uuid4().hex[:12]}",
            doc_id=document.doc_id,
            question_id=self._question_id(instruction + selected_text),
            text=payload["answer"],
            citations=citations,
            source="cache" if response.cached else "llm",
            model_used=self.llm_client.model,
            background_note=payload["background_note"],
            selection_verified=match.match_type != "none",
        )
        valid, warnings = verify_answer_citations(nearby, answer)
        answer.status = "verified" if valid else "rejected"
        answer.warnings = warnings
        answer.rejection_reason = None if valid else warnings[0]
        if valid:
            self._store_answer(cache_key, answer)
        return self._log_answer(document, instruction, answer, started)
