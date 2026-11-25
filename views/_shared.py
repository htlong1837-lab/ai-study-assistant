"""Thành phần giao diện dùng chung giữa các trang."""
from html import escape

import streamlit as st

from core.llm_client import get_client


def llm_status() -> bool:
    """Hiện trạng thái LLM; trả True nếu dùng được."""
    client = get_client()
    reason = client.not_configured_reason()
    if reason:
        st.warning(f"Chức năng AI đang tắt. {reason}", icon="⚠️")
        return False
    st.success(f"AI sẵn sàng · {client.model}", icon="✅")
    return True


OWNER_COLOR = {"A": "#4D96FF", "B": "#FFB84C", "C": "#F07167", "D": "#00AFB9"}


def module_header(title: str, subtitle: str, code: str) -> None:
    """Tiêu đề trang: biểu tượng trong ô màu theo module (``code`` A–D chỉ để chọn màu), dòng phụ
    mô tả trang cho người dùng."""
    icon, _, name = title.partition(" ")
    color = OWNER_COLOR.get(code, "#F07167")
    st.html(f'<div class="nh-head"><div class="ic" style="background:{color}22">{icon}</div>'
            f'<div><h1>{escape(name)}</h1><p>{escape(subtitle)}</p></div></div>')
