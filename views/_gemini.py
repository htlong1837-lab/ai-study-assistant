"""Khóa Gemini của người dùng: hướng dẫn lấy khóa và ô nhập khóa (chỉ giữ trong phiên)."""
from __future__ import annotations

import re

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


def looks_like_key(value: str) -> bool:
    return bool(re.fullmatch(r"AIza[0-9A-Za-z_-]{20,}", value.strip()))


def key_controls(ws, typed: str, prefix: str) -> None:
    """Nút lưu khóa ngay dưới ô nhập, hoặc trạng thái "đã lưu" kèm nút quên khóa."""
    saved = saved_key(ws)
    if ws is None or ws.is_guest:
        if typed:
            st.caption("🔒 Đăng nhập Google (nút ở cuối thanh bên) để lưu khóa cho lần sau. "
                       "Hiện khóa chỉ dùng trong phiên này.")
        return
    if typed and typed != saved:
        c_btn, c_note = st.columns([1, 3], vertical_alignment="center")
        if c_btn.button("💾 Lưu khóa", type="primary", key=f"{prefix}_save_key", width="stretch"):
            if looks_like_key(typed):
                ws.write_state("gemini", {"key": typed.strip()})
                st.toast("Đã lưu khóa Gemini cho tài khoản của bạn.", icon="🔑")
                st.rerun()
            else:
                st.error("Khóa này không giống khóa Gemini (thường bắt đầu bằng AIza…). Kiểm tra lại rồi lưu.")
        c_note.caption("Lưu vào tài khoản của bạn để lần sau, ở mọi trang, không phải nhập lại.")
    elif saved:
        c_note, c_btn = st.columns([3, 1], vertical_alignment="center")
        c_note.caption("✅ Đã lưu khóa Gemini cho tài khoản này · dùng cho Hỏi đáp và đọc ảnh thời khoá biểu.")
        if c_btn.button("Quên khóa", key=f"{prefix}_forget_key", width="stretch"):
            ws.clear_state("gemini")
            for k in ("qa_api_key", "qa_api_key_input"):
                st.session_state.pop(k, None)
            st.rerun()


def key_input(session_key: str, label: str = "Gemini API key", ws=None) -> str:
    """Khóa để dùng: khóa người cài app đặt sẵn, khóa đã lưu của tài khoản, hoặc khóa vừa nhập."""
    preset = configured_key()
    if preset:
        return preset
    saved = saved_key(ws)
    typed = st.text_input(label, type="password", key=session_key,
                          placeholder="Đã lưu khóa · để trống để dùng khóa đã lưu" if saved else "AIza…").strip()
    key_controls(ws, typed, session_key)
    value = typed or saved
    if not value:
        how_to_get_key()
    return value
