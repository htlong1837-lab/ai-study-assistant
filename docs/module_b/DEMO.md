# Kịch bản Demo và Hướng dẫn Vận hành Module B

Tài liệu hướng dẫn chạy thử nghiệm thực tế tính năng của **Module B (Trích xuất yêu cầu bài tập)** trong Đồ án Trợ lý Học tập AI.

---

## 1. Yêu cầu Tiền đề (Prerequisites)

- Python 3.11+ (hoặc 3.14).
- Các gói thư viện phụ thuộc: `streamlit`, `pytest`, `pydantic`, `pyyaml`, `ortools`, `python-dotenv`.
- CSDL SQLite nội bộ tự động khởi tạo tại `data/app.db`.

---

## 2. Kịch bản Demo 4 Bước (The Golden Path)

Kịch bản thể hiện trọn vẹn 5 nguyên tắc Hiến pháp dự án:

### Bước 1: Tiếp nhận Nguồn và Trích xuất Đề xuất (AI chỉ đề xuất)
- Truy cập vào giao diện web Streamlit (Tab **📝 Trích xuất bài tập**).
- Hệ thống duyệt qua danh sách email từ `core/mocks.py`:
  - Email an toàn (`SAFE`) được phép đọc và hiển thị nội dung.
  - Email lừa đảo (`MALICIOUS`) lập tức bị cổng an toàn chặn lại đỏ rực, không bao giờ được gửi vào LLM.
- Nhấn nút **"🚀 Bắt đầu trích xuất email & tài liệu mẫu vào DB"**.
- Kết quả: Các bài tập được phân tích, chuẩn hóa ngày giờ và lưu vào bảng `tasks` ở trạng thái `proposed`.

### Bước 2: Sinh viên Kiểm tra, Chỉnh sửa và Xác nhận (Human-in-the-loop)
- Sinh viên xem thẻ bài tập:
  - Xem hạn nộp đã được phân giải tự động (kèm giờ mặc định 23:59 nếu văn bản không ghi giờ).
  - Bấm mở rộng **"🔍 Chi tiết yêu cầu bài tập & Tiêu chí chấm điểm (Rubric)"** để kiểm tra kênh nộp (LMS / Drive), quy cách đặt tên và rubric chấm điểm.
  - Chỉnh sửa inline số giờ học dự kiến (ví dụ: tăng từ 2 giờ lên 6 giờ) hoặc mức ưu tiên (`high`).
- Nhấn nút **"✅ Xác nhận vào lịch"**:
  - Trạng thái bài tập chuyển từ `proposed` sang `confirmed`.
  - Nhiệm vụ xuất hiện ngay lập tức trong bảng "Bài tập đã xác nhận", sẵn sàng cho Module C (Lập lịch) tự động phân bổ khối học và nhắc nhở Telegram.

### Bước 3: Phát hiện Mâu thuẫn & Đề xuất Dời hạn nộp (Conflicts & Update Proposals)
- Giảng viên gửi email dính chính dời hạn nộp cho bài tập đã có.
- Bộ so khớp `matcher.py` tự động phát hiện bài tập tương ứng trong CSDL mà không tạo trùng lặp.
- Nguyên tắc an toàn: Hệ thống **tuyệt đối không tự sửa task gốc đã xác nhận**.
- Thay vào đó:
  - Sinh một bản ghi trong bảng `task_update_proposals` ở trạng thái `pending`.
  - Trên giao diện xuất hiện thẻ thông báo: Hạn cũ (`13/11`) $\rightarrow$ Hạn mới (`20/11`) kèm trích dẫn văn bản gốc.

### Bước 4: Sinh viên Phê duyệt Dời hạn
- Sinh viên xem xét đề xuất:
  - Nếu đồng ý: Bấm **"✅ Chấp nhận thay đổi"** $\rightarrow$ Hạn nộp mới được cập nhật vào task gốc, Module C tự động dời lịch học.
  - Nếu từ chối: Bấm **"❌ Giữ nguyên hạn cũ"**.

---

## 3. Khởi chạy Giao diện

Khởi chạy ứng dụng Streamlit:
```bash
streamlit run app.py
```
Mở trình duyệt tại địa chỉ `http://localhost:8501`, chọn trang **Trích xuất bài tập**.

---

## 4. Chạy Đánh giá Benchmark Tự động

Chạy benchmark so sánh 3 cấu hình thực nghiệm phục vụ Báo cáo SP2:
```bash
# Cấu hình đề xuất (Hybrid: LLM + Rule Engine)
python -m eval.run_eval --config hybrid --split test

# Cấu hình Baseline 1 (Regex only)
python -m eval.run_eval --config regex_only --split test

# Cấu hình Baseline 2 (LLM Direct)
python -m eval.run_eval --config llm_direct --split test

# Thử nghiệm không neo thời gian
python -m eval.run_eval --config hybrid --split test --no-anchor
```

Kết quả tổng hợp và báo cáo Markdown được tự động xuất ra thư mục `eval/results/<timestamp>/summary.md`.

---

## 5. Chạy Toàn bộ Bộ Kiểm thử (Pytest)

Chạy kiểm thử riêng cho Module B:
```bash
pytest tests/extraction/ -v
```

Chạy kiểm thử giao diện trang:
```bash
pytest tests/test_pages.py -v
```
