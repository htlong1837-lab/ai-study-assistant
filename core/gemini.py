"""Gọi Gemini cho chắc: thử lại khi Google quá tải, đổi sang model "flash" khác khi model đang dùng quá tải,
hết lượt hoặc bị ngừng, và dịch lỗi của Google thành câu dễ hiểu (không bao giờ lộ khóa).
"""
from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from typing import Any

DEFAULT_MODEL = "gemini-3.5-flash"
# Dùng khi không hỏi được Google danh sách model của khóa (danh sách thật luôn được ưu tiên).
FALLBACK_MODELS = ("gemini-3.5-flash", "gemini-flash-latest", "gemini-3.5-flash-lite", "gemini-flash-lite-latest")
_EXCLUDE = ("tts", "image", "live", "audio", "embedding", "thinking-exp", "native")
MAX_MODELS = 6            # thử tối đa chừng này model mỗi lần gọi
FIRST_MODEL_RETRIES = 2   # model đầu bị quá tải thì thử lại thêm ngần này lần
BACKOFF_SECONDS = (1.5, 4.0)
_resolved: dict[str, str] = {}  # model cấu hình đã bị ngừng → model thay thế dùng được (theo khóa băm)
_lock = threading.Lock()
_sleep = time.sleep


def is_model_missing(exc: Exception) -> bool:
    msg = str(exc)
    return ("404" in msg or "NOT_FOUND" in msg) and ("model" in msg.lower())


def is_transient(exc: Exception) -> bool:
    """Lỗi tạm thời phía Google: quá tải, lỗi nội bộ, hết giờ chờ."""
    msg = str(exc)
    return any(k in msg for k in ("503", "UNAVAILABLE", "500 INTERNAL", "INTERNAL", "504", "DEADLINE_EXCEEDED"))         or "overloaded" in msg.lower()


def is_quota(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def available_flash_models(client: Any) -> list[str]:
    """Các model "flash" hỗ trợ sinh nội dung mà khóa này dùng được, mới nhất trước."""
    names = []
    try:
        for m in client.models.list():
            name = str(getattr(m, "name", "")).removeprefix("models/")
            actions = getattr(m, "supported_actions", None) or []
            if "flash" in name and not any(x in name for x in _EXCLUDE) and (
                    not actions or "generateContent" in actions):
                names.append(name)
    except Exception:  # noqa: BLE001
        return []
    def rank(n: str):
        version = tuple(int(x) for x in re.findall(r"\d+", n.split("flash")[0])) or (0,)
        return ("lite" in n, any(x in n for x in ("preview", "exp")), not n.endswith("latest"),
                tuple(-v for v in version), n)
    return sorted(dict.fromkeys(names), key=rank)


def suggested_model(exc: Exception) -> str | None:
    """Model Google gợi ý thay thế trong lời báo lỗi ("Please update your code to use models/…")."""
    m = re.search(r"use models/([A-Za-z0-9._-]*[A-Za-z0-9])", str(exc))
    return m.group(1) if m else None


def call_with_fallback(client: Any, model: str, call: Callable[[str], Any], key_id: str = "") -> Any:
    """Gọi ``call(model)`` cho chắc:

    - model quá tải / lỗi tạm thời: thử lại model đó vài lần, chờ ngắn giữa các lần;
    - vẫn lỗi, hết lượt của model đó (429), hoặc model đã bị ngừng: chuyển sang model flash khác
      (mỗi model có hạn mức riêng). Model bị ngừng thì nhớ model thay thế cho các lần sau.
    Lỗi khác (khóa sai, yêu cầu sai) báo ngay.
    """
    cache_key = f"{key_id}|{model}"
    first = _resolved.get(cache_key, model)

    hints: list[str] = []  # model Google gợi ý trong lời báo lỗi

    def candidates():
        yield first
        while hints:
            yield hints.pop(0)
        yield from available_flash_models(client)  # model thật của khóa này
        yield from FALLBACK_MODELS

    tried: set[str] = set()
    last: Exception | None = None
    first_missing = False
    for m in candidates():
        if m in tried:
            continue
        if len(tried) >= MAX_MODELS:
            break
        tried.add(m)
        retries = FIRST_MODEL_RETRIES if m == first else 0
        for attempt in range(retries + 1):
            try:
                out = call(m)
            except Exception as exc:  # noqa: BLE001
                last = exc
                hint = suggested_model(exc)
                if hint and hint not in tried:
                    hints.append(hint)
                if is_transient(exc) and attempt < retries:
                    _sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])
                    continue
                if not (is_transient(exc) or is_quota(exc) or is_model_missing(exc)):
                    raise
                if m == first and is_model_missing(exc):
                    first_missing = True
                break
            else:
                if first_missing and m != first:
                    with _lock:
                        _resolved[cache_key] = m
                return out
    assert last is not None
    raise last


def friendly_error(exc: Exception, api_key: str = "") -> str:
    """Câu tiếng Việt cho lỗi khi gọi Gemini, kèm lý do gốc ngắn gọn (đã che khóa)."""
    msg = str(exc)
    if api_key:
        msg = msg.replace(api_key, "[khóa]")
    msg = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[khóa]", msg)
    m = re.search(r"'message':\s*'([^']{0,300})", msg) or re.search(r'"message":\s*"([^"]{0,300})', msg)
    reason = (m.group(1) if m else msg.splitlines()[0] if msg else type(exc).__name__)[:220]
    if "API key not valid" in msg or "API_KEY_INVALID" in msg or "401" in msg:
        return "Khóa Gemini không hợp lệ. Sao chép lại cả khóa trong Google AI Studio hoặc tạo khóa mới."
    if "403" in msg or "PERMISSION_DENIED" in msg:
        return f"Khóa Gemini chưa được phép dùng dịch vụ này ({reason})."
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return "Khóa Gemini đã hết lượt dùng miễn phí trong lúc này, thử lại sau ít phút."
    if is_model_missing(exc):
        return f"Không tìm thấy model Gemini phù hợp cho khóa này ({reason})."
    if "503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg.lower():
        return "Gemini đang quá tải ở mọi model đã thử, thử lại sau ít phút."
    if "400" in msg or "INVALID_ARGUMENT" in msg:
        return f"Gemini từ chối yêu cầu: {reason}"
    if any(k in msg.lower() for k in ("timed out", "timeout", "connection", "resolve", "network")):
        return "Không kết nối được tới Gemini. Kiểm tra mạng rồi thử lại."
    return f"Gemini báo lỗi: {reason}"
