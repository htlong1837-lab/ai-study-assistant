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
            "Khóa dùng miễn phí trong giới hạn lượt mỗi ngày của Google. Mặc định DP chỉ giữ khóa trong phiên "
            "làm việc này (đóng trang là mất). Nếu bạn đã đăng nhập và tích **Nhớ khóa cho tài khoản này**, "
            "khóa được lưu trong dữ liệu riêng của tài khoản để lần sau khỏi nhập lại. Đừng gửi khóa cho người "
            "khác; muốn thu hồi, vào lại trang AI Studio và xoá khóa."
        )


def saved_key(ws) -> str:
    """Khóa người dùng đã chọn nhớ cho tài khoản của họ (không có thì chuỗi rỗng)."""
    if ws is None or ws.is_guest:
        return ""
    return str((ws.read_state("gemini", {}) or {}).get("key", "") or "")


def remember_box(ws, value: str, key: str) -> None:
    """Ô tích để nhớ khóa theo tài khoản (lưu trong dữ liệu riêng của tài khoản, có sao lưu Drive)."""
    if ws is None or ws.is_guest or not value:
        return
    if st.checkbox("Nhớ khóa cho tài khoản này", key=key, value=saved_key(ws) == value,
                   help="Lưu khóa trong dữ liệu riêng của tài khoản (và bản sao lưu trong Google Drive "
                        "của bạn) để lần sau không phải nhập lại. Bỏ tích để quên khóa."):
        if saved_key(ws) != value:
            ws.write_state("gemini", {"key": value})
    elif saved_key(ws) == value:
        ws.clear_state("gemini")


def key_input(session_key: str, label: str = "Gemini API key (chỉ lưu trong phiên)", ws=None) -> str:
    """Khóa để dùng: khóa người cài app đặt sẵn hoặc khóa đã nhớ của tài khoản; không có thì ô nhập kèm
    hướng dẫn lấy khóa."""
    preset = configured_key() or saved_key(ws)
    if preset:
        if saved_key(ws) and not configured_key():
            c_note, c_forget = st.columns([3, 1], vertical_alignment="center")
            c_note.caption("🔑 Đang dùng khóa Gemini đã nhớ cho tài khoản của bạn.")
            if c_forget.button("Quên khóa", key=f"{session_key}_forget"):
                ws.clear_state("gemini")
                st.rerun()
        return preset
    value = st.text_input(label, type="password", key=session_key, placeholder="AIza…").strip()
    if value:
        remember_box(ws, value, key=f"{session_key}_remember")
    else:
        how_to_get_key()
    return value
