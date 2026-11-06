# Quickstart: kiểm tra khung dự án

1. `python -m venv .venv` rồi kích hoạt (`.venv\Scripts\activate` trên Windows).
2. `pip install -r requirements.txt`
3. `copy .env.example .env` (để trống khóa cũng được).
4. `pytest` → tất cả pass, không cần mạng.
5. `streamlit run app.py` → mở trình duyệt:
   - Trang chủ có sơ đồ luồng và trạng thái LLM ("đang tắt" nếu chưa có khóa).
   - 4 trang module mở được; trang "Lập lịch" hiện bảng nhiệm vụ mẫu.
6. Điền `GEMINI_API_KEY` vào `.env`, khởi động lại → trang chủ báo LLM "sẵn sàng".
