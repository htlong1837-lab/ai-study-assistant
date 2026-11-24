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


OWNER_COLOR = {"A": "#4D96FF", "B": "#FFB84C", "C": "#F07167", "D": "#00AFB9"}


def module_header(title: str, owner: str, inputs: str, outputs: str) -> None:
    """Tiêu đề trang: biểu tượng trong ô màu theo module, dòng phụ ghi đầu vào → đầu ra."""
    icon, _, name = title.partition(" ")
    code = owner.strip()[-2:-1] if owner.strip().endswith(")") else ""
    color = OWNER_COLOR.get(code, "#F07167")
    st.html(f'<div class="nh-head"><div class="ic" style="background:{color}22">{icon}</div>'
            f'<div><h1>{name}</h1><p>Phụ trách: {owner} · {inputs} → {outputs}</p></div></div>')
