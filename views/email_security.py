from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from core import mocks
from core.contracts import SafetyStatus
from modules.email_security import approve_suspicious, process_email
from modules.email_security.handoff import publish_to_modules
from modules.email_security import gmail
from modules.email_security.mailbox import MailboxError, fetch_recent
from views._shared import llm_status, module_header


def get_verified_emails() -> list:
    """Lấy danh sách ClassifiedEmail đã duyệt qua Module D."""
    value = st.session_state.get("verified_emails", {})
    return list(value.values()) if isinstance(value, dict) else value


def get_safe_attachments() -> list:
    """Lấy danh sách SafeAttachment đã duyệt qua Module D."""
    value = st.session_state.get("safe_attachments", {})
    return list(value.values()) if isinstance(value, dict) else value


module_header("📬 Hộp thư", "D")
llm_status()

ICON = {
    SafetyStatus.SAFE: "🟢 an toàn",
    SafetyStatus.SUSPICIOUS: "🟡 nghi ngờ",
    SafetyStatus.MALICIOUS: "🔴 độc",
}

# ---- Trạng thái phiên (Streamlit chạy lại script sau mỗi lần bấm) ----
if "processed_list" not in st.session_state:
    raws = mocks.emails_raw() if hasattr(mocks, "emails_raw") else []
    st.session_state["processed_list"] = [process_email(raw) for raw in raws]
st.session_state.setdefault("forwarded", set())  # id email đã chuyển sang B/A

processed_items = st.session_state["processed_list"]

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

DEMO_DIR = Path(__file__).resolve().parents[1] / "data" / "demo"


def _ingest(raws: list[bytes]) -> None:
    known_ids = {p.email.id for p in processed_items}
    added = 0
    for raw in raws:
        p = process_email(raw)
        if p.email.id in known_ids:  # tránh nạp trùng khi bấm nhiều lần
            continue
        processed_items.append(p)
        known_ids.add(p.email.id)
        added += 1
    st.session_state["flash"] = (
        f"Đã nạp {added} email mới." if added else "Các email này đã có trong danh sách."
    )
    st.rerun()


GMAIL_DAYS = 14


def _google_configured() -> bool:
    """App đã có khóa "Đăng nhập bằng Google" trong .streamlit/secrets.toml chưa."""
    try:
        auth = st.secrets.get("auth")
    except Exception:  # noqa: BLE001 — chưa có file secrets
        return False
    return bool(auth) and "google" in auth


def _google_user():
    """``st.user`` nếu đang đăng nhập Google, ngược lại ``None``."""
    try:
        return st.user if st.user.is_logged_in else None
    except Exception:  # noqa: BLE001 — chưa cấu hình đăng nhập
        return None


def _sync_google(user) -> None:
    token = (getattr(user, "tokens", None) or {}).get("access", "")
    with st.spinner("Đang lấy thư Gmail…"):
        try:
            raws = gmail.fetch_recent(token, days=GMAIL_DAYS)
        except gmail.GmailError as exc:
            st.session_state["mailbox_error"] = str(exc)
            st.session_state["gmail_synced"] = True
            st.rerun()
    st.session_state["gmail_synced"] = True
    if raws:
        _ingest(raws)
    st.session_state["flash"] = f"Không có thư nào trong {GMAIL_DAYS} ngày gần đây."
    st.rerun()


def _sync_imap(address: str, password: str, host: str) -> None:
    with st.spinner(f"Đang lấy thư của {address}…"):
        try:
            raws = fetch_recent(address, password, host=host or None, days=GMAIL_DAYS)
        except MailboxError as exc:
            st.session_state["mailbox_error"] = str(exc)
            st.rerun()
    if raws:
        _ingest(raws)
    st.session_state["flash"] = f"Không có thư nào trong {GMAIL_DAYS} ngày gần đây."
    st.rerun()


# ---- Đăng nhập bằng Google (lối chính) ----
if "mailbox_error" in st.session_state:
    st.error(st.session_state.pop("mailbox_error"), icon="🔐")
user = _google_user()
if user is not None:
    if not st.session_state.get("gmail_synced"):  # vừa đăng nhập: tự lấy thư luôn
        _sync_google(user)
    c_who, c_sync, c_out = st.columns([3, 1, 1], vertical_alignment="center")
    c_who.html(f'<div class="nh-chip" style="margin:0">📬 <b>{escape(str(user.get("email", "")))}</b>'
               f'&nbsp;· {GMAIL_DAYS} ngày gần đây</div>')
    if c_sync.button("🔄 Lấy thư mới", type="primary", width="stretch"):
        _sync_google(user)
    if c_out.button("Đăng xuất", width="stretch"):
        st.session_state.pop("gmail_synced", None)
        st.logout()
else:
    with st.container(border=True, key="google_card"):
        st.html('<div class="nh-login"><div class="i">📬</div><b>Kết nối Gmail</b></div>')
        if st.button("Đăng nhập bằng Google", key="google_login", icon=":material/login:"):
            if _google_configured():
                st.session_state.pop("gmail_synced", None)
                st.login("google")
            else:
                st.session_state["mailbox_error"] = (
                    "App chưa được bật đăng nhập Google. Người cài app làm một lần theo "
                    "docs/dang-nhap-google.md.")
                st.rerun()
        st.caption("Nhịp chỉ đọc thư và không bao giờ thấy mật khẩu của bạn.")

with st.expander("Cách khác: email Yahoo/iCloud, file .eml, email mẫu"):
    with st.form("mailbox_login", border=False):
        c_mail, c_pw, c_host = st.columns([2, 2, 1.4])
        address = c_mail.text_input("Email", placeholder="ban@yahoo.com")
        password = c_pw.text_input("Mật khẩu ứng dụng", type="password")
        host = c_host.text_input("Máy chủ IMAP", placeholder="tự nhận")
        if st.form_submit_button("Kết nối"):
            _sync_imap(address, password, host)
    st.divider()
    c_up, c_demo = st.columns([3, 1], vertical_alignment="bottom")
    uploaded_files = c_up.file_uploader("File .eml", type=["eml"], accept_multiple_files=True)
    demo_files = sorted(DEMO_DIR.glob("*.eml"))
    if demo_files and c_demo.button(
        "✨ Email mẫu", help="3 email tự soạn: giao bài kèm đề PDF, dời hạn, lừa đảo."
    ):
        _ingest([f.read_bytes() for f in demo_files])
    if uploaded_files and st.button("Kiểm tra các file này", type="primary"):
        _ingest([f.read() for f in uploaded_files])

if not processed_items:
    st.html(
        '<div style="text-align:center;padding:42px 20px;border-radius:22px;background:#fff;'
        'box-shadow:0 6px 20px rgba(0,175,185,.10)"><div style="font-size:44px">📭</div>'
        '<div style="font-weight:700;font-size:17px;color:#2B2D42;margin-top:6px">Hộp thư đang trống</div></div>'
    )
    st.stop()


def forward_state(p) -> str:
    mail = p.email
    if mail.id in st.session_state["forwarded"]:
        return "đã chuyển"
    if mail.safety is SafetyStatus.MALICIOUS:
        return "chặn"
    if mail.safety is SafetyStatus.SUSPICIOUS:
        return "đã duyệt" if p.user_approved else "chờ duyệt"
    return "có" if p.can_forward else "chặn"


def do_forward(p) -> None:
    """Điểm chuyển tiếp duy nhất; luôn kiểm tra lại trước khi chuyển."""
    mail = p.email
    if mail.safety is SafetyStatus.MALICIOUS:
        return
    if mail.safety is SafetyStatus.SUSPICIOUS and not p.user_approved:
        return
    if not p.can_forward:
        return
    if not publish_to_modules(p, st.session_state):
        st.error("Email chưa vượt qua cổng an toàn hoặc chưa được người dùng duyệt.")
        return
    st.session_state["forwarded"].add(mail.id)


# ---- Tổng quan ----
n_mal = sum(p.email.safety is SafetyStatus.MALICIOUS for p in processed_items)
n_sus = sum(
    p.email.safety is SafetyStatus.SUSPICIOUS and not p.user_approved
    for p in processed_items
)
n_safe = sum(p.email.safety is SafetyStatus.SAFE for p in processed_items)

c1, c2, c3 = st.columns(3)
c1.metric("🟢 An toàn", n_safe)
c2.metric("🟡 Chờ duyệt", n_sus)
c3.metric("🔴 Bị chặn", n_mal)

# ---- Bảng hộp thư ----
st.subheader("Thư đã quét")
df = pd.DataFrame(
    [
        {
            "An toàn": ICON.get(p.email.safety, "Chưa rõ"),
            "Nhãn": p.email.label.value,
            "Người gửi": p.email.sender,
            "Tiêu đề": p.email.subject,
            "Chuyển tiếp": forward_state(p),
            "Tóm tắt": p.email.summary or "",
        }
        for p in processed_items
    ]
)

event = st.dataframe(
    df,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    key="inbox_table",
)

rows = event.selection.rows
if not rows:
    st.info("Chọn một email trong bảng để xem chi tiết và duyệt.")
    st.stop()

row = rows[0]
selected_p = processed_items[row]
e = selected_p.email
state = e.safety

# ---- Chi tiết email ----
st.subheader(f"✉️ {e.subject}")
st.write(f"**Từ:** {e.sender}")
st.write(
    f"**Nhãn đề xuất:** `{e.label.value}` — độ tin cậy {e.label_confidence:.0%} "
    "(AI đề xuất, người dùng quyết định)"
)
if e.summary:
    st.write(f"📝 **Tóm tắt:** {e.summary}")

with st.expander("Nội dung email"):
    st.text(e.body)

if selected_p.url_findings:
    st.write("🔗 **Đường dẫn bóc tách (defanged):**")
    for u in selected_p.url_findings:
        st.code(f"{u.defanged} -> [{u.status.value}]")

findings = selected_p.attachment_findings
if state is SafetyStatus.MALICIOUS and findings:
    st.write("📎 **File đính kèm:** bị chặn cùng email")
elif selected_p.safe_attachments:
    st.write("📎 **File đính kèm:**")
    for a in selected_p.safe_attachments:
        st.code(f"{a.path}\nsha256: {a.sha256}")
elif findings:
    st.write(
        f"📎 **File đính kèm:** {len(findings)} file, sẽ chuyển sau khi bạn duyệt email"
    )
else:
    st.write("📎 **File đính kèm:** không có")

# ---- Nút duyệt theo trạng thái an toàn ----
st.divider()
if e.id in st.session_state["forwarded"]:
    st.success("✅ Đã chuyển sang Trích xuất bài tập và Hỏi đáp tài liệu.")

elif state is SafetyStatus.MALICIOUS:
    st.error("🔴 Email độc hại — đã chặn hoàn toàn, không thể chuyển tiếp.")

elif state is SafetyStatus.SUSPICIOUS:
    st.warning(
        "🟡 Email có dấu hiệu đáng ngờ (hoặc đang ở chế độ rà soát sơ bộ). "
        "Chỉ chuyển tiếp nếu bạn chắc chắn tin tưởng người gửi."
    )
    if not selected_p.user_approved:
        if st.button("Tôi xác nhận muốn chuyển tiếp", key=f"approve_{e.id}"):
            # approve_suspicious trả về đối tượng MỚI → phải ghi đè vào danh sách
            processed_items[row] = approve_suspicious(selected_p)
            st.rerun()
    else:
        st.info("Bạn đã xác nhận email này.")
        if st.button("➡️ Chuyển tiếp", key=f"fwd_{e.id}", type="primary"):
            do_forward(selected_p)
            st.rerun()

else:  # SAFE
    if selected_p.can_forward:
        if st.button("✅ Duyệt & chuyển tiếp", key=f"fwd_{e.id}", type="primary"):
            do_forward(selected_p)
            st.rerun()
    else:
        st.error("Email không đủ điều kiện chuyển tiếp.")
