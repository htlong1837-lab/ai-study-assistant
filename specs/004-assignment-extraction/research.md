# Research: Trích xuất yêu cầu bài tập (Module B)

## R1. Kiến trúc Pipeline lai (Hybrid Extraction Architecture)

- **Decision**: Kết hợp LLM và Rule Engine tất định theo mô hình 4 chặng:
  $$\text{Văn bản thô} \xrightarrow{\text{LLM Extraction}} \text{Cụm từ thô} + \text{Cấu trúc} \xrightarrow{\text{Rule Normalizer}} \text{Datetime chuẩn} \xrightarrow{\text{Conflict Checker}} \text{Proposed Task}$$
- **Rationale**:
  - LLM rất mạnh ở khả năng đọc hiểu ngữ cảnh tiếng Việt học đường, trích xuất cấu trúc phức tạp (tiêu chí chấm, quy cách đặt tên, điều kiện nộp) và tìm cụm từ chỉ thời gian nguyên văn.
  - Tuy nhiên, LLM thường xuyên bị ảo giác (hallucination) khi tự tính toán bước nhảy thời gian tương đối ("thứ 6 tuần sau", "trong vòng 3 ngày tới"), đặc biệt khi mốc neo không phải là ngày chạy máy chủ.
  - Tách bạch phần tính toán thời gian cho Rule Engine tất định giúp bảo đảm 100% tính kiểm chứng, tái lập và độc lập với mô hình LLM bên dưới.
- **Alternatives**:
  - *Direct LLM Output (LLM sinh trực tiếp ISO-8601)*: Dễ sai lệch ngày khi mốc neo ở quá khứ/tương lai, không thể kiểm chứng quy tắc tính toán.
  - *Regex/Heuristic thuần túy*: Nhanh nhưng quá cứng nhắc, dễ gãy khi giảng viên đổi cách hành văn, không thể trích xuất tiêu chí chấm dài nhiều đoạn.

---

## R2. Động cơ Chuẩn hoá Ngày giờ Tiếng Việt (Vietnamese Datetime Normalization)

- **Decision**:
  - Xây dựng động cơ luật thuần (pure function) `normalize(text, anchor, semester)` nhận đầu vào là chuỗi cụm từ nguyên văn và mốc neo thời gian `anchor` (`ClassifiedEmail.received_at` hoặc ngày tài liệu).
  - Tuần quy ước theo ISO-8601: Bắt đầu thứ Hai, kết thúc Chủ Nhật. "Thứ 6 tuần sau" = thứ Sáu của tuần liền kề tiếp theo.
  - Giờ mặc định: Nếu văn bản không ghi giờ (ví dụ: *"hạn nộp ngày 20/11"*), hệ thống tự động gán `23:59:00`, đặt cờ `time_defaulted = True` và ghi nhận giả định `"Không ghi giờ, giả định 23:59"`.
  - Giờ đặc thù tiếng Việt: "12h trưa" = 12:00; "12h đêm 15/11" = 00:00 ngày 16/11 kèm cờ `AMBIGUOUS`. "Sáng" mặc định 08:00, "Chiều" mặc định 14:00, "Tối" mặc định 20:00.
  - Mốc học kỳ ("tuần 10 môn CSDL", "hết tuần 8"): Chỉ phân giải khi có `SemesterConfig(start_date)`. Nếu thiếu cấu hình, trả `value = None` kèm cờ `UNRESOLVED`.
  - Mơ hồ đứng một mình ("nộp vào tuần sau", "buổi học tới"): Trả `value = None` kèm cờ `AMBIGUOUS`, không tự đoán.
- **Rationale**: Sinh viên và giảng viên đại học tại Việt Nam có thói quen diễn đạt thời gian rất phong phú và đặc thù; giải pháp cần xử lý linh hoạt nhưng luôn giữ được tính tất định tuyệt đối.

---

## R3. Cơ chế Kiểm chứng Bằng chứng (Evidence Grounding)

- **Decision**:
  - Mọi trường dữ liệu do LLM trích xuất bắt buộc phải trả về kèm `Evidence(quote=..., location=...)`.
  - Code Python tự động chuẩn hóa khoảng trắng và kiểm tra xem chuỗi `quote` có phải là chuỗi con (substring) của văn bản nguồn gốc hay không (đối với tài liệu PDF, kiểm tra đúng trang được chỉ định).
  - Nếu `quote` không tìm thấy trong văn bản: Thu hồi giá trị (`value = None`), gắn cảnh báo `"evidence_not_found:<field>"`.
- **Rationale**: Đảm bảo nguyên tắc "Truy xuất nguồn gốc" (Constitution III). Sinh viên chỉ cần nhìn vào đề xuất là có thể bấm xem ngay đoạn trích dẫn đối chứng trong email hoặc trang PDF gốc.

---

## R4. Phát hiện Mâu thuẫn Tất định & Đề xuất Cập nhật (Conflict Handling)

- **Decision**:
  - So sánh hạn nộp: Nếu một bên có `time_defaulted = True`, hệ thống chỉ so sánh ở **mức độ ngày**. Nếu cùng ngày thì không báo lệch hạn nộp để tránh làm phiền sinh viên với cảnh báo giả.
  - Khi email là thông báo dời hạn cho một nhiệm vụ đã tồn tại (kể cả task đã `confirmed`): Hệ thống **không được tự tiện ghi đè task**, mà tạo một bản ghi `task_update_proposals` ở trạng thái `pending`.
  - Gợi ý của hệ thống: Ưu tiên nguồn có tính chất đính chính/gia hạn và có ngày gửi mới hơn.
- **Rationale**: Bảo vệ tính ổn định của lịch học (Module C). Sinh viên phải là người quyết định cuối cùng có chấp nhận dời hạn hay không.

---

## R5. Đánh giá Thực nghiệm & Bộ ba Cấu hình (3-Way Evaluation)

- **Decision**:
  - Xây dựng kịch bản benchmark `eval/run_eval.py` so sánh 3 cấu hình:
    1. `regex_only`: Baseline 1 — Heuristic regex tìm cụm thời gian + rule engine.
    2. `llm_direct`: Baseline 2 — LLM sinh trực tiếp datetime ISO mà không qua rule engine.
    3. `hybrid`: Phương pháp đề xuất — LLM trích cụm thô + rule engine chuẩn hóa.
  - Đo lường Field-level F1, Datetime Exact Accuracy, Conflict Detection Recall/Precision và chi phí token.
- **Rationale**: Cung cấp đầy đủ số liệu định lượng cho Báo cáo sản phẩm SP2 theo đúng yêu cầu Application Track.
