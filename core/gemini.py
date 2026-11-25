"""Gọi Gemini cho chắc: tự đổi sang model "flash" còn dùng được khi model cấu hình bị Google ngừng, và dịch
lỗi của Google thành câu dễ hiểu (không bao giờ lộ khóa).
"""
from __future__ import annotations

import re
import threading
from collections.abc import Callable
from typing import Any

FALLBACK_MODELS = ("gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash")
_EXCLUDE = ("tts", "image", "live", "audio", "embedding", "thinking-exp", "native")
_resolved: dict[str, str] = {}  # model cấu hình → model đã dùng được (theo khóa băm)
_lock = threading.Lock()


def is_model_missing(exc: Exception) -> bool:
    msg = str(exc)
    return ("404" in msg or "NOT_FOUND" in msg) and ("model" in msg.lower())


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
    latest = [n for n in names if n.endswith("latest")]
    rest = sorted((n for n in names if n not in latest), reverse=True)
    return latest + rest


def call_with_fallback(client: Any, model: str, call: Callable[[str], Any], key_id: str = "") -> Any:
    """Gọi ``call(model)``; nếu model không còn tồn tại thì thử lần lượt model thay thế."""
    cache_key = f"{key_id}|{model}"
    first = _resolved.get(cache_key, model)
    try:
        return call(first)
    except Exception as exc:  # noqa: BLE001
        if not is_model_missing(exc):
            raise
        last = exc
    tried = {first}
    for candidate in (*FALLBACK_MODELS, *available_flash_models(client)):
        if candidate in tried:
            continue
        tried.add(candidate)
        try:
            out = call(candidate)
        except Exception as exc:  # noqa: BLE001
            if is_model_missing(exc):
                last = exc
                continue
            raise
        with _lock:
            _resolved[cache_key] = candidate
        return out
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
        return "Gemini đang quá tải, thử lại sau ít phút."
    if "400" in msg or "INVALID_ARGUMENT" in msg:
        return f"Gemini từ chối yêu cầu: {reason}"
    if any(k in msg.lower() for k in ("timed out", "timeout", "connection", "resolve", "network")):
        return "Không kết nối được tới Gemini. Kiểm tra mạng rồi thử lại."
    return f"Gemini báo lỗi: {reason}"
