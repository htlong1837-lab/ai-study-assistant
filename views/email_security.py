import pandas as pd
import streamlit as st

from core import mocks
from core.contracts import SafetyStatus
from modules.email_security import approve_suspicious, process_email
from views._shared import llm_status, module_header

module_header(
    "🛡️ Email & bảo mật",
    "Hoàng Minh (D)",
    "File .eml",
    "ClassifiedEmail (cho B), SafeAttachment (cho A)",
)
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

# ---- Tải file .eml thật ----
uploaded_files = st.file_uploader(
    "Tải lên file .eml để kiểm tra",
    type=["eml"],
    accept_multiple_files=True,
)
if uploaded_files and st.button("Xử lý file tải lên"):
    known_ids = {p.email.id for p in processed_items}
    added = 0
    for f in uploaded_files:
        p = process_email(f.read())
        if p.email.id in known_ids:  # tránh nạp trùng khi bấm nhiều lần
            continue
        processed_items.append(p)
        known_ids.add(p.email.id)
        added += 1
    st.session_state["flash"] = (
        f"Đã nạp {added} email mới." if added else "Các email này đã có trong danh sách."
    )
    st.rerun()

if not processed_items:
    st.info("Chưa có email nào. Hãy tải lên file .eml.")
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
    # TODO: gọi Module B (p.email) và Module A (p.safe_attachments) tại đây.
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
st.subheader("Hộp thư")
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
    st.write(f"📎 **File đính kèm:** {len(findings)} file, sẽ chuyển sau khi bạn duyệt email")
else:
    st.write("📎 **File đính kèm:** không có")

# ---- Nút duyệt theo trạng thái an toàn ----
st.divider()
if e.id in st.session_state["forwarded"]:
    st.success("✅ Đã chuyển sang Module B/A.")

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
        if st.button("➡️ Chuyển sang B/A", key=f"fwd_{e.id}", type="primary"):
            do_forward(selected_p)
            st.rerun()

else:  # SAFE
    if selected_p.can_forward:
        if st.button("✅ Duyệt & chuyển sang B/A", key=f"fwd_{e.id}", type="primary"):
            do_forward(selected_p)
            st.rerun()
    else:
        st.error("Email không đủ điều kiện chuyển tiếp.")