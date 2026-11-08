from __future__ import annotations

import os
from pathlib import Path

try:  # pragma: no cover - optional dependency in environments without Streamlit
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None  # type: ignore[assignment]

from document_parser import parse_document
from errors import LLMUnavailableError, MissingAPIKeyError
from qa_service import QAService

# ---------------------------------------------------------------------------
# Model catalogue
# ---------------------------------------------------------------------------
_MODEL_OPTIONS: list[tuple[str, str]] = [
    # (display_label, model_id)
    ("🔴 gemini-4-argon — Flagship Reasoning (Mạnh nhất, cần tài khoản trả phí)", "gemini-4-argon"),
    ("🟠 gemini-3.8-flash — High-Intelligence & Fast (cần tài khoản trả phí)", "gemini-3.8-flash"),
    ("🟢 gemini-2.5-flash — Miễn phí / Free Tier (Cân bằng & Mạnh)", "gemini-2.5-flash"),
    ("🟢 gemini-2.0-flash — Miễn phí / Free Tier (Tốc độ cao)", "gemini-2.0-flash"),
    ("🟢 gemini-1.5-flash — Miễn phí / Free Tier (Dự phòng)", "gemini-1.5-flash"),
]
_MODEL_LABELS = [label for label, _ in _MODEL_OPTIONS]
_MODEL_IDS = {label: mid for label, mid in _MODEL_OPTIONS}
_DEFAULT_MODEL_LABEL = _MODEL_LABELS[2]  # gemini-2.5-flash as safe default


# ---------------------------------------------------------------------------
# Key resolution helpers
# ---------------------------------------------------------------------------

def _resolve_api_key(user_input: str) -> str | None:
    """Return the effective API key: user-supplied > host env/secrets > None."""
    key = (user_input or "").strip()
    if key:
        return key
    # Host-level defaults (server env / Streamlit Cloud secrets)
    for env_var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(env_var, "").strip()
        if value:
            return value
    if st is not None:
        for secret_key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            try:
                value = str(st.secrets.get(secret_key, "")).strip()
                if value:
                    return value
            except Exception:
                pass
    return None


def _key_badge(user_input: str) -> tuple[str, str | None]:
    """Return (badge_markdown, effective_key)."""
    key = _resolve_api_key(user_input)
    user_provided = bool((user_input or "").strip())
    if key and user_provided:
        badge = "🟢 Đang sử dụng **API Key cá nhân** của bạn"
    elif key:
        badge = "🔵 Đang sử dụng **API Key mặc định** của hệ thống"
    else:
        badge = "🟡 Chưa có API Key — vui lòng nhập để hỏi câu hỏi"
    return badge, key


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar() -> tuple[str | None, str]:
    """Render the sidebar and return (effective_api_key, selected_model_id)."""
    if st is None:
        return None, "gemini-2.5-flash"

    st.sidebar.title("⚙️ Cài đặt")

    # --- API Key section ---
    with st.sidebar.expander("❓ API Key là gì? Cách lấy key miễn phí", expanded=False):
        st.markdown(
            """
**API Key** giống như một *chìa khoá điện tử* giúp ứng dụng kết nối tới mô hình AI của Google
để đọc và phân tích tài liệu của bạn.

**Cách lấy key hoàn toàn miễn phí (không cần thẻ ngân hàng):**

1. Truy cập [Google AI Studio](https://aistudio.google.com/)
2. Đăng nhập bằng tài khoản **Gmail** bất kỳ
3. Chọn **Get API key → Create API key**
4. Sao chép và dán vào ô bên dưới

> **Để trống cũng được** — ứng dụng sẽ tự động dùng API key mặc định của hệ thống nếu có.
"""
        )

    user_key_input: str = st.sidebar.text_input(
        "Gemini API key (tùy chọn)",
        type="password",
        help="Để trống nếu muốn dùng API key mặc định của hệ thống",
        key="sidebar_api_key_input",
        placeholder="Dán API key của bạn vào đây…",
    )

    badge, effective_key = _key_badge(user_key_input)
    st.sidebar.caption(badge)

    col1, col2 = st.sidebar.columns(2)
    if col1.button("🔍 Kiểm tra key", use_container_width=True):
        _check_api_key(effective_key)
    if col2.button("🗑️ Xóa key", use_container_width=True):
        st.session_state.pop("sidebar_api_key_input", None)
        st.rerun()

    st.sidebar.divider()

    # --- Model selection ---
    st.sidebar.markdown("**🤖 Chọn mô hình AI**")
    selected_label: str = st.sidebar.selectbox(
        "Mô hình AI ưu tiên",
        options=_MODEL_LABELS,
        index=_MODEL_LABELS.index(_DEFAULT_MODEL_LABEL),
        label_visibility="collapsed",
    )
    st.sidebar.caption(
        "💡 Các mô hình **Miễn phí** dùng được ngay với key Google AI Studio thông thường. "
        "Mô hình **Mạnh nhất** yêu cầu tài khoản Google đã bật thanh toán."
    )

    selected_model = _MODEL_IDS[selected_label]
    return effective_key, selected_model


def _check_api_key(key: str | None) -> None:
    if st is None:
        return
    if not key:
        st.sidebar.warning("⚠️ Không có API key nào để kiểm tra.")
        return
    try:
        from google import genai  # type: ignore[import-untyped]
        client = genai.Client(api_key=key, http_options={"timeout": 10_000})
        client.models.count_tokens(model="gemini-2.0-flash", contents="ping")
        st.sidebar.success("✅ API key hợp lệ!")
    except Exception as exc:
        st.sidebar.error(f"❌ Key không hợp lệ hoặc hết hạn: {exc}")


# ---------------------------------------------------------------------------
# Citation links
# ---------------------------------------------------------------------------

def _render_citation_links(answer, page_lookup: dict) -> None:  # type: ignore[no-untyped-def]
    if st is None:
        return
    for index, citation in enumerate(answer.citations):
        st.button(
            f"[{citation.page_num}]",
            key=f"citation_{answer.answer_id}_{index}",
            on_click=lambda page=citation.page_num: page_lookup.__setitem__(
                "selected_page", page
            ),
        )


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    if st is None:
        raise RuntimeError("Streamlit is not installed in this environment.")

    st.set_page_config(page_title="Document Q&A", page_icon="📄", layout="wide")
    st.title("📄 Document Q&A via Gemini AI")

    effective_key, selected_model = _render_sidebar()

    # --- File upload ---
    uploaded_file = st.file_uploader(
        "Upload a PDF document",
        type=["pdf"],
        help="Drag and drop a PDF or browse your files to begin.",
    )

    if uploaded_file is not None:
        temp_dir = Path(".tmp_uploads")
        temp_dir.mkdir(exist_ok=True)
        upload_path = temp_dir / uploaded_file.name

        try:
            with st.spinner("Đang xử lý tài liệu PDF…"):
                upload_path.write_bytes(uploaded_file.getvalue())
                st.session_state["document"] = parse_document(
                    str(upload_path), uploaded_file.name
                )
            st.success("✅ Tài liệu đã được tải lên thành công.")
        except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
            st.error(
                f"❌ Không thể phân tích tài liệu PDF. "
                f"Vui lòng tải lên file PDF hợp lệ. Chi tiết: {exc}"
            )
            st.session_state.pop("document", None)
            return

    if "document" not in st.session_state:
        st.info("📂 Hãy tải lên một file PDF để bắt đầu.")
        return

    document = st.session_state["document"]

    # --- Question input ---
    question = st.text_input(
        "💬 Đặt câu hỏi về tài liệu",
        placeholder="Nhập câu hỏi của bạn tại đây…",
    )

    ask_disabled = not bool(effective_key)
    if ask_disabled:
        st.warning(
            "🟡 Vui lòng nhập API key ở sidebar (hoặc cấu hình key mặc định cho hệ thống) "
            "để có thể đặt câu hỏi."
        )

    if st.button("🔍 Hỏi", disabled=ask_disabled) and question:
        try:
            with st.spinner(f"Đang tạo câu trả lời bằng **{selected_model}**…"):
                service = QAService(api_key=effective_key)
                service.llm_client.model = selected_model
                answer = service.ask_question(document, question, reference_material=True)
            st.session_state["answer"] = answer
        except MissingAPIKeyError as exc:
            st.error(f"🔑 {exc}")
            return
        except LLMUnavailableError as exc:
            st.error(f"🤖 Không thể kết nối tới bất kỳ mô hình AI nào: {exc}")
            return
        except ValueError as exc:
            st.error(f"❌ Câu hỏi không thể được trả lời: {exc}")
            return
        except RuntimeError as exc:
            st.error(f"⚠️ Lỗi khi gọi LLM: {exc}")
            return
        except Exception as exc:  # pragma: no cover
            st.error(
                "❌ Đã xảy ra sự cố khi liên hệ với AI hoặc xác thực câu trả lời. "
                f"Chi tiết: {exc}"
            )
            return

    if "answer" in st.session_state:
        answer = st.session_state["answer"]

        # --- Source transparency banner (Task 0.5) ---
        if answer.source == "local_fallback":
            st.warning(
                "⚠️ **Kết quả dự phòng (Fallback):** Đây là kết quả trích xuất từ khóa nội bộ, "
                "không phải câu trả lời do AI sinh ra. "
                "Vui lòng kiểm tra lại kết nối mạng hoặc API key của bạn."
            )
        elif answer.source == "cache":
            st.caption("⚡ Trả lời từ bộ nhớ đệm (Cache)")

        if answer.model_used:
            st.caption(f"🤖 Mô hình AI: **{answer.model_used}**")

        st.subheader("💡 Câu trả lời")
        st.write(answer.text)

        if answer.citations:
            st.subheader("📎 Trích dẫn nguồn")
            for citation in answer.citations:
                if st.button(
                    f"Trang {citation.page_num}",
                    key=f"page_button_{answer.answer_id}_{citation.page_num}",
                ):
                    st.session_state["selected_page"] = citation.page_num

        selected_page = st.session_state.get("selected_page")
        if selected_page is None and answer.citations:
            selected_page = answer.citations[0].page_num
        if selected_page is not None:
            page = document.page_by_number(selected_page)
            if page is not None:
                st.subheader(f"📄 Nội dung Trang {selected_page}")
                st.text_area("Nội dung trang", value=page.text, height=220)


if __name__ == "__main__":
    main()
