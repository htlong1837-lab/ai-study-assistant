import streamlit as st

from core import mocks
from core.contracts import TaskStatus
from core.llm_client import get_client
from modules.email_security.handoff import verified_email_batches
from modules.extraction.extractor import extract_from_email
from views._shared import llm_status, module_header

module_header(
    "📝 Trích xuất bài tập",
    "Trường (B)",
    "ClassifiedEmail đã qua cổng D, ParsedDocument từ A",
    "Đề xuất bài tập → người dùng xác nhận",
)
llm_status()

st.subheader("Email đã được Module D cho phép")
email_batches = verified_email_batches(st.session_state)
results = st.session_state.setdefault("email_extraction_results", {})

if not email_batches:
    st.info(
        "Chưa có email nào được duyệt ở Module D. Hãy xử lý email trong trang Email & bảo mật."
    )
else:
    for email, allow_suspicious in email_batches:
        with st.container(border=True):
            st.write(f"**{email.subject}** — {email.sender}")
            if allow_suspicious:
                st.warning("Email nghi ngờ đã được người dùng xác nhận tại Module D.")
            if email.id not in results and st.button(
                "Phân tích email", key=f"extract_email_{email.id}"
            ):
                try:
                    with st.spinner("Đang trích xuất yêu cầu bài tập..."):
                        results[email.id] = extract_from_email(
                            email,
                            get_client(),
                            allow_suspicious=allow_suspicious,
                        )
                except Exception as exc:
                    st.error(f"Không thể trích xuất email này: {exc}")
            outcome = results.get(email.id)
            if outcome:
                if outcome.error:
                    st.error(outcome.error)
                elif outcome.is_empty:
                    st.info("Không tìm thấy yêu cầu bài tập trong email.")
                elif outcome.items:
                    for item in outcome.items:
                        st.write(item.assignment.model_dump(exclude_none=True))
                        if item.normalized_deadlines:
                            st.write(
                                "Hạn đã chuẩn hóa: "
                                + ", ".join(
                                    str(deadline.value)
                                    for deadline in item.normalized_deadlines
                                )
                            )

st.subheader("Đề xuất chờ xác nhận")
for task in mocks.tasks():
    if task.status is TaskStatus.PROPOSED:
        st.write(
            f"- {task.title} · hạn {task.deadline:%d/%m %H:%M} · nguồn `{task.source}` · "
            f"tin cậy {task.confidence:.0%}"
        )
