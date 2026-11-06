import pandas as pd
import streamlit as st

from core import mocks
from core.contracts import can_forward
from views._shared import llm_status, module_header

module_header("🛡️ Email & bảo mật", "Hoàng Minh (D)",
              "File .eml", "ClassifiedEmail (cho B), SafeAttachment (cho A)")
llm_status()

ICON = {"safe": "🟢 an toàn", "suspicious": "🟡 nghi ngờ", "malicious": "🔴 độc"}
st.subheader("Hộp thư (mẫu)")
st.dataframe(pd.DataFrame([{
    "An toàn": ICON[e.safety.value], "Nhãn": e.label.value, "Người gửi": e.sender,
    "Tiêu đề": e.subject, "Chuyển tiếp": "có" if can_forward(e) else "chặn",
    "Tóm tắt": e.summary or "",
} for e in mocks.emails()]), hide_index=True, width="stretch")
