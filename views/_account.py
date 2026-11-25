"""Người đang dùng app và dữ liệu riêng của họ (xem ``core.workspace``)."""
from __future__ import annotations

from html import escape

from datetime import datetime, timezone

import streamlit as st

from core import mocks, workspace
from core.workspace import Workspace

# Dữ liệu trong phiên gắn với một người; đổi người thì phải xoá để không lộ sang người sau.
PERSONAL_KEYS = ("processed_list", "forwarded", "verified_emails", "verified_email_ids", "safe_attachments",
                 "verified_documents", "approved_suspicious_email_ids", "sched", "gmail_synced", "mailbox_error",
                 "qa_document", "qa_pdf_bytes", "qa_threads", "qa_selected_hash", "extract_flash", "flash",
                 "_raw_of", "qa_document_hash", "qa_api_key", "qa_api_key_input", "tt_img")


def google_configured() -> bool:
    """App đã có khóa "Đăng nhập bằng Google" trong .streamlit/secrets.toml chưa."""
    try:
        auth = st.secrets.get("auth")
    except Exception:  # noqa: BLE001 — chưa có file secrets
        return False
    return bool(auth) and "google" in auth


def google_user():
    """``st.user`` nếu đang đăng nhập Google, ngược lại ``None``."""
    try:
        return st.user if st.user.is_logged_in else None
    except Exception:  # noqa: BLE001 — chưa cấu hình đăng nhập
        return None


def _session_id() -> str:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx()
        return ctx.session_id if ctx else "khach"
    except Exception:  # noqa: BLE001
        return "khach"


def _seed_guest(repo) -> None:
    """Dữ liệu mẫu cho khách dùng thử: nạp từ core.mocks khi CSDL của phiên còn trống."""
    existing = repo.list_tasks()
    if not existing:
        for t in mocks.tasks():
            repo.create_task({
                "id": t.id,
                "title": t.title,
                "course": t.course,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "estimated_hours": t.estimated_hours,
                "priority": t.priority.value,
                "confidence": t.confidence,
                "status": t.status.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            repo.add_sources(t.id, [{
                "source": t.source,
                "field": "title",
                "quote": t.title,
                "kind": "mock",
            }])
            repo.save_assignment_details(t.id, {
                "raw_deadline_text": f"{t.deadline:%d/%m %H:%M}" if t.deadline else None,
                "submission_platform": "LMS Đại học Bách Khoa",
                "submission_format": [".pdf", ".zip"],
                "naming_convention": "MSSV_HoTen_BaiTap.zip",
                "grading_criteria": ["Đúng yêu cầu đề bài", "Báo cáo rõ ràng, mạch lạc"],
                "assumptions": ["Giờ mặc định là 23:59 nếu không ghi rõ"],
            })


def current() -> Workspace:
    """Không gian dữ liệu của người đang dùng: tài khoản Google, hoặc khách theo phiên."""
    user = google_user()
    email = str(user.get("email", "") or "") if user is not None else ""
    ws = workspace.for_user(email) if email else workspace.for_guest(_session_id())
    owner = ws.email or f"guest:{ws.root.name}"
    if st.session_state.get("_ws_owner") not in (None, owner):
        for k in PERSONAL_KEYS:
            st.session_state.pop(k, None)
    st.session_state["_ws_owner"] = owner
    if not ws.is_guest and not st.session_state.get("_drive_checked"):
        st.session_state["_drive_checked"] = True
        _drive("restore", ws)  # máy chủ mới khởi động lại: lấy lại lịch từ Drive của người dùng
    if not ws.is_guest and "processed_list" not in st.session_state:
        from views import _inbox

        with st.spinner("Đang mở lại hộp thư của bạn…"):
            _inbox.restore(ws, st.session_state)  # vào thẳng trang nào cũng có thư và tài liệu đã duyệt
    if ws.is_guest and not st.session_state.get("_guest_seeded"):
        from db.repository import Repository

        _seed_guest(Repository(ws.db_path))
        st.session_state["_guest_seeded"] = True
    return ws


def access_token() -> str:
    user = google_user()
    return str((getattr(user, "tokens", None) or {}).get("access", "") or "") if user is not None else ""


def _drive(action: str, ws: Workspace) -> None:
    """Khôi phục hoặc sao lưu thư mục dữ liệu qua Google Drive; lỗi chỉ ghi trạng thái, không làm hỏng trang."""
    from datetime import datetime as _dt

    from modules.storage import drive_sync

    token = access_token()
    if not token:
        return
    try:
        if action == "restore":
            if drive_sync.restore(ws.root, token):
                st.session_state["_drive_status"] = ("ok", f"Đã lấy lịch từ Google Drive lúc {_dt.now():%H:%M}")
        elif drive_sync.save(ws.root, token):
            st.session_state["_drive_status"] = ("ok", f"Đã lưu vào Google Drive lúc {_dt.now():%H:%M}")
    except drive_sync.DriveError as exc:
        st.session_state["_drive_status"] = ("warn", f"Chưa lưu được vào Drive: {exc}")
    except Exception as exc:  # noqa: BLE001 — mạng, zip hỏng…: không chặn người dùng
        st.session_state["_drive_status"] = ("warn", f"Chưa lưu được vào Drive ({type(exc).__name__}).")


def backup() -> None:
    """Gọi sau mỗi lần chạy trang: có gì thay đổi thì lưu lên Drive của người đang đăng nhập."""
    owner = st.session_state.get("_ws_owner", "")
    if owner and not owner.startswith("guest:"):
        _drive("save", workspace.for_user(owner))


NOT_CONFIGURED = ("App chưa được bật đăng nhập Google. Người cài app làm một lần theo "
                  "docs/dang-nhap-google.md.")


def login() -> None:
    """Bắt đầu đăng nhập Google (hoặc báo app chưa bật đăng nhập)."""
    if google_configured():
        st.session_state.pop("gmail_synced", None)
        st.login("google")
    else:
        st.toast(NOT_CONFIGURED, icon="🔐")


def code_version() -> str:
    """Mã commit đang chạy (đọc thẳng .git, không cần lệnh git), để biết máy chủ đã nhận bản mới chưa."""
    from pathlib import Path

    git = Path(__file__).resolve().parents[1] / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[5:]
            ref_file = git / ref
            if ref_file.is_file():
                return ref_file.read_text(encoding="utf-8").strip()[:7]
            for line in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
                if line.endswith(" " + ref):
                    return line[:7]
            return "?"
        return head[:7]
    except OSError:
        return "?"


def sidebar() -> None:
    """Tài khoản ở cuối thanh bên: ảnh, tên, email và nút đăng xuất; khách thì có nút đăng nhập."""
    user = google_user()
    st.sidebar.html(f'<div class="nh-ver">Phiên bản {code_version()}</div>')
    with st.sidebar, st.container(key="acct_box"):
        if user is not None:
            name = str(user.get("name", "") or user.get("email", ""))
            email = str(user.get("email", "") or "")
            pic = str(user.get("picture", "") or "")
            avatar = (f'<img src="{escape(pic)}" alt="" referrerpolicy="no-referrer">' if pic.startswith("https://")
                      else f'<span>{escape(name[:1].upper() or "?")}</span>')
            st.html(f'<div class="nh-acct">{avatar}<div><b>{escape(name)}</b><small>{escape(email)}</small></div></div>')
            kind, text = st.session_state.get("_drive_status", ("", ""))
            if text:
                st.caption(("☁️ " if kind == "ok" else "⚠️ ") + text)
            if st.button("Đăng xuất", key="acct_logout", icon=":material/logout:", width="stretch"):
                for k in PERSONAL_KEYS:
                    st.session_state.pop(k, None)
                st.logout()
        else:
            st.html('<div class="nh-acct guest"><span>👋</span><div><b>Bạn đang dùng thử</b>'
                    '<small>Dữ liệu mẫu, không được lưu lại</small></div></div>')
            if st.button("Đăng nhập bằng Google", key="acct_login", icon=":material/login:", width="stretch"):
                login()
