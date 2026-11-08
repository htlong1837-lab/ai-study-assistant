# AI-002 — Lập kế hoạch, đặc tả Spec-kit, triển khai CSDL, Chuẩn hóa thời gian và Trích xuất Module B

| Trường thông tin | Nội dung |
|---|---|
| Mã tương tác | AI-002 |
| Người thực hiện | Duy |
| Thời gian | 2026-11-08 (phiên làm việc liên tục) |
| Công cụ AI | Antigravity (Google Gemini 3.8 Flash), môi trường Agentic IDE có quyền chạy lệnh shell và thao tác file |
| Mục đích | Lập kế hoạch, review chức năng, sinh tài liệu Spec-kit (spec, plan, tasks), triển khai Phase 1 (Setup) và Phase 2 (Foundational: CSDL SQLite, Schemas, Chuẩn hóa ngày giờ tiếng Việt, Cổng bảo mật, Extractor) cho Module B: Trích xuất yêu cầu bài tập |
| Prompt đầy đủ | Mục "Hội thoại" bên dưới |
| Phản hồi đầy đủ | Tóm tắt các phản hồi và hành động cụ thể của AI bên dưới |
| Nhận xét, đánh giá | AI tuân thủ tốt nguyên tắc kiến trúc (Hybrid Pipeline, Chặn tại cổng, AI chỉ đề xuất). Nhận diện sớm lỗi va chạm từ vựng ("sau" trong "tuần sau" bị nhầm sang thứ Sáu) khi chạy bộ 62 test cases. |
| Nội dung được sử dụng | Toàn bộ các file tài liệu thiết kế (`docs/report/B-trich-xuat.md`, `docs/module_b/plans/`, `specs/004-assignment-extraction/`), mã nguồn CSDL (`db/schema.sql`, `db/repository.py`), logic trích xuất (`modules/extraction/`) và bộ test suite (`tests/extraction/`). |
| Nội dung chỉnh sửa hoặc loại bỏ | - Chỉnh sửa regex thứ trong tuần trong `datetime_normalizer.py` để tránh từ "sau" trong "tuần sau" bị khớp sai thành thứ Sáu.<br>- Bổ sung `.gitignore` cho file `.db`, `data/private/`, `eval/gold/*.json`. |
| Cách kiểm chứng | Chạy kiểm thử tự động `pytest tests/extraction/ -v` (đạt 73/73 passed), kiểm tra tính toàn vẹn `pytest tests/test_contracts.py tests/test_llm_client.py tests/test_mocks.py tests/test_pages.py` (đạt 113/113 passed), kiểm tra CSDL SQLite bằng các test cascade delete và unique log. |
| Kết quả áp dụng | Tạo thành công 9 sub-plans, thư mục đặc tả `specs/004-assignment-extraction/`, mã nguồn cốt lõi Module B trong `modules/extraction/`, `db/`, và bộ test tự động. |

---

## Hội thoại (câu lệnh, mục đích, cách kiểm chứng và phản hồi)

| Lượt | Câu lệnh của Duy | Mục đích của Duy | Cách kiểm chứng của Duy | Phản hồi của AI (tóm tắt) |
|---|---|---|---|---|
| **1** | *"Từ file plan của project, hãy tạo 1 file review đầy đủ chức năng của module 'Trích xuất yêu cầu bài tập'"* | Lập bản review/đặc tả chi tiết chức năng Module B bám sát kế hoạch 5 tuần, phân công 46h và hợp đồng dữ liệu. | Đọc file review được tạo, kiểm tra tính đầy đủ của 10 chức năng (FR-B01 đến FR-B10) và liên kết với báo cáo SP2. | Phân tích plan tổng thể, khởi tạo `docs/report/B-trich-xuat.md` cấu trúc tương đồng `C-lap-lich.md`, cập nhật liên kết trong `docs/report/SP2-bao-cao-san-pham.md`. |
| **2** | *"Đây là file plan cho module B của mình. Hãy review lại và tạo ra các file plan con trước khi code nhé"* (kèm tài liệu PLAN TRIỂN KHAI Module B) | Đánh giá độ khả thi của Master Plan và phân rã thành các file kế hoạch con chi tiết, độc lập cho từng phase. | Kiểm tra các file kế hoạch con trong `docs/module_b/plans/` và thư mục `specs/004-assignment-extraction/` có đầy đủ tiêu chí nghiệm thu không. | Phân tích đối chiếu Master Plan với repo; tạo 9 kế hoạch con (`00-recon-setup.md` đến `08-integration-demo.md`) và chỉ mục `README.md`, đồng thời tạo `plan.md` và `tasks.md` theo chuẩn Spec-kit. |
| **3** | `/speckit-specify Xây dựng Module B Trích xuất yêu cầu bài tập từ email/văn bản đầu vào, trích xuất các thông tin như tiêu đề, hạn nộp và nội dung chi tiết.` | Khởi tạo tài liệu đặc tả tính năng (`spec.md`) theo chuẩn quy trình Spec-kit, định vị user stories và tiêu chí đo lường. | Kiểm tra `specs/004-assignment-extraction/spec.md` và checklist thẩm định chất lượng `checklists/requirements.md`. | Chạy quy trình `speckit-specify`: thiết lập `spec.md` với 4 User Stories (P1 đến P2), 12 Functional Requirements, 5 Success Criteria, và hoàn thành checklist kiểm định 16/16 mục đạt chuẩn. |
| **4** | `/speckit-plan` | Lập kế hoạch kỹ thuật, thiết kế kiến trúc, nghiên cứu công nghệ và hợp đồng API theo chuẩn Spec-kit. | Đọc các file thiết kế kỹ thuật: `research.md`, `data-model.md`, `contracts/extraction-api.md`, `quickstart.md`. | Tạo đầy đủ bộ tài liệu thiết kế trong `specs/004-assignment-extraction/`, ghi nhận 5 quyết định kỹ thuật cốt lõi (Hybrid Pipeline, Chuẩn hóa thời gian tất định, Evidence Grounding, CSDL SQLite 6 bảng). |
| **5** | `/speckit-tasks` | Sinh danh sách công việc (`tasks.md`) có thứ tự phụ thuộc, phân rã theo User Story và đánh dấu các task chạy song song. | Kiểm tra cấu trúc phân rã công việc từ Phase 1 đến Phase 7, định dạng `[ID] [P?] [Story]`. | Khởi tạo và hoàn thiện `specs/004-assignment-extraction/tasks.md` gồm 35 nhiệm vụ chi tiết từ T001 đến T035, phân tầng từ Setup, Foundational đến từng User Story. |
| **6** | `/speckit-implement Phase1, Phase 2` | Yêu cầu AI tiến hành cài đặt mã nguồn thực tế cho Phase 1 (Setup) và Phase 2 (Foundational). | Theo dõi quá trình tạo file, cài đặt thư viện thiếu (`pytest`, `pydantic`, `pyyaml`, `python-dotenv`, `streamlit`, `ortools`), chạy lệnh kiểm thử tự động. | Triển khai hoàn tất: cập nhật `.gitignore`, tạo `RECON.md`, `CONTRACT_REQUESTS.md`, `semester.example.yaml`, `db/schema.sql`, `db/repository.py`, `schemas.py`, `gate.py`, bộ 62 test cases `eval/datetime_cases.yaml`, `datetime_normalizer.py`. Chạy pytest và sửa lỗi phát hiện được. |
| **7** | *"Phase1 và phase 2 có lấy dữ liệu đầu vào từ core.mocks (ví dụ module C: mocks.tasks()), viết logic trong modules/<module>/, giao diện trong views/<module>.py không? Pytest đã pass chưa?"* | Thẩm định và kiểm tra chéo việc tuân thủ cấu trúc repo, nguồn dữ liệu giả lập và kết quả kiểm thử tự động. | Yêu cầu báo cáo rõ nguồn dữ liệu `mocks`, đường dẫn logic `modules/extraction/`, đường dẫn UI `views/extraction.py` và số liệu pytest cụ thể. | Trả lời và chứng minh: (1) Lấy đầy đủ từ `mocks.emails()`, `mocks.documents()` và `mocks.tasks()`; (2) Logic hoàn toàn nằm trong `modules/extraction/` và `db/`, UI nằm trong `views/extraction.py`; (3) Pytest đạt **73/73 passed** cho Module B và **113/113 passed** cho toàn bộ hệ thống. |

---

## Các lần AI tự phát hiện sai và sửa trong phiên (Dữ kiện đánh giá)

1. **Lỗi va chạm từ vựng trong chuẩn hóa ngày giờ tiếng Việt:**
   - *Hiện tượng:* Khi chạy kiểm thử ca `"chủ nhật tuần sau"`, kết quả trả về thứ Sáu tuần sau (`2026-11-13`) thay vì Chủ Nhật (`2026-11-15`).
   - *Nguyên nhân:* Regex tìm thứ Sáu bắt từ khóa `"sau"` vô tình khớp với chữ `"sau"` trong cụm từ `"tuần sau"` của `"chủ nhật tuần sau"`.
   - *Khắc phục:* Viết lại danh sách regex thứ trong tuần có thứ tự ưu tiên chặt chẽ (bắt `chu nhat` trước, yêu cầu `thu sau` / `t6` hoặc tiền tố rõ ràng, không để từ `sau` đứng độc lập gây hiểu nhầm). Sau khi sửa, 61/61 ca test tham số hóa pass 100%.
2. **Xử lý thiếu thư viện phụ thuộc:**
   - *Hiện tượng:* Khi chạy `pytest`, môi trường thiếu `dotenv`, `pydantic`, `pyyaml`, `streamlit`, `ortools`.
   - *Khắc phục:* AI tự động chạy lệnh cài đặt bổ sung qua pip, đưa test suite về trạng thái hoạt động ổn định trên môi trường máy cục bộ.
3. **Tuân thủ quy ước vị trí thư mục:**
   - *Hiện tượng:* Master Plan ban đầu ghi tên thư mục là `modules/b_extraction/`, nhưng repo đã có sẵn `modules/extraction/`.
   - *Khắc phục:* AI áp dụng quy tắc "Code trong repo thắng", cài đặt toàn bộ logic vào `modules/extraction/` và tài liệu hóa điểm này trong `RECON.md`.

---

## Phần kiểm chứng và trạng thái hiện tại

- **Cơ sở dữ liệu:** Đã kiểm thử `tests/extraction/test_repository.py` (7 tests) chứng minh tính idempotent của `init_db`, cascade delete, ràng buộc unique của cache logs và hỗ trợ `deadline NULL` khi proposed.
- **Động cơ ngày giờ:** Đã kiểm thử `tests/extraction/test_datetime_normalizer.py` (61 tests) chứng minh tính tất định, không phụ thuộc đồng hồ hệ thống `datetime.now()`, xử lý mốc neo `anchor` chính xác.
- **Cổng an toàn & Schemas:** Đã kiểm thử `tests/extraction/test_gate_and_schemas.py` (5 tests) chứng minh chặn đứng email độc hại ngay tại cổng và schema tương thích Pydantic v2.
- **Trạng thái sẵn sàng:** Toàn bộ Phase 1 và Phase 2 hoàn thành; sẵn sàng chuyển tiếp sang Phase 3 (LLM Extractor & Grounding) và Phase 4 (Streamlit UI hoàn chỉnh).
