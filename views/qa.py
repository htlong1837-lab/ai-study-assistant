from __future__ import annotations

import hashlib
import re
from uuid import uuid4

import streamlit as st

from core import config
from core.llm_client import LLMClient, get_client
from modules.qa import QAService
from modules.qa.loader import load_document_bytes
from modules.qa.messages import rejection_message
from modules.qa.reader.component import render_reader
from modules.qa.reader.threads import ThreadStore, export_markdown


def _configured_key() -> str:
    """Khóa theo cấu hình chung (.env: <LLM_PROVIDER>_API_KEY), dự phòng st.secrets."""
    name = f"{config.env('LLM_PROVIDER', 'gemini').upper()}_API_KEY"
    value = config.env(name).strip()
    if value:
        return value
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


def _client() -> LLMClient:
    """Dùng LLM_PROVIDER/LLM_MODEL chung; khóa nhập trong phiên được ưu tiên."""
    base = get_client()
    return LLMClient(
        provider=base.provider,
        model=base.model,
        api_key=st.session_state.get("qa_api_key", "").strip() or _configured_key(),
    )


def _clear_key() -> None:
    st.session_state.pop("qa_api_key", None)
    st.session_state.pop("qa_api_key_input", None)
    st.session_state["qa_key_cleared"] = True


def _safe_error(error: Exception) -> str:
    message = str(error)
    key = st.session_state.get("qa_api_key", "")
    if key:
        message = message.replace(key, "[đã ẩn]")
    return re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[đã ẩn khóa]", message)


st.title("💬 Đọc và hỏi đáp tài liệu")
st.caption(
    "Tải tài liệu lên, đọc theo trang, bôi đen đoạn cần hỏi hoặc đặt câu hỏi cho toàn tài liệu."
)
key_input = st.text_input(
    "Gemini API key (chỉ lưu trong phiên)", type="password", key="qa_api_key_input"
)
if key_input:
    st.session_state["qa_api_key"] = key_input
    st.session_state.pop("qa_key_cleared", None)
elif "qa_api_key" not in st.session_state and not st.session_state.get(
    "qa_key_cleared", False
):
    st.session_state["qa_api_key"] = _configured_key()
api_key = st.session_state.get("qa_api_key", "")
if api_key:
    st.button("Xóa API key khỏi phiên", key="qa_clear_api_key", on_click=_clear_key)

uploaded = st.file_uploader(
    "Chọn PDF, TXT hoặc Markdown", type=["pdf", "txt", "md"], key="qa_upload"
)
if uploaded is not None:
    try:
        raw = uploaded.getvalue()
        document = load_document_bytes(uploaded.name, raw)
        file_hash = hashlib.sha256(raw).hexdigest()
        if st.session_state.get("qa_document_hash") != file_hash:
            st.session_state["qa_document"] = document
            st.session_state["qa_document_hash"] = file_hash
            st.session_state["qa_pdf_bytes"] = (
                raw if uploaded.name.lower().endswith(".pdf") else None
            )
            st.session_state.pop("qa_reader_sent_doc_id", None)
            st.session_state["qa_threads"] = {}
            st.session_state["qa_seen_events"] = []
            st.session_state["qa_answer_cache"] = {}
    except Exception as exc:
        st.error(f"Không thể mở tài liệu: {_safe_error(exc)}")

document = st.session_state.get("qa_document")
if document is None:
    st.info("Tải tệp lên để bắt đầu đọc. Chưa nhập key vẫn có thể mở và đọc tài liệu.")
    st.stop()

empty_pages = sum(len(p.text.strip()) < 20 for p in document.pages)
if document.pages and empty_pages / len(document.pages) > 0.5:
    st.warning(
        "PDF có vẻ là bản scan hoặc thiếu lớp văn bản; hiện chưa có OCR tích hợp."
    )

left, right = st.columns([3, 2], gap="medium")
with left:
    try:
        saved_threads = st.session_state.get("qa_threads", {})
        highlights = [
            {"thread_id": tid, "rects": thread.rects}
            for tid, thread in saved_threads.items()
            if thread.rects
        ]
        event = render_reader(
            document,
            ask_enabled=bool(api_key),
            pdf_bytes=st.session_state.get("qa_pdf_bytes"),
            session_state=st.session_state,
            goto=st.session_state.get("qa_goto"),
            highlights=highlights,
            key="qa_reader_main",
        )
    except Exception as exc:
        st.error(f"Không thể mở reader: {_safe_error(exc)}")
        event = None
with right:
    st.subheader("Trao đổi về tài liệu")
    if not api_key:
        st.info("Nhập Gemini API key phía trên để bật chức năng hỏi.")

    if event is not None:
        if event.type == "need_pdf":
            st.rerun()
        if event.type == "open_thread":
            st.session_state["qa_active_thread"] = event.payload.get("thread_id")
            st.rerun()
        if event.type != "ask":
            event = None
    if event is not None:
        if event.type == "ask":
            payload = event.payload
            passage = payload.get("selected_text", "")
            threads = st.session_state.setdefault("qa_threads", {})
            thread = ThreadStore(threads).get_or_create(
                document.doc_id,
                payload["page"],
                passage,
                payload.get("rects", []),
            )
            thread_id = thread.thread_id
            st.session_state["qa_active_thread"] = thread_id
            try:
                action_titles = {
                    "explain": "Giải thích đoạn đã chọn",
                    "simplify": "Đơn giản hóa đoạn đã chọn",
                    "translate": "Dịch đoạn đã chọn",
                    "define": "Định nghĩa thuật ngữ trong đoạn",
                }
                user_message = (
                    payload.get("question", "")
                    if payload["action"] == "custom"
                    else action_titles[payload["action"]]
                )
                with st.spinner("Đang đọc đoạn đã chọn…"):
                    answer = QAService(
                        _client(), st.session_state.setdefault("qa_answer_cache", {})
                    ).ask_about_selection(
                        document,
                        payload["page"],
                        passage,
                        action=payload["action"],
                        custom_question=payload.get("question", ""),
                        thread_history=thread.history[-12:],
                    )
                thread.questions.append(user_message)
                thread.history.extend(
                    [("user", user_message), ("assistant", answer.text)]
                )
                thread.answers.append(answer)
                thread.selection_verified = answer.selection_verified
            except Exception as exc:
                st.error(f"Không thể hỏi tài liệu: {_safe_error(exc)}")
            st.rerun()

    threads = st.session_state.setdefault("qa_threads", {})
    active_id = st.session_state.get("qa_active_thread")
    if threads:
        labels = list(threads)
        active_id = st.selectbox(
            "Đoạn hội thoại",
            labels,
            index=labels.index(active_id) if active_id in labels else 0,
            format_func=lambda tid: (
                f"Trang {threads[tid].page_num}: {threads[tid].selected_text[:45]}…"
            ),
            key="qa_thread_picker",
        )
        st.session_state["qa_active_thread"] = active_id
        active = threads[active_id]
        for question_text, answer in zip(active.questions, active.answers):
            with st.chat_message("user"):
                st.write(question_text)
            with st.chat_message("assistant"):
                st.write(answer.text)
                if answer.background_note:
                    st.info(
                        "Kiến thức bổ sung của AI, không lấy từ tài liệu: "
                        + answer.background_note
                    )
                for citation in answer.citations:
                    if st.button(
                        f"Trang {citation.page_num} · {citation.evidence_text[:90]}",
                        key=f"qa_cite_{answer.answer_id}_{citation.page_num}",
                    ):
                        st.session_state["qa_goto"] = {
                            "page": citation.page_num,
                            "nonce": uuid4().hex,
                            "highlight_text": citation.evidence_text,
                        }
                if not answer.selection_verified:
                    st.caption(
                        "Không khớp chính xác đoạn chọn với văn bản trích xuất; hãy kiểm tra câu trả lời."
                    )
                if answer.status == "rejected":
                    st.warning(rejection_message(answer.rejection_reason))
                if answer.source == "local_fallback":
                    st.warning("Câu trả lời này được tạo bằng fallback cục bộ.")

        followup = st.chat_input("Hỏi tiếp về đoạn này", key="qa_followup")
        if followup and api_key:
            try:
                answer = QAService(
                    _client(), st.session_state.setdefault("qa_answer_cache", {})
                ).ask_about_selection(
                    document,
                    active.page_num,
                    active.selected_text,
                    action="custom",
                    custom_question=followup,
                    thread_history=active.history[-12:],
                )
                active.questions.append(followup)
                active.history.extend([("user", followup), ("assistant", answer.text)])
                active.answers.append(answer)
                st.rerun()
            except Exception as exc:
                st.error(f"Không thể hỏi tiếp: {_safe_error(exc)}")

    with st.expander("Hỏi toàn tài liệu"):
        question = st.text_input("Câu hỏi", key="qa_doc_question")
        if st.button(
            "Gửi câu hỏi",
            key="qa_doc_ask",
            disabled=not (_client().is_configured() and question.strip()),
        ):
            try:
                with st.spinner("Đang tìm trong tài liệu…"):
                    answer = QAService(
                        _client(), st.session_state.setdefault("qa_answer_cache", {})
                    ).ask_question(document, question)
                st.session_state["qa_doc_answer"] = answer
            except Exception as exc:
                st.error(f"Không thể hỏi tài liệu: {_safe_error(exc)}")
        answer = st.session_state.get("qa_doc_answer")
        if answer and answer.doc_id == document.doc_id:
            st.write(answer.text)
            if answer.status == "rejected":
                st.warning(rejection_message(answer.rejection_reason))
            if answer.source == "local_fallback":
                st.warning("Câu trả lời này được tạo bằng fallback cục bộ.")
            if answer.background_note:
                st.info(
                    "Kiến thức bổ sung của AI, không lấy từ tài liệu: "
                    + answer.background_note
                )
            for index, citation in enumerate(answer.citations):
                if st.button(
                    f"Trang {citation.page_num} · {citation.evidence_text[:90]}",
                    key=f"qa_doc_cite_{answer.answer_id}_{index}",
                ):
                    st.session_state["qa_goto"] = {
                        "page": citation.page_num,
                        "nonce": uuid4().hex,
                        "highlight_text": citation.evidence_text,
                    }
                    st.rerun()

    st.download_button(
        "Tải hội thoại Markdown",
        export_markdown(document.filename, threads),
        file_name="hoi-dap-tai-lieu.md",
        mime="text/markdown",
        key="qa_export",
    )
