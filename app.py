"""Điểm vào ứng dụng: streamlit run app.py"""

import streamlit as st

st.set_page_config(page_title="Trợ lý AI học tập", page_icon="📚", layout="wide")

pages = {
    "Tổng quan": [
        st.Page("views/home.py", title="Trang chủ", icon="🏠", default=True),
    ],
    "Luồng xử lý": [
        st.Page("views/email_security.py", title="Email & bảo mật", icon="🛡️"),
        st.Page("views/extraction.py", title="Trích xuất bài tập", icon="📝"),
        st.Page("views/scheduler.py", title="Lập lịch & nhắc nhở", icon="📅"),
        st.Page("views/qa.py", title="Hỏi đáp tài liệu", icon="💬"),
    ],
}

selected_page = st.navigation(pages)
current_page = selected_page.url_path
previous_page = st.session_state.get("app_current_page")
if previous_page == "qa" and current_page != "qa":
    st.session_state.pop("qa_api_key", None)
    st.session_state.pop("qa_api_key_input", None)
st.session_state["app_current_page"] = current_page
selected_page.run()
