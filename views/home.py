import streamlit as st

from core import mocks
from core.contracts import TaskStatus, can_forward
from core.llm_client import get_client
from views._shared import llm_status

st.title("📚 Trợ lý AI học tập và lịch trình")
st.write(
    "Gom email, đề bài và giáo trình thành lịch học có nhắc nhở, kèm hỏi đáp tài liệu có "
    "trích dẫn trang. **AI chỉ đề xuất** — mọi nhiệm vụ phải được bạn xác nhận trước khi vào lịch."
)

st.subheader("Luồng xử lý")
st.graphviz_chart(
    """
    digraph {
      rankdir=LR; node [shape=box, style=rounded];
      mail [label="Email (.eml)"];
      D [label="D · Email & bảo mật\\nphân loại, quét link/file"];
      block [label="Chặn\\n(độc)", shape=octagon];
      A [label="A · Hỏi đáp tài liệu\\nđọc PDF theo trang"];
      B [label="B · Trích xuất bài tập\\nhạn nộp, yêu cầu"];
      ok [label="Bạn xác nhận", shape=diamond];
      C [label="C · Lập lịch & nhắc nhở\\nEDF / CP-SAT"];
      mail -> D; D -> block [style=dashed]; D -> B; D -> A [label="file an toàn"];
      A -> B [label="văn bản"]; B -> ok; ok -> C;
    }
    """
)

st.subheader("Trạng thái")
llm_status()

emails, tasks = mocks.emails(), mocks.tasks()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Email mẫu", len(emails))
c2.metric("Bị chặn tại cổng", sum(not can_forward(e) for e in emails))
c3.metric("Nhiệm vụ đã xác nhận", sum(t.status is TaskStatus.CONFIRMED for t in tasks))
c4.metric("Lượt gọi LLM", get_client().usage()["calls"])
