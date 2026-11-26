"""Người dùng duyệt từng tệp đính kèm: tệp này dùng để làm gì.

Tệp an toàn không còn tự chảy sang mọi trang. Mỗi tệp được gợi ý một mục đích (theo tên tệp và nội dung),
người dùng chọn lại nếu cần rồi bấm duyệt; chỉ khi đó tệp mới được dùng:

- ``assignment``: đề bài / hạn nộp → trang Trích xuất bài tập (và Hỏi đáp);
- ``exam``: lịch thi / kiểm tra → buổi thi trên lịch + nhiệm vụ ôn thi;
- ``timetable``: thời khoá biểu → thời khoá biểu của tài khoản;
- ``material``: tài liệu học → chỉ Hỏi đáp tài liệu;
- ``skip``: bỏ qua.

Quyết định lưu trong ``state/attachments.json`` của tài khoản, khoá theo SHA-256 của tệp, và được chép
vào ``st.session_state["attachment_purpose"]`` để các trang khác lọc.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

PURPOSES: dict[str, tuple[str, str]] = {
    "assignment": ("📝", "Bài tập / hạn nộp"),
    "exam": ("🧪", "Lịch thi / kiểm tra"),
    "timetable": ("🗓️", "Thời khoá biểu"),
    "material": ("📚", "Tài liệu học"),
    "skip": ("🚫", "Bỏ qua"),
}
STATE_KEY = "attachment_purpose"
USES = {"extraction": {"assignment"}, "qa": {"assignment", "material"}}

_KEYWORDS = (  # thứ tự quan trọng: từ khoá rõ nghĩa hơn đứng trước
    ("exam", ("lich thi", "lichthi", "kiem tra", "kiemtra", "giua ky", "cuoi ky", "thi cuoi", "thi giua",
              "ca thi", "phong thi", "exam", "midterm", "final test", "quiz")),
    ("timetable", ("thoi khoa bieu", "thoikhoabieu", "tkb", "timetable", "lich hoc", "lichhoc", "schedule")),
    ("assignment", ("de bai", "debai", "bai tap", "baitap", "btl", "assignment", "han nop", "deadline",
                    "nop bai", "do an", "project", "bao cao", "lich nop", "yeu cau")),
    ("material", ("slide", "bai giang", "giao trinh", "lecture", "chuong", "tai lieu", "syllabus",
                  "de cuong", "notes")),
)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[_\-.]+", " ", text)


def suggest(filename: str, text: str = "") -> str:
    """Mục đích gợi ý: tên tệp quyết định trước, rồi đến 3000 ký tự đầu của nội dung."""
    for source in (_fold(Path(filename).stem), _fold(text[:3000])):
        padded = f" {source} "
        for purpose, words in _KEYWORDS:
            if any(f" {w} " in padded or (len(w) > 4 and w in source) for w in words):
                return purpose
    ext = Path(filename).suffix.lower()
    if ext in {".pptx", ".mp4", ".mov", ".webm", ".mp3", ".m4a", ".wav"}:
        return "material"
    return "assignment" if ext in {".pdf", ".docx", ".xlsx", ".csv"} else "material"


def label(purpose: str) -> str:
    icon, name = PURPOSES.get(purpose, ("📄", purpose))
    return f"{icon} {name}"


def decisions(ws) -> dict[str, dict]:
    """{sha256: {"purpose": ..., "done": bool}} đã lưu của tài khoản."""
    d = ws.read_state("attachments", {}) or {}
    return {k: v for k, v in d.items() if isinstance(v, dict) and v.get("purpose") in PURPOSES}


def remember(ws, state: MutableMapping[str, Any], sha: str, purpose: str, done: bool = True) -> None:
    if purpose not in PURPOSES:
        raise ValueError(f"mục đích không hợp lệ: {purpose}")
    d = decisions(ws)
    d[sha] = {"purpose": purpose, "done": bool(done)}
    ws.write_state("attachments", d)
    sync(ws, state)


def sync(ws, state: MutableMapping[str, Any]) -> None:
    """Chép các tệp đã duyệt vào phiên để trang Trích xuất / Hỏi đáp lọc theo."""
    state[STATE_KEY] = {sha: v["purpose"] for sha, v in decisions(ws).items() if v.get("done")}


def allows(state: Mapping[str, Any], sha: str, use: str) -> bool:
    """Tệp ``sha`` có được dùng cho ``use`` ("extraction" | "qa") không.

    Phiên chưa từng mở Hộp thư mới (không có ``attachment_purpose``) giữ cách cũ: cho qua tất cả.
    """
    chosen = state.get(STATE_KEY)
    if not isinstance(chosen, Mapping):
        return True
    return chosen.get(sha) in USES[use]
