# Sub-Plan 7: Bộ Đánh giá Thực nghiệm & Benchmark (FR-B07)

> **Mục tiêu:** Xây dựng bộ công cụ đánh giá tự động (`metrics.py`, `run_eval.py`), định dạng dữ liệu vàng (Gold standard dataset), và thực hiện thí nghiệm đo lường so sánh 3 cấu hình thực nghiệm phục vụ viết Báo cáo SP2.  
> **Ước tính thời gian:** 5 giờ  
> **Phase tương ứng:** Phase 8

---

## 1. Thiết kế Bộ Đánh giá & Chỉ số Đo lường

### 1.1. Cấu trúc Dữ liệu Vàng (`eval/gold/*.json`)
Mỗi mẫu kiểm thử là một file JSON độc lập:
```json
{
  "id": "s001",
  "category": "standard",            // standard | extension | complex_time | ambiguous
  "split": "test",                   // dev | test (Chỉ báo cáo số trên test)
  "email": {
    "received_at": "2026-11-04T10:00:00+07:00",
    "body": "Nộp bài tập SP1 trước 23h59 thứ Sáu tuần sau lên Google Drive."
  },
  "document": {
    "pages": [{"number": 1, "text": "Hạn nộp báo cáo SP1: 13/11/2026"}]
  },
  "gold": {
    "title": "Báo cáo SP1",
    "course": "Trí tuệ nhân tạo",
    "deadline": "2026-11-13T23:59:00+07:00",
    "raw_deadline_text": "23h59 thứ Sáu tuần sau",
    "submission_platform": "Google Drive",
    "submission_format": [".pdf"],
    "grading_criteria": ["Khảo sát giải pháp", "Kiến trúc hệ thống"],
    "has_deadline_conflict": false
  }
}
```
*Lưu ý bảo mật:* Chỉ commit các file `*.example.json` đã ẩn danh trong git. Dữ liệu thật được lưu ngoài git và bị `.gitignore` chặn.

### 1.2. Các chỉ số đánh giá cốt lõi (`eval/metrics.py`)
1. **Field-level F1-score:**
   - Đánh giá trên các trường: `title`, `course`, `raw_deadline_text`, `submission_platform`, `grading_criteria`.
   - Chuẩn hóa chuỗi trước khi so sánh (chữ thường, bỏ dấu tiếng Việt, loại bỏ khoảng trắng thừa).
   - Quy ước: Cả kỳ vọng và dự đoán đều là `null` thì tính là đúng (True Negative) và không làm thổi phồng Precision/Recall.
2. **Datetime Accuracy (Độ chính xác ngày giờ %):**
   - Exact Match đến từng phút:
     - Đo riêng trên tập `eval/datetime_cases.yaml` ($\ge 60$ ca, độc lập hoàn toàn với LLM).
     - Đo luồng đầu - cuối trên tập dữ liệu bài tập vàng.
3. **Conflict Detection (Phát hiện mâu thuẫn):**
   - Precision và Recall phát hiện lệch hạn nộp.
   - Báo cáo cả số đếm tuyệt đối (ví dụ $4/4$ ca phát hiện chính xác), không chỉ dựa vào tỉ lệ phần trăm.
4. **Hiệu năng & Chi phí:**
   - Latency trung bình mỗi văn bản (giây).
   - Số lượng prompt/completion tokens trung bình và chi phí ước tính dựa trên `TokenTracker`.

### 1.3. Ba cấu hình so sánh thực nghiệm (Experimental Configurations)
Script `eval/run_eval.py` hỗ trợ cờ `--config`:
1. `regex_only`: Baseline 1 — Chỉ dùng Regex/Heuristic tìm cụm thời gian và gọi bộ luật `normalize()`, không gọi LLM.
2. `llm_direct`: Baseline 2 — LLM sinh trực tiếp chuỗi ngày giờ ISO, không đi qua Rule Engine.
3. `hybrid`: Phương pháp đề xuất — LLM trích xuất cụm từ thô và cấu trúc, Rule Engine chuẩn hóa ngày giờ.
4. Thử nghiệm bổ sung (`--no-anchor`): Chạy `hybrid` nhưng dùng ngày hiện tại thay vì `received_at` để chứng minh tầm quan trọng sống còn của kỹ thuật neo thời gian.

---

## 2. Nhiệm vụ chi tiết (Checklist)

- [ ] **T07.1 — Cài đặt `eval/metrics.py`:**
  - Viết các hàm tính Precision, Recall, F1 cho trường chuỗi đơn và trường danh sách.
  - Viết hàm kiểm tra Exact Match datetime có xử lý timezone.
  - Viết unit test `tests/extraction/test_metrics.py` kiểm tra công thức tính toán trên các ca tính tay mẫu.
- [ ] **T07.2 — Soạn thảo dữ liệu mẫu `eval/gold/*.example.json`:**
  - Tạo các mẫu đại diện đủ 4 nhóm: chuẩn, dời hạn/mâu thuẫn, thời gian phức tạp, mơ hồ.
- [ ] **T07.3 — Cài đặt script `eval/run_eval.py`:**
  - Hỗ trợ các tham số dòng lệnh `--config [regex_only|llm_direct|hybrid]`, `--split [dev|test]`, `--no-anchor`.
  - Tự động xuất kết quả báo cáo ra file `eval/results/<timestamp>/summary.md` và `summary.json`.
- [ ] **T07.4 — Chạy benchmark và ghi nhận số liệu:**
  - Chạy benchmark với Fake LLM và (nếu có API key) trên tập dữ liệu đánh giá để sinh bảng so sánh 3 phương pháp phục vụ Báo cáo SP2.

---

## 3. Tiêu chí nghiệm thu (Definition of Done)

- Script `python -m eval.run_eval --config hybrid --split test` chạy thành công không lỗi.
- Bảng tổng hợp so sánh 3 cấu hình hiển thị rõ ràng F1-score, Datetime Accuracy và Latency.
- File `eval/README.md` hướng dẫn cách chạy và tái lập số liệu.
