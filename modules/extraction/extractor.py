"""Bộ trích xuất bài tập từ Email và Tài liệu (Module B).

Kết hợp:
1. LLM Structured Output (JSON / Pydantic).
2. Kiểm chứng bằng chứng (Evidence Grounding): quote phải là chuỗi con trong văn bản nguồn.
3. Động cơ chuẩn hoá ngày giờ tiếng Việt tất định.
4. Tính toán độ tin cậy tự động bằng code.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.contracts import ClassifiedEmail, ParsedDocument
from core.llm_client import LLMClient
from db.repository import Repository
from modules.extraction.confidence import compute_confidence
from modules.extraction.datetime_normalizer import NormalizedDeadline, normalize
from modules.extraction.gate import ensure_safe
from modules.extraction.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_extraction_prompt
from modules.extraction.schemas import ExtractionResult, RawAssignment

logger = logging.getLogger(__name__)

MAX_DOC_CHARS = 60_000
ASSIGNMENT_KEYWORDS = [
    "bài tập", "bai tap", "btvn", "đồ án", "do an", "assignment",
    "deadline", "hạn", "han", "nộp", "nop", "tiêu chí", "tieu chi", "rubric", "thang điểm"
]


@dataclass
class ExtractedItem:
    """Một bài tập được trích xuất và chuẩn hóa hoàn chỉnh."""
    assignment: RawAssignment
    normalized_deadlines: list[NormalizedDeadline] = field(default_factory=list)
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ExtractionOutcome:
    """Kết quả tổng thể của một lần gọi trích xuất."""
    items: list[ExtractedItem] = field(default_factory=list)
    is_empty: bool = False
    error: str | None = None
    tokens_used: int = 0
    from_cache: bool = False


def _normalize_text_for_search(text: str) -> str:
    """Chuẩn hóa khoảng trắng để tìm kiếm chuỗi con tin cậy."""
    return " ".join(text.lower().split())


def _verify_evidence_in_text(quote: str, source_text: str) -> bool:
    """Kiểm tra quote có thực sự là chuỗi con trong source_text hay không."""
    if not quote or not quote.strip():
        return False
    norm_quote = _normalize_text_for_search(quote)
    norm_source = _normalize_text_for_search(source_text)
    return norm_quote in norm_source


def _parse_llm_json(raw_text: str) -> dict[str, Any] | None:
    """Bóc tách JSON hợp lệ từ phản hồi của LLM."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception:
        # Thử tìm cặp ngoặc nhọn JSON đầu tiên và cuối cùng
        m = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return None


def extract_from_email(
    email: ClassifiedEmail,
    llm: LLMClient,
    repo: Repository | None = None,
    allow_suspicious: bool = False,
) -> ExtractionOutcome:
    """Trích xuất bài tập từ một email học tập an toàn."""
    # 1. Cổng bảo mật
    ensure_safe(email, allow_suspicious=allow_suspicious)

    full_email_text = f"Người gửi: {email.sender}\nTiêu đề: {email.subject}\nNội dung:\n{email.body}"
    content_hash = hashlib.sha256(full_email_text.encode("utf-8")).hexdigest()

    cached_log = None
    if repo:
        cached_log = repo.get_cached_extraction(email.id, content_hash, PROMPT_VERSION)

    raw_response_text: str = ""
    tokens = 0
    from_cache = False

    if cached_log and cached_log.get("raw_response"):
        raw_response_text = cached_log["raw_response"]
        tokens = (cached_log.get("prompt_tokens") or 0) + (cached_log.get("completion_tokens") or 0)
        from_cache = True
    else:
        prompt = build_extraction_prompt(full_email_text, source_type="email", location_hint="email")
        start_t = time.perf_counter()
        resp = llm.generate(prompt, system=SYSTEM_PROMPT, temperature=0.0)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        raw_response_text = resp.text
        tokens = resp.input_tokens + resp.output_tokens

        # Thử parse JSON; nếu lỗi, thử lại duy nhất 1 lần
        parsed_dict = _parse_llm_json(raw_response_text)
        if not parsed_dict:
            retry_prompt = (
                f"Phản hồi trước đó không phải JSON hợp lệ. Hãy sửa lại và chỉ trả về duy nhất chuỗi JSON:\n{prompt}"
            )
            resp2 = llm.generate(retry_prompt, system=SYSTEM_PROMPT, temperature=0.0)
            raw_response_text = resp2.text
            tokens += resp2.input_tokens + resp2.output_tokens
            parsed_dict = _parse_llm_json(raw_response_text)

        if repo:
            try:
                repo.log_extraction({
                    "source_type": "email",
                    "source_id": email.id,
                    "content_hash": content_hash,
                    "prompt_version": PROMPT_VERSION,
                    "model_name": getattr(llm, "model", "default"),
                    "prompt_tokens": resp.input_tokens,
                    "completion_tokens": resp.output_tokens,
                    "execution_time_ms": elapsed_ms,
                    "raw_response": raw_response_text,
                })
            except Exception as e:
                logger.warning(f"Không thể ghi extraction_log: {e}")

    # Parse Pydantic
    parsed_dict = _parse_llm_json(raw_response_text)
    if not parsed_dict:
        return ExtractionOutcome(
            error="Không thể phân tích cú pháp JSON từ phản hồi LLM",
            tokens_used=tokens,
            from_cache=from_cache,
        )

    try:
        extraction_res = ExtractionResult.model_validate(parsed_dict)
    except Exception as e:
        return ExtractionOutcome(
            error=f"Dữ liệu trích xuất không khớp schema: {e}",
            tokens_used=tokens,
            from_cache=from_cache,
        )

    if extraction_res.not_assignment or not extraction_res.assignments:
        return ExtractionOutcome(is_empty=True, tokens_used=tokens, from_cache=from_cache)

    items: list[ExtractedItem] = []
    for raw_a in extraction_res.assignments:
        warnings: list[str] = []
        sources: list[dict[str, Any]] = []

        # Kiểm chứng Evidence trong thân email
        def _check_field(field_obj, field_name: str):
            if field_obj and field_obj.evidence and field_obj.evidence.quote:
                quote = field_obj.evidence.quote
                if _verify_evidence_in_text(quote, full_email_text):
                    sources.append({
                        "source": f"email:{email.id}",
                        "field": field_name,
                        "quote": quote,
                        "kind": "email",
                    })
                else:
                    field_obj.value = None
                    warnings.append(f"evidence_not_found:{field_name}")

        _check_field(raw_a.title, "title")
        _check_field(raw_a.course, "course")
        _check_field(raw_a.submission_platform, "submission_platform")
        _check_field(raw_a.submission_format, "submission_format")
        _check_field(raw_a.naming_convention, "naming_convention")
        _check_field(raw_a.grading_criteria, "grading_criteria")

        # Chuẩn hoá ngày giờ
        norm_deadlines: list[NormalizedDeadline] = []
        for dl in raw_a.deadlines:
            if dl.evidence and dl.evidence.quote:
                if _verify_evidence_in_text(dl.evidence.quote, full_email_text):
                    sources.append({
                        "source": f"email:{email.id}",
                        "field": "deadline",
                        "quote": dl.evidence.quote,
                        "kind": "email",
                    })
                else:
                    warnings.append("evidence_not_found:deadline")

            nd = normalize(dl.raw_text, anchor=email.received_at)
            norm_deadlines.append(nd)

        conf = compute_confidence(raw_a, norm_deadlines, warnings)
        items.append(ExtractedItem(
            assignment=raw_a,
            normalized_deadlines=norm_deadlines,
            confidence=conf,
            warnings=warnings,
            sources=sources,
        ))

    return ExtractionOutcome(items=items, tokens_used=tokens, from_cache=from_cache)


def extract_from_document(
    doc: ParsedDocument,
    llm: LLMClient,
    repo: Repository | None = None,
    pages: list[int] | None = None,
    anchor: datetime | None = None,
) -> ExtractionOutcome:
    """Trích xuất bài tập từ tài liệu PDF / văn bản theo trang."""
    anchor_dt = anchor or datetime.now(timezone.utc)

    # 1. Chọn trang
    selected_pages = doc.pages
    if pages:
        p_set = set(pages)
        selected_pages = [p for p in doc.pages if p.number in p_set]
    else:
        # Nếu tài liệu quá lớn, lọc theo từ khóa bài tập
        total_chars = sum(len(p.text) for p in doc.pages)
        if total_chars > MAX_DOC_CHARS:
            filtered = []
            for p in doc.pages:
                low = p.text.lower()
                if any(kw in low for kw in ASSIGNMENT_KEYWORDS):
                    filtered.append(p)
            if filtered:
                selected_pages = filtered

    if not selected_pages:
        return ExtractionOutcome(is_empty=True)

    doc_text_by_page = {p.number: p.text for p in selected_pages}
    full_doc_text = "\n\n".join(f"--- TRANG {p.number} ---\n{p.text}" for p in selected_pages)
    content_hash = hashlib.sha256(full_doc_text.encode("utf-8")).hexdigest()

    cached_log = None
    if repo:
        cached_log = repo.get_cached_extraction(doc.doc_id, content_hash, PROMPT_VERSION)

    raw_response_text = ""
    tokens = 0
    from_cache = False

    if cached_log and cached_log.get("raw_response"):
        raw_response_text = cached_log["raw_response"]
        tokens = (cached_log.get("prompt_tokens") or 0) + (cached_log.get("completion_tokens") or 0)
        from_cache = True
    else:
        prompt = build_extraction_prompt(full_doc_text, source_type="document", location_hint=f"doc:{doc.doc_id}")
        start_t = time.perf_counter()
        resp = llm.generate(prompt, system=SYSTEM_PROMPT, temperature=0.0)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        raw_response_text = resp.text
        tokens = resp.input_tokens + resp.output_tokens

        parsed_dict = _parse_llm_json(raw_response_text)
        if not parsed_dict:
            retry_prompt = f"Phản hồi không phải JSON hợp lệ. Hãy sửa lại và trả về JSON:\n{prompt}"
            resp2 = llm.generate(retry_prompt, system=SYSTEM_PROMPT, temperature=0.0)
            raw_response_text = resp2.text
            tokens += resp2.input_tokens + resp2.output_tokens
            parsed_dict = _parse_llm_json(raw_response_text)

        if repo:
            try:
                repo.log_extraction({
                    "source_type": "document",
                    "source_id": doc.doc_id,
                    "content_hash": content_hash,
                    "prompt_version": PROMPT_VERSION,
                    "model_name": getattr(llm, "model", "default"),
                    "prompt_tokens": resp.input_tokens,
                    "completion_tokens": resp.output_tokens,
                    "execution_time_ms": elapsed_ms,
                    "raw_response": raw_response_text,
                })
            except Exception as e:
                logger.warning(f"Không thể ghi extraction_log: {e}")

    parsed_dict = _parse_llm_json(raw_response_text)
    if not parsed_dict:
        return ExtractionOutcome(error="Lỗi JSON từ LLM khi đọc tài liệu", tokens_used=tokens, from_cache=from_cache)

    try:
        extraction_res = ExtractionResult.model_validate(parsed_dict)
    except Exception as e:
        return ExtractionOutcome(error=f"Lỗi schema tài liệu: {e}", tokens_used=tokens, from_cache=from_cache)

    if extraction_res.not_assignment or not extraction_res.assignments:
        return ExtractionOutcome(is_empty=True, tokens_used=tokens, from_cache=from_cache)

    items: list[ExtractedItem] = []
    for raw_a in extraction_res.assignments:
        warnings: list[str] = []
        sources: list[dict[str, Any]] = []

        def _verify_doc_evidence(field_obj, field_name: str):
            if field_obj and field_obj.evidence and field_obj.evidence.quote:
                quote = field_obj.evidence.quote
                loc = field_obj.evidence.location or "p1"
                m = re.search(r"\bp?(\d+)\b", loc.lower())
                page_num = int(m.group(1)) if m else None

                page_text = doc_text_by_page.get(page_num) if page_num else None
                found = False
                if page_text and _verify_evidence_in_text(quote, page_text):
                    found = True
                elif _verify_evidence_in_text(quote, full_doc_text):
                    found = True

                if found:
                    loc_str = f"doc:{doc.doc_id}#p{page_num}" if page_num else f"doc:{doc.doc_id}"
                    sources.append({"source": loc_str, "field": field_name, "quote": quote, "kind": "document"})
                else:
                    field_obj.value = None
                    warnings.append(f"evidence_not_found:{field_name}")

        _verify_doc_evidence(raw_a.title, "title")
        _verify_doc_evidence(raw_a.course, "course")
        _verify_doc_evidence(raw_a.submission_platform, "submission_platform")
        _verify_doc_evidence(raw_a.submission_format, "submission_format")
        _verify_doc_evidence(raw_a.naming_convention, "naming_convention")
        _verify_doc_evidence(raw_a.grading_criteria, "grading_criteria")

        norm_deadlines: list[NormalizedDeadline] = []
        for dl in raw_a.deadlines:
            if dl.evidence and dl.evidence.quote:
                if _verify_evidence_in_text(dl.evidence.quote, full_doc_text):
                    sources.append({"source": f"doc:{doc.doc_id}", "field": "deadline", "quote": dl.evidence.quote, "kind": "document"})
                else:
                    warnings.append("evidence_not_found:deadline")
            nd = normalize(dl.raw_text, anchor=anchor_dt)
            norm_deadlines.append(nd)

        conf = compute_confidence(raw_a, norm_deadlines, warnings)
        items.append(ExtractedItem(
            assignment=raw_a,
            normalized_deadlines=norm_deadlines,
            confidence=conf,
            warnings=warnings,
            sources=sources,
        ))

    return ExtractionOutcome(items=items, tokens_used=tokens, from_cache=from_cache)
