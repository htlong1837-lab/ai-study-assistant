from __future__ import annotations

import os

import streamlit as st

from core import mocks
from core.llm_client import LLMClient
from modules.qa import QAService


def _configured_key() -> str:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        try:
            value = str(st.secrets.get(name, "")).strip()
        except Exception:
            value = ""
        if value:
            return value
    return ""


st.title("💬 Hỏi đáp tài liệu")
st.caption("Bản demo dùng ParsedDocument mẫu; file thật sẽ chỉ được nhận qua cổng SafeAttachment của Module D.")

api_key = st.text_input("Gemini API key", type="password", key="qa_api_key")
effective_key = api_key.strip() or _configured_key()
if not effective_key:
    st.info("Nhập API key để bật chức năng hỏi đáp.")

documents = mocks.documents()
selected_id = st.selectbox(
    "Tài liệu mẫu",
    options=[doc.doc_id for doc in documents],
    format_func=lambda doc_id: next(doc.filename for doc in documents if doc.doc_id == doc_id),
    key="qa_document_id",
)
document = next(doc for doc in documents if doc.doc_id == selected_id)
st.caption(f"{len(document.pages)} trang · Dữ liệu mẫu từ hợp đồng dùng chung")

question = st.text_input("Câu hỏi về tài liệu")
if st.button("Hỏi", disabled=not bool(effective_key and question.strip())):
    client = LLMClient(provider="gemini", model="gemini-2.5-flash", api_key=effective_key)
    try:
        answer = QAService(client).ask_question(document, question)
        st.session_state["qa_answer"] = answer
    except Exception:
        st.error("Không thể tạo câu trả lời có trích dẫn hợp lệ. Kiểm tra key và thử lại.")

answer = st.session_state.get("qa_answer")
if answer is not None and answer.doc_id == document.doc_id:
    st.subheader("Câu trả lời")
    st.write(answer.text)
    for citation in answer.citations:
        st.caption(f"Trang {citation.page_num}: {citation.evidence_text}")
