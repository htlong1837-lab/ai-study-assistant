"""Khóa Gemini của người dùng: hướng dẫn lấy khóa và ô nhập khóa (chỉ giữ trong phiên)."""
from __future__ import annotations

import streamlit as st

from core import config

AI_STUDIO = "https://aistudio.google.com/apikey"


def configured_key() -> str:
    """Khóa người cài app đặt sẵn (.env GEMINI_API_KEY hoặc Secrets trên Cloud)."""
    value = config.env("GEMINI_API_KEY")
    if value:
        return value
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:  # noqa: BLE001 — chưa có secrets
        return ""


def how_to_get_key(expanded: bool = True) -> None:
    """Các bước lấy khóa Gemini miễn phí bằng tài khoản Google của chính người dùng."""
    with st.expander("🔑 Chưa có khóa Gemini? Lấy miễn phí trong 1 phút", expanded=expanded):
        st.markdown(
            f"1. Mở **[Google AI Studio → API keys]({AI_STUDIO})** và đăng nhập bằng tài khoản Google của bạn.\n"
            "2. Bấm **Create API key** (Tạo khóa API). Nếu được hỏi dự án, chọn **Create API key in new project**.\n"
            "3. Bấm biểu tượng sao chép cạnh khóa vừa tạo (khóa bắt đầu bằng `AIza…`).\n"
            "4. Dán vào ô **Gemini API key** ở trên.\n\n"
            "Khóa dùng miễn phí trong giới hạn lượt mỗi ngày của Google. DP chỉ giữ khóa trong phiên làm việc "
            "này (đóng trang là mất), không lưu xuống máy chủ. Đừng gửi khóa cho người khác; muốn thu hồi, vào "
            "lại trang AI Studio và xoá khóa."
        )


def key_input(session_key: str, label: str = "Gemini API key (chỉ lưu trong phiên)") -> str:
    """Khóa để dùng: khóa người cài app đặt sẵn, nếu không có thì ô nhập kèm hướng dẫn lấy khóa."""
    preset = configured_key()
    if preset:
        return preset
    value = st.text_input(label, type="password", key=session_key, placeholder="AIza…").strip()
    if not value:
        how_to_get_key()
    return value
