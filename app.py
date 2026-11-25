"""Điểm vào ứng dụng: streamlit run app.py"""

import streamlit as st

from views import _ui

st.set_page_config(page_title="DP · Daily Planner", page_icon=str(_ui.FAVICON), layout="wide")
_ui.apply()

pages = [
    st.Page("views/home.py", title="Hôm nay", icon=":material/wb_sunny:", default=True),
    st.Page("views/scheduler.py", title="Lập lịch & nhắc nhở", icon=":material/calendar_month:"),
    st.Page("views/extraction.py", title="Trích xuất bài tập", icon=":material/task_alt:"),
    st.Page("views/email_security.py", title="Hộp thư", icon=":material/inbox:"),
    st.Page("views/qa.py", title="Hỏi đáp tài liệu", icon=":material/forum:"),
]

selected_page = st.navigation(pages)
current_page = selected_page.url_path
previous_page = st.session_state.get("app_current_page")
if previous_page == "qa" and current_page != "qa":
    st.session_state.pop("qa_api_key", None)
    st.session_state.pop("qa_api_key_input", None)
st.session_state["app_current_page"] = current_page
_ui.intro(current_page or "home")
selected_page.run()
