import streamlit as st

from core import mocks
from views._shared import llm_status, module_header

module_header("💬 Hỏi đáp tài liệu", "Nam (A)",
              "SafeAttachment (từ D)", "ParsedDocument (cho B), câu trả lời có trích trang")
llm_status()

st.subheader("Tài liệu đã đọc (mẫu)")
for doc in mocks.documents():
    with st.expander(f"{doc.filename} · {len(doc.pages)} trang"):
        for p in doc.pages:
            st.markdown(f"**Trang {p.number}:** {p.text}")
