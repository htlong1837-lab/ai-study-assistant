from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from core.contracts import Page, ParsedDocument

from . import document_parser
from .document_parser import parse_document

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_PAGES = 1000
PARSE_TIMEOUT_SECONDS = 60


def _parse_pdf_with_timeout(
    path: str,
    doc_id: str,
    timeout_seconds: float = PARSE_TIMEOUT_SECONDS,
) -> ParsedDocument:
    if timeout_seconds <= 0:
        raise ValueError("Thời hạn phân tích PDF phải lớn hơn 0.")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "-m",
                "modules.qa.pdf_parse_worker",
                path,
                doc_id,
            ],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            f"Phân tích PDF vượt quá {timeout_seconds:g} giây và đã bị dừng."
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip()[-1000:]
        raise RuntimeError(f"Lỗi phân tích PDF: {detail or 'worker failed'}")
    try:
        payload = json.loads(result.stdout)
        return ParsedDocument(
            doc_id=payload["doc_id"],
            filename=payload["filename"],
            pages=[
                Page(number=item["number"], text=item["text"])
                for item in payload["pages"]
            ],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Worker phân tích PDF trả kết quả không hợp lệ.") from exc


def load_document_bytes(
    filename: str,
    data: bytes,
    doc_id: str | None = None,
    *,
    parse_timeout_seconds: float = PARSE_TIMEOUT_SECONDS,
) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise ValueError("Chỉ hỗ trợ PDF, TXT hoặc Markdown.")
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Tệp rỗng hoặc vượt giới hạn 50 MB.")
    if suffix == ".pdf" and not data.startswith(b"%PDF-"):
        raise ValueError("Tệp có đuôi PDF nhưng nội dung không phải PDF hợp lệ.")
    if suffix == ".pdf" and document_parser.fitz is None:
        raise RuntimeError("PyMuPDF is required to read PDF documents.")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        temp_path = Path(tmp.name)
    try:
        stable_doc_id = doc_id or hashlib.sha256(data).hexdigest()[:16]
        if suffix == ".pdf":
            document = _parse_pdf_with_timeout(
                str(temp_path), stable_doc_id, parse_timeout_seconds
            )
        else:
            document = parse_document(str(temp_path), stable_doc_id)
    finally:
        temp_path.unlink(missing_ok=True)
    document.filename = Path(filename).name
    if suffix in {".txt", ".md"}:
        return document
    if len(document.pages) > MAX_PAGES:
        raise ValueError("Tài liệu vượt giới hạn 1000 trang.")
    return document
