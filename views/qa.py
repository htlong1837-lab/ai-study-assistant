from __future__ import annotations

import streamlit as st

from core import mocks
from core.llm_client import LLMClient, get_client
from modules.qa import QAService


st.title("💬 Hỏi đáp tài liệu")
st.caption("Bản demo dùng ParsedDocument mẫu; file thật sẽ chỉ được nhận qua cổng SafeAttachment của Module D.")

# Cấu hình chung từ .env (LLM_PROVIDER, LLM_MODEL, <PROVIDER>_API_KEY).
# Ô nhập key chỉ dùng trong phiên, không ghi ra file.
client = get_client()
api_key = st.text_input("API key (tuỳ chọn, chỉ dùng trong phiên này)", type="password", key="qa_api_key")
if api_key.strip():
    client = LLMClient(provider=client.provider, model=client.model, api_key=api_key.strip())
if not client.is_configured():
    st.info(f"Hỏi đáp đang tắt: {client.not_configured_reason()} Nhập API key hoặc điền vào .env.")

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
if st.button("Hỏi", disabled=not (client.is_configured() and question.strip())):
    try:
        answer = QAService(client).ask_question(document, question)
        st.session_state["qa_answer"] = answer
    except ValueError as exc:
        st.session_state.pop("qa_answer", None)
        st.error(f"Không tạo được câu trả lời có trích dẫn hợp lệ: {exc}")
    except Exception:
        st.session_state.pop("qa_answer", None)
        st.error("Gọi LLM thất bại. Kiểm tra key và kết nối mạng rồi thử lại.")

answer = st.session_state.get("qa_answer")
if answer is not None and answer.doc_id == document.doc_id:
    st.subheader("Câu trả lời")
    st.write(answer.text)
    for citation in answer.citations:
        st.caption(f"Trang {citation.page_num}: {citation.evidence_text}")
