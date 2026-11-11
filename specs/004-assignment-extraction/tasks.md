# Tasks: Trích xuất yêu cầu bài tập từ email và văn bản (Module B)

**Input**: Design documents from `/specs/004-assignment-extraction/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/extraction-api.md`, `quickstart.md`)

**Prerequisites**: Python 3.10+, SQLite3, Pydantic v2, pytest. Không yêu cầu mạng hay API key (chạy bằng `FakeLLMClient`).

**Organization**: Các nhiệm vụ được nhóm theo cơ sở hạ tầng (Setup, Foundational) và từng User Story (US1, US2, US3, US4) để đảm bảo tính độc lập và khả năng kiểm thử riêng biệt.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Có thể chạy song song (khác file, không phụ thuộc nhau)
- **[Story]**: Gắn với User Story tương ứng (`US1`, `US2`, `US3`, `US4`)
- Bao gồm đường dẫn file chính xác trong mô tả công việc

---

## Phase 1: Setup (Hạ tầng chung & Khảo sát)

**Mục tiêu**: Khảo sát mã nguồn, thiết lập môi trường bảo vệ dữ liệu và chuẩn bị cấu hình ban đầu.

- [x] T001 Cập nhật `.gitignore` để loại trừ `data/private/`, `eval/gold/*.json`, `!eval/gold/*.example.json`, `*.db`, `*.db-journal`, `*.db-wal`
- [x] T002 [P] Soạn thảo `docs/module_b/RECON.md` đối chiếu các giả định kỹ thuật với `core/contracts.py`, `core/mocks.py` và `core/llm_client.py`
- [x] T003 [P] Soạn thảo `docs/module_b/CONTRACT_REQUESTS.md` ghi nhận các đề xuất hợp đồng (hỗ trợ thread_id, xử lý deadline null nội bộ)
- [x] T004 [P] Tạo file cấu hình học kỳ mẫu `config/semester.example.yaml`

---

## Phase 2: Foundational (Nền tảng kỹ thuật bắt buộc)

**Mục tiêu**: Xây dựng CSDL SQLite dùng chung, Pydantic schemas, động cơ chuẩn hóa thời gian tiếng Việt và cổng chặn bảo mật. Mọi User Story đều phụ thuộc vào pha này.

**⚠️ QUAN TRỌNG**: Không bắt đầu cài đặt User Story trước khi Phase 2 hoàn thành và test xanh.

- [x] T005 Tạo schema cơ sở dữ liệu `db/schema.sql` (bảng tasks, task_sources, assignment_details, conflicts, task_update_proposals, extraction_logs)
- [x] T006 Cài đặt `db/repository.py` (hàm init_db idempotent, bật foreign_keys=ON và journal_mode=WAL, kết nối theo transaction)
- [x] T007 Viết unit test `tests/extraction/test_repository.py` kiểm tra CRUD, cascade delete, ràng buộc unique log và deadline NULL
- [x] T008 [P] Cài đặt `modules/extraction/schemas.py` (Pydantic models: Evidence, ExField, RawDeadline, RawAssignment, ExtractionResult)
- [x] T009 [P] Xây dựng bộ test cases thời gian tiếng Việt `eval/datetime_cases.yaml` ($\ge 60$ ca kiểm thử bao quát mẫu tuyệt đối, tương đối, tuần, giờ mặc định 23:59)
- [x] T010 Cài đặt `modules/extraction/datetime_normalizer.py` (hàm thuần normalize, neo vào anchor, không gọi datetime.now, xử lý tuần ISO, gán cờ cảnh báo)
- [x] T011 Viết unit test `tests/extraction/test_datetime_normalizer.py` đọc tham số hóa toàn bộ cases từ `eval/datetime_cases.yaml`
- [x] T012 [P] Cài đặt cổng bảo mật `modules/extraction/gate.py` (hàm ensure_safe gọi can_forward, ném UnsafeSourceError khi gặp email độc hại)

**Checkpoint**: Nền tảng CSDL và bộ chuẩn hóa thời gian hoàn tất; kiểm thử `pytest tests/extraction/test_repository.py tests/extraction/test_datetime_normalizer.py` đạt 100% xanh.

---

## Phase 3: User Story 1 - Tự động trích xuất bài tập từ email và đề bài (Priority: P1) 🎯 MVP

**Mục tiêu**: Nhận email học tập hoặc tài liệu đề bài an toàn, gọi LLM trích xuất thông tin có cấu trúc, kiểm chứng bằng chứng (quote) và lưu đề xuất nhiệm vụ (`proposed`) vào CSDL.

**Kiểm thử độc lập**: Xử lý một email bài tập mẫu (hoặc tài liệu PDF mẫu), hệ thống sinh ra một bản ghi trong bảng `tasks` ở trạng thái `proposed` với đầy đủ tên bài tập, môn học, hạn nộp đã chuẩn hóa kèm trích dẫn văn bản gốc.

### Tests cho User Story 1
- [x] T013 [P] [US1] Viết unit test `tests/extraction/test_extractor.py` (kiểm tra chặn email độc hại, kiểm tra loại bỏ trường khi evidence giả, kiểm tra caching không tốn token)

### Cài đặt cho User Story 1
- [x] T014 [P] [US1] Cài đặt `modules/extraction/prompts.py` (PROMPT_VERSION, system prompt trợ lý học vụ, chống prompt injection, 4 ví dụ few-shot chuẩn)
- [x] T015 [P] [US1] Cài đặt `modules/extraction/confidence.py` (hàm compute_confidence bằng code tất định dựa trên độ đầy đủ bằng chứng và cờ cảnh báo)
- [x] T016 [US1] Cài đặt `modules/extraction/extractor.py` (hàm extract_from_email, extract_from_document, retry 1 lần khi lỗi JSON, kiểm tra quote là substring trong văn bản gốc, gọi datetime_normalizer)
- [ ] T017 [US1] Cài đặt hàm `process_email` và `process_document` trong `modules/extraction/workflow.py` để kết nối extractor với repository

**Checkpoint**: Hoạt động trích xuất độc lập hoàn chỉnh; test `pytest tests/extraction/test_extractor.py` xanh hoàn toàn với Fake LLM.

---

## Phase 4: User Story 2 - Sinh viên kiểm tra, chỉnh sửa inline và xác nhận đề xuất (Priority: P1)

**Mục tiêu**: Sinh viên xem danh sách các đề xuất bài tập trên giao diện Streamlit, chỉnh sửa hạn nộp, số giờ dự kiến, độ ưu tiên và nhấn "Xác nhận vào lịch" (`confirm()`) hoặc "Từ chối" (`cancel()`).

**Kiểm thử độc lập**: Chạy giao diện `views/extraction.py`, chọn một đề xuất bài tập, sửa hạn nộp và bấm "Xác nhận vào lịch"; task chuyển trạng thái sang `confirmed`, được hàm `schedulable()` chấp thuận và có thể chuyển đổi thành `contracts.Task`.

### Tests cho User Story 2
- [ ] T018 [P] [US2] Viết unit test `tests/extraction/test_workflow.py` (kiểm tra vòng đời proposed → confirmed, proposed → cancelled, chặn confirm khi thiếu deadline, kiểm tra to_contract_task)

### Cài đặt cho User Story 2
- [ ] T019 [US2] Cài đặt các hàm chuyển đổi trạng thái trong `modules/extraction/workflow.py` (`confirm`, `cancel`, `to_contract_task`)
- [ ] T020 [US2] Xây dựng giao diện Streamlit Mức 1 trong `views/extraction.py` (danh sách email an toàn, danh sách thẻ proposed, form chỉnh sửa inline deadline / số giờ / ưu tiên, nút Xác nhận và Từ chối)
- [ ] T021 [US2] Cập nhật `tests/test_pages.py` kiểm tra trang `views/extraction.py` render thành công không có ngoại lệ runtime

**Checkpoint**: Hoàn thiện toàn bộ luồng MVP cốt lõi (User Story 1 + User Story 2) từ trích xuất đến người dùng duyệt bài tập.

---

## Phase 5: User Story 3 - Trích xuất chi tiết yêu cầu nộp bài và tiêu chí chấm điểm (Priority: P2)

**Mục tiêu**: Mở rộng khả năng đọc hiểu để trích xuất quy cách nộp bài (định dạng .zip/.pdf, nơi nộp LMS/Drive, quy cách đặt tên file) và danh sách tiêu chí chấm điểm (rubric).

**Kiểm thử độc lập**: Cung cấp tài liệu đề bài có rubric và yêu cầu đặt tên; hệ thống trích xuất và lưu đầy đủ vào bảng `assignment_details`, hiển thị mục mở rộng trên UI.

### Tests cho User Story 3
- [ ] T022 [P] [US3] Bổ sung test kiểm tra trích xuất chi tiết rubric và định dạng nộp trong `tests/extraction/test_extractor.py`

### Cài đặt cho User Story 3
- [ ] T023 [US3] Mở rộng `modules/extraction/extractor.py` để lưu trữ dữ liệu chi tiết vào bảng `assignment_details`
- [ ] T024 [US3] Bổ sung thành phần hiển thị chi tiết (expander/dialog) trên giao diện `views/extraction.py` hiển thị quy cách đặt tên, kênh nộp và bảng tiêu chí chấm

---

## Phase 6: User Story 4 - Phát hiện mâu thuẫn và thông báo dời hạn nộp (Priority: P2)

**Mục tiêu**: Tự động so sánh đối chiếu giữa email và file đề bài PDF; phát hiện lệch hạn nộp, lệch kênh nộp, cảnh báo mơ hồ và xử lý email dời hạn cho task đã `confirmed`.

**Kiểm thử độc lập**: Cung cấp email dời hạn cho một bài tập đã tồn tại; hệ thống nhận diện đúng bài tập, giữ nguyên task gốc và sinh một bản ghi `task_update_proposals` ở trạng thái pending kèm cảnh báo lệch hạn trên UI.

### Tests cho User Story 4
- [ ] T025 [P] [US4] Viết unit test `tests/extraction/test_conflicts.py` (test lệch hạn 7 ngày, test cùng ngày khác giờ mặc định không báo lỗi, test đề xuất dời hạn cho task đã confirmed)

### Cài đặt cho User Story 4
- [ ] T026 [P] [US4] Cài đặt `modules/extraction/matcher.py` (hàm find_matching_task so khớp theo mã bài, refers_to và độ tương đồng tên môn/tên bài)
- [ ] T027 [US4] Cài đặt `modules/extraction/conflicts.py` (hàm compare_deadlines, compare_submission, detect_ambiguity, gợi ý phương án thông minh)
- [ ] T028 [US4] Bổ sung hàm `resolve_conflict`, `accept_update_proposal`, `reject_update_proposal` vào `modules/extraction/workflow.py`
- [ ] T029 [US4] Bổ sung Hộp cảnh báo mâu thuẫn (`st.warning`) và Danh sách đề xuất dời hạn (`task_update_proposals`) trên giao diện `views/extraction.py`

---

## Phase 7: Polish & Cross-Cutting Concerns (Đo lường, Demo & Hoàn thiện)

**Mục tiêu**: Xây dựng bộ công cụ benchmark đo số cho Báo cáo SP2, kiểm thử tích hợp toàn bộ luồng và kịch bản demo.

- [ ] T030 Cài đặt `eval/metrics.py` (Field F1-score, Datetime Exact Accuracy, Conflict Precision/Recall) và test `tests/extraction/test_metrics.py`
- [ ] T031 [P] Soạn thảo bộ dữ liệu mẫu vàng `eval/gold/*.example.json` (đại diện 4 nhóm: chuẩn, dời hạn, thời gian phức tạp, mơ hồ)
- [ ] T032 Cài đặt script chạy đánh giá benchmark `eval/run_eval.py` (hỗ trợ cờ `--config regex_only|llm_direct|hybrid` và `--no-anchor`, xuất `eval/results/<timestamp>/summary.md`)
- [ ] T033 Viết bài kiểm thử luồng tích hợp đầu - cuối `tests/extraction/test_e2e_flow.py` chạy qua 4 bước kịch bản demo bằng Fake LLM
- [ ] T034 [P] Soạn thảo tài liệu hướng dẫn demo `docs/module_b/DEMO.md` và chụp ảnh màn hình lưu vào `docs/module_b/screens/`
- [ ] T035 Rà soát toàn bộ Checklist Định nghĩa Hoàn thành (Definition of Done) trong Kế hoạch Master

---

## Dependencies & Execution Order

```
[Phase 1: Setup] ──► [Phase 2: Foundational]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [Phase 3: US1 (P1)] ──► [Phase 4: US2 (P1)] 🎯 MVP Complete
            │                                 │
            ├────────────────┬────────────────┘
            ▼                ▼
   [Phase 5: US3 (P2)]  [Phase 6: US4 (P2)]
            │                │
            └────────┬───────┘
                     ▼
        [Phase 7: Polish & Demo]
```

### Chiến lược triển khai lũy tiến (Incremental Delivery):
1. **Hoàn thành Setup + Foundational (Phase 1 + 2)**: CSDL SQLite và bộ chuẩn hóa ngày giờ hoạt động ổn định.
2. **Triển khai MVP (Phase 3 + 4)**: US1 (Trích xuất) và US2 (Duyệt/Xác nhận) hoàn thành $\rightarrow$ Hệ thống đã có thể chạy demo độc lập và cấp dữ liệu `Task` cho Module C xếp lịch.
3. **Mở rộng tính năng nâng cao (Phase 5 + 6)**: US3 (Chi tiết rubric) và US4 (Bắt mâu thuẫn & dời hạn).
4. **Đo số & Báo cáo (Phase 7)**: Chạy `run_eval.py` lấy bảng số liệu 3 cấu hình phục vụ Báo cáo SP2.

---

## Parallel Execution Examples

### Chạy song song trong Phase 1 (Setup):
```bash
# Thực hiện đồng thời các tài liệu khảo sát và cấu hình không phụ thuộc nhau:
Task: "T002 [P] Soạn thảo docs/module_b/RECON.md"
Task: "T003 [P] Soạn thảo docs/module_b/CONTRACT_REQUESTS.md"
Task: "T004 [P] Tạo file cấu hình học kỳ mẫu config/semester.example.yaml"
```

### Chạy song song trong Phase 2 (Foundational):
```bash
# Triển khai song song schemas và bộ test cases ngày giờ:
Task: "T008 [P] Cài đặt modules/extraction/schemas.py"
Task: "T009 [P] Xây dựng bộ test cases thời gian tiếng Việt eval/datetime_cases.yaml"
Task: "T012 [P] Cài đặt cổng bảo mật modules/extraction/gate.py"
```

### Chạy song song trong Phase 3 (User Story 1):
```bash
# Viết test và chuẩn bị prompt/confidence song song:
Task: "T013 [P] [US1] Viết unit test tests/extraction/test_extractor.py"
Task: "T014 [P] [US1] Cài đặt modules/extraction/prompts.py"
Task: "T015 [P] [US1] Cài đặt modules/extraction/confidence.py"
```

---

## Notes & Verification

- **[P] tasks**: Thực hiện trên các file độc lập, không có xung đột mã nguồn.
- **[Story] tags**: Đảm bảo truy xuất nguồn gốc ngược lại `spec.md` (US1, US2, US3, US4).
- **Quy tắc chuyển phase**: Viết test trước, đảm bảo test thất bại (red) trước khi viết logic để test chuyển sang xanh (green).
- **Môi trường**: 100% test chạy offline với `FakeLLMClient`, không phụ thuộc mạng hay quota API.

