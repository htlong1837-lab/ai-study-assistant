# Quickstart: Module B — Trích xuất yêu cầu bài tập

Tài liệu hướng dẫn nhanh khởi động, kiểm thử và chạy thử nghiệm Module B.

---

## 1. Yêu cầu môi trường

- Python 3.10+
- Không yêu cầu khóa API bên ngoài khi chạy chế độ kiểm thử hoặc chế độ ngoại tuyến (sử dụng Fake LLM Client mặc định).

---

## 2. Khởi tạo Cơ sở dữ liệu SQLite

Module B cung cấp cơ sở dữ liệu dùng chung cho toàn bộ dự án tại `db/assistant.db`:

```bash
python -c "from db.repository import init_db; init_db('data/assistant.db')"
```

---

## 3. Chạy Kiểm thử Tự động (Offline Unit Tests)

Toàn bộ logic xử lý, chuẩn hóa ngày giờ và máy trạng thái đều chạy kiểm thử ngoại tuyến không cần internet:

```bash
# Chạy toàn bộ test của Module B
pytest tests/extraction/ -v

# Chạy riêng bộ kiểm thử chuẩn hóa ngày giờ (>= 60 ca)
pytest tests/extraction/test_datetime_normalizer.py -v

# Chạy kiểm thử luồng tích hợp đầu - cuối (End-to-End)
pytest tests/extraction/test_e2e_flow.py -v
```

---

## 4. Chạy Đánh giá Thực nghiệm (Benchmark 3 Cấu hình)

So sánh hiệu năng giữa phương pháp đề xuất (`hybrid`) với hai phương pháp cơ sở (`regex_only` và `llm_direct`):

```bash
# Chạy cấu hình Hybrid chính thức
python -m eval.run_eval --config hybrid --split test

# Chạy baseline 1: Regex Only
python -m eval.run_eval --config regex_only --split test

# Chạy baseline 2: LLM Direct
python -m eval.run_eval --config llm_direct --split test

# Chạy thử nghiệm đánh giá ảnh hưởng của mốc neo thời gian (Không dùng anchor received_at)
python -m eval.run_eval --config hybrid --split test --no-anchor
```

Kết quả đo lường và bảng so sánh F1 / Datetime Accuracy sẽ tự động được ghi nhận tại `eval/results/<timestamp>/summary.md`.

---

## 5. Mở Ứng dụng Giao diện Streamlit

```bash
streamlit run app.py
```
Điều hướng đến trang **"📝 Trích xuất bài tập"** trên menu bên trái để trải nghiệm duyệt đề xuất, xem cảnh báo mâu thuẫn và xác nhận nhiệm vụ vào lịch học.
