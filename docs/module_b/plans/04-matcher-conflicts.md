# Sub-Plan 4: Khớp Bài tập & Phát hiện Mâu thuẫn (FR-B03)

> **Mục tiêu:** Xây dựng cơ chế so khớp hai mục trích xuất từ các nguồn khác nhau (`matcher.py`), phát hiện các điểm mâu thuẫn về hạn nộp, kênh nộp bài và sự mơ hồ bằng giải thuật tất định (`conflicts.py`), sinh đề xuất cập nhật khi có email dời hạn cho task đã tồn tại.  
> **Ước tính thời gian:** 5 giờ  
> **Phase tương ứng:** Phase 5

---

## 1. Thiết kế Kỹ thuật chi tiết

### 1.1. Bộ so khớp bài tập (`modules/extraction/matcher.py`)
- Nhiệm vụ: Xác định xem một trích xuất mới (ví dụ từ email) có cùng nói về một bài tập đã có từ trước (ví dụ từ đề bài PDF) hay không.
- Thứ tự ưu tiên khớp:
  1. Nếu email có trường tham chiếu (`refers_to`) hoặc tiêu đề chỉ rõ mã bài tập (ví dụ: "Báo cáo SP1", "Bài tập lớn CSDL").
  2. So khớp theo tên môn học (`course`) và độ tương đồng ngữ nghĩa của tên bài tập (`title`) qua thuật toán Levenshtein / Jaccard / Token similarity với ngưỡng cấu hình ($\ge 0.75$).
  3. Vùng xám ($0.50 \le \text{similarity} < 0.75$): Có thể dùng LLM đóng vai trò phân xử nhanh chỉ trả về `same` / `different` / `unsure`.
  4. **Nguyên tắc an toàn mặc định:** Nếu kết quả là `unsure`, tuyệt đối không tự động gộp mà coi như hai bài tập riêng biệt và gắn cờ cảnh báo người dùng.

### 1.2. Phát hiện mâu thuẫn tất định (`modules/extraction/conflicts.py`)
- **1. So sánh hạn nộp (`compare_deadlines(a: NormalizedDeadline, b: NormalizedDeadline)`):**
  - Nếu cả hai nguồn đều có giờ cụ thể do người viết ghi (`time_defaulted = False`): So sánh chính xác đến từng phút.
  - Nếu một trong hai nguồn do hệ thống tự gán giờ mặc định 23:59 (`time_defaulted = True`): Chỉ so sánh ở **mức độ ngày** (`date`). Nếu cùng ngày thì không báo lệch hạn nộp.
  - Nếu lệch hạn: Sinh đối tượng `ConflictReport(kind='deadline', value_a=..., value_b=..., diff_hours=...)`.
- **2. So sánh kênh và định dạng nộp (`compare_submission(a, b)`):**
  - So sánh `submission_platform` và `submission_format` sau khi đã chuẩn hóa chữ thường, bỏ dấu tiếng Việt và loại bỏ khoảng trắng thừa.
  - Nếu có sự khác biệt (ví dụ: một bên yêu cầu nộp link GitHub, một bên yêu cầu file nén `.zip` lên LMS) $\rightarrow$ Sinh `ConflictReport(kind='submission', ...)` và lưu giữ cả 2 phương án.
- **3. Cơ chế gợi ý thông minh (`suggestion`):**
  - Nếu nguồn nào có dấu hiệu là thông báo gia hạn / đính chính (`is_extension_notice = True` hoặc chứa từ khóa `dời hạn`, `lùi hạn`, `đính chính`, `thay đổi`) và có mốc neo thời gian mới hơn $\rightarrow$ Gợi ý nghiêng về nguồn đó.
  - Gợi ý này **chỉ hiển thị dưới dạng khuyến nghị trực quan**, không tự động áp dụng đè lên quyết định của người dùng.
- **4. Phát hiện sự mơ hồ (`detect_ambiguity(raw, normalized)`):**
  - Gắn cờ cảnh báo khi:
    - Hạn nộp có cờ `AMBIGUOUS` (ví dụ: "nộp vào tuần sau" không có thứ) hoặc `UNRESOLVED`.
    - Không xác định được nơi nộp bài (`submission_platform is None`).
    - Tiêu chí chấm điểm ghi chung chung, không có rubric hay thang điểm cụ thể.
- **5. Xử lý thông báo dời hạn cho Task đã tồn tại (`task_update_proposals`):**
  - Khi email là thông báo dời hạn của một bài tập đã được lưu trong DB (kể cả task đã ở trạng thái `confirmed`): Hệ thống **không được tự tiện sửa task cũ**, mà tạo bản ghi trong bảng `task_update_proposals` ở trạng thái `pending`.

---

## 2. Nhiệm vụ chi tiết (Checklist)

- [ ] **T04.1 — Cài đặt `modules/extraction/matcher.py`:**
  - Viết hàm so khớp dựa trên chuỗi tên môn học, tiêu đề và trường `refers_to`.
  - Thiết lập ngưỡng tương đồng và fallback an toàn khi `unsure`.
- [ ] **T04.2 — Cài đặt `modules/extraction/conflicts.py`:**
  - Viết logic so sánh hạn nộp xử lý ca `time_defaulted` (cùng ngày khác giờ mặc định không báo lỗi).
  - Viết logic so sánh kênh và định dạng nộp bài.
  - Viết hàm suy luận gợi ý nguồn dựa trên tính chất gia hạn.
  - Viết hàm phát hiện mơ hồ sinh các cờ tương ứng.
- [ ] **T04.3 — Kiểm thử đơn vị `tests/extraction/test_conflicts.py`:**
  - Test phát hiện lệch hạn 7 ngày giữa email và đề PDF.
  - Test cùng ngày nhưng một bên có giờ 17h, một bên không ghi giờ (hệ thống mặc định 23h59) $\rightarrow$ Không báo lệch hạn sai.
  - Test phát hiện lệch hình thức nộp (LMS vs GitHub).
  - Test email dời hạn cho task đã `confirmed`: Tạo bản ghi proposal, không làm đổi dữ liệu task gốc.
  - Test cờ mơ hồ khi hạn nộp thiếu thông tin.

---

## 3. Tiêu chí nghiệm thu (Definition of Done)

- 100% test trong `test_conflicts.py` xanh.
- Không có hiện tượng so sánh sai do giờ mặc định.
- Mọi cảnh báo mâu thuẫn đều lưu lại nguồn gốc rõ ràng để hiển thị cho người dùng.
