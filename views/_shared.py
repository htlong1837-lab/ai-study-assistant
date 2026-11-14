"""Thành phần giao diện dùng chung giữa các trang."""
import streamlit as st

from core.llm_client import get_client


def llm_status() -> bool:
    """Hiện trạng thái LLM; trả True nếu dùng được."""
    client = get_client()
    reason = client.not_configured_reason()
    if reason:
        st.warning(f"Chức năng AI đang tắt. {reason}", icon="⚠️")
        return False
    st.success(f"LLM sẵn sàng: {client.provider} / {client.model}", icon="✅")
    return True


def module_header(title: str, owner: str, inputs: str, outputs: str) -> None:
    st.title(title)
    st.caption(f"Phụ trách: **{owner}** · Trạng thái: đang phát triển")
    c1, c2 = st.columns(2)
    c1.markdown(f"**Đầu vào:** {inputs}")
    c2.markdown(f"**Đầu ra:** {outputs}")
    st.info("Đang dùng dữ liệu giả từ `core/mocks.py`.", icon="🧪")
