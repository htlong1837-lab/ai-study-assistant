# Kế hoạch con Module B: Trích xuất yêu cầu bài tập

> Căn cứ theo `PLAN TRIỂN KHAI — Module B` và cấu trúc repo `ai-study-assistant`.
> Tài liệu này đóng vai trò chỉ mục (index) và hướng dẫn thực thi từng bước cho AI coding agent và thành viên nhóm trước khi viết code.

---

## 1. Kết quả Review Kế hoạch Master

Kế hoạch Master của Module B được xây dựng rất chặt chẽ, đáp ứng xuất sắc các tiêu chí của môn học (Application Track, 5 tuần, 46 giờ) và giải quyết trọn vẹn bài toán trích xuất học vụ với độ tin cậy cao.

### Điểm mạnh cốt lõi:
1. **Kiến trúc Hybrid bền bỉ:** LLM chỉ đảm nhận việc đọc hiểu ngữ nghĩa, trích xuất cấu trúc và văn bản thô kèm trích dẫn nguyên văn (`evidence.quote`). Việc tính toán thời gian và so sánh lệch hạn nộp được giao hoàn toàn cho **code tất định (Rule Engine)**. Thiết kế này triệt tiêu nguy cơ ảo giác (hallucination) về ngày giờ của LLM.
2. **Kỷ luật dữ liệu & Hợp đồng nghiêm ngặt:** Tuân thủ 4 nguyên tắc bất biến: AI chỉ đề xuất (`proposed` $\rightarrow$ `confirm()`), Chặn tại cổng (`can_forward()`), Truy xuất nguồn gốc và Hợp đồng độc lập (`core/contracts.py`).
3. **Phân rã kiểm thử sâu:** Kiểm thử ngoại tuyến (offline) bằng Fake LLM, kiểm thử tham số hóa bộ chuẩn hóa ngày giờ tiếng Việt với $\ge 60$ ca biên, đo lường F1 và độ chính xác ngày giờ trên 3 cấu hình thực nghiệm (`regex_only`, `llm_direct`, `hybrid`).

### Điểm cần lưu ý & Khớp nối Codebase (Recon Findings):
- **Vị trí thư mục code:** Master plan đề cập `modules/b_extraction/` hoặc `modules/extraction/`. Trong codebase, thư mục `modules/extraction/` đã có sẵn và đang được `views/extraction.py` import. Chúng ta sẽ cài đặt mã nguồn chính vào `modules/extraction/` (đồng thời tạo alias/import tương thích nếu cần) để tuân thủ quy tắc "Code trong repo thắng".
- **Hợp đồng `ClassifiedEmail`:** Hiện tại trong `core/contracts.py`, `ClassifiedEmail` chưa có các trường `thread_id` và `in_reply_to`. Vì vậy, logic so khớp bài tập dời hạn sẽ ưu tiên dùng nội dung tham chiếu (`refers_to`) và tên môn/tên bài, ghi nhận yêu cầu bổ sung vào `docs/module_b/CONTRACT_REQUESTS.md`.
- **Hợp đồng `Task`:** Thuộc tính `deadline` trong `contracts.Task` là bắt buộc kiểu `datetime` (không cho phép `None`). Do đó, các bài tập trích xuất mà chưa tìm thấy hạn nộp sẽ được lưu nội bộ trong bảng `tasks` của SQLite (`deadline IS NULL`, trạng thái `proposed`), và chỉ chuyển đổi sang `contracts.Task` sau khi sinh viên đã bổ sung hạn nộp trên UI.
- **Cấu hình `.gitignore`:** Cần bổ sung `eval/gold/*.json` (trừ `*.example.json`) và `data/private/` để đảm bảo không rò rỉ dữ liệu thật.

---

## 2. Danh mục các Kế hoạch con (Sub-Plans)

Mỗi kế hoạch con tương ứng với một đơn vị công việc độc lập, có định nghĩa đầu vào/đầu ra rõ ràng và tiêu chí kiểm thử nghiệm thu (DoD) riêng biệt:

| Kế hoạch con | Tên file | Mô tả & Nhiệm vụ chính | Phase tương ứng |
|---|---|---|---|
| **Sub-Plan 0** | [00-recon-setup.md](00-recon-setup.md) | Khảo sát repo, kiểm tra contracts, cập nhật `.gitignore`, lập `RECON.md` & `CONTRACT_REQUESTS.md` | Phase 0 |
| **Sub-Plan 1** | [01-database-repository.md](01-database-repository.md) | Thiết kế CSDL SQLite dùng chung (`schema.sql`), cài đặt `repository.py` & kiểm thử CRUD | Phase 1 (FR-B06) |
| **Sub-Plan 2** | [02-schemas-datetime-normalizer.md](02-schemas-datetime-normalizer.md) | Xây dựng Pydantic Schemas & Động cơ luật chuẩn hóa ngày giờ tiếng Việt ($\ge 60$ edge cases) | Phase 2 & 3 (FR-B01, FR-B02) |
| **Sub-Plan 3** | [03-llm-extractor-grounding.md](03-llm-extractor-grounding.md) | Cổng chặn an toàn (`gate.py`), Prompts có version, Extractor kiểm tra Evidence & tính Confidence | Phase 4 (FR-B01) |
| **Sub-Plan 4** | [04-matcher-conflicts.md](04-matcher-conflicts.md) | So khớp bài tập (`matcher.py`), phát hiện lệch hạn/lệch kênh nộp, sinh đề xuất cập nhật task | Phase 5 (FR-B03) |
| **Sub-Plan 5** | [05-workflow-state-machine.md](05-workflow-state-machine.md) | Máy trạng thái (`proposed` $\rightarrow$ `confirmed`), giải quyết xung đột, chuyển đổi sang `contracts.Task` | Phase 6 (FR-B04) |
| **Sub-Plan 6** | [06-streamlit-ui.md](06-streamlit-ui.md) | Giao diện Streamlit duyệt đề xuất (`views/extraction.py`), cảnh báo mâu thuẫn, sửa inline | Phase 7 (FR-B05) |
| **Sub-Plan 7** | [07-evaluation-benchmark.md](07-evaluation-benchmark.md) | Bộ đánh giá (`metrics.py`, `run_eval.py`), so sánh 3 cấu hình thực nghiệm (`regex_only`, `llm_direct`, `hybrid`) | Phase 8 (FR-B07) |
| **Sub-Plan 8** | [08-integration-demo.md](08-integration-demo.md) | Kịch bản demo vàng (End-to-End), tài liệu `DEMO.md`, kiểm thử liên module | Phase 9 |

---

## 3. Thứ tự thực thi và Kỷ luật làm việc

```
[00-recon-setup] ──► [01-database-repository] ──► [02-schemas-datetime-normalizer]
                                                              │
                                                              ▼
[05-workflow-state-machine] ◄── [04-matcher-conflicts] ◄── [03-llm-extractor-grounding]
         │
         ├──► [06-streamlit-ui]
         ├──► [07-evaluation-benchmark]
         └──► [08-integration-demo]
```

- **Quy tắc chuyển phase:** Mỗi kế hoạch con phải đạt 100% test xanh (`pytest tests/extraction/`) trước khi bắt đầu kế hoạch tiếp theo.
- **Cam kết không hồi quy:** Mọi thay đổi không được làm hỏng các bài test hiện có của `core` và `scheduler`.
