import streamlit as st

from core import mocks
from core.contracts import TaskStatus, can_forward
from views._shared import llm_status, module_header

module_header("📝 Trích xuất bài tập", "Trường (B)",
              "ClassifiedEmail an toàn (từ D), ParsedDocument (từ A)",
              "Task trạng thái đề xuất → người dùng xác nhận")
llm_status()

st.subheader("Email được phép đọc")
for e in mocks.emails():
    if can_forward(e):
        st.write(f"- **{e.subject}** — {e.summary or e.body[:80]}")

st.subheader("Đề xuất chờ xác nhận")
for t in mocks.tasks():
    if t.status is TaskStatus.PROPOSED:
        st.write(f"- {t.title} · hạn {t.deadline:%d/%m %H:%M} · nguồn `{t.source}` · "
                 f"tin cậy {t.confidence:.0%}")
