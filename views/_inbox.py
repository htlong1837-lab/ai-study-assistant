"""Hộp thư của từng tài khoản giữ lại giữa các lần mở app.

Lưu thư thô (``.eml``) trong ``<thư mục tài khoản>/inbox/`` và quyết định của người dùng (email nghi ngờ
đã duyệt, email đã chuyển tiếp) trong ``state/inbox.json``, khoá theo mã băm nội dung thư (Message-ID có
thể thiếu và bị sinh ngẫu nhiên mỗi lần quét). Khi mở phiên mới, thư được quét lại và các quyết định
được áp lại, nên trang Trích xuất và Hỏi đáp có dữ liệu ngay cả khi người dùng vào thẳng các trang đó.
"""
from __future__ import annotations

import hashlib
from collections.abc import MutableMapping
from dataclasses import replace
from typing import Any

from core.workspace import Workspace

MAX_KEEP = 100  # giữ tối đa chừng này thư gần nhất


def raw_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()[:20]


def process(ws: Workspace, raw: bytes):
    """Quét email; tệp đính kèm an toàn lưu vào thư mục riêng của tài khoản."""
    from modules.email_security import process_email
    from modules.email_security.config import get_settings

    return process_email(raw, settings=replace(get_settings(), attachments_dir=str(ws.attachments_dir)))


def save_raw(ws: Workspace, raw: bytes) -> str:
    """Lưu thư thô (nếu chưa có), xoá bớt thư cũ nhất khi vượt ``MAX_KEEP``. Trả mã băm thư."""
    h = raw_hash(raw)
    ws.inbox_dir.mkdir(parents=True, exist_ok=True)
    path = ws.inbox_dir / f"{h}.eml"
    if not path.exists():
        path.write_bytes(raw)
    files = sorted(ws.inbox_dir.glob("*.eml"), key=lambda p: p.stat().st_mtime)
    for old in files[:-MAX_KEEP]:
        old.unlink(missing_ok=True)
    return h


def decisions(ws: Workspace) -> dict[str, list[str]]:
    d = ws.read_state("inbox", {}) or {}
    return {"approved": list(d.get("approved", [])), "forwarded": list(d.get("forwarded", []))}


def remember(ws: Workspace, state: MutableMapping[str, Any], email_id: str, kind: str) -> None:
    """Ghi lại một quyết định (``approved`` hoặc ``forwarded``) cho email trong phiên."""
    h = state.get("_raw_of", {}).get(email_id)
    if not h:
        return
    d = decisions(ws)
    if h not in d[kind]:
        d[kind].append(h)
        ws.write_state("inbox", d)


def restore(ws: Workspace, state: MutableMapping[str, Any]) -> int:
    """Đầu phiên: quét lại thư đã lưu, áp lại quyết định, chuyển tiếp lại email đã chuyển. Trả số thư."""
    from modules.email_security import approve_suspicious
    from modules.email_security.handoff import publish_to_modules

    if "processed_list" in state:
        return len(state["processed_list"])
    d = decisions(ws)
    items, raw_of = [], {}
    files = sorted(ws.inbox_dir.glob("*.eml"), key=lambda p: p.stat().st_mtime) if ws.inbox_dir.is_dir() else []
    for path in files:
        try:
            p = process(ws, path.read_bytes())
        except Exception:  # noqa: BLE001 — một thư hỏng không được làm mất cả hộp thư
            continue
        if path.stem in d["approved"]:
            p = approve_suspicious(p)
        items.append(p)
        raw_of[p.email.id] = path.stem
    from modules.email_security import purpose

    purpose.sync(ws, state)
    state["processed_list"] = items
    state["_raw_of"] = raw_of
    forwarded = state.setdefault("forwarded", set())
    for p in items:
        if raw_of.get(p.email.id) in d["forwarded"] and publish_to_modules(p, state):
            forwarded.add(p.email.id)
    return len(items)
