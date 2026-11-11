# Sub-Plan 0: Khảo sát Repo, Thiết lập Môi trường & Xác minh Hợp đồng

> **Mục tiêu:** Xác minh toàn bộ các giả định kỹ thuật giữa tài liệu Master Plan và mã nguồn hiện có trong repo, cập nhật `.gitignore` để bảo vệ dữ liệu, tạo `RECON.md` và `CONTRACT_REQUESTS.md`.  
> **Ước tính thời gian:** 0.5 giờ  
> **Phase tương ứng:** Phase 0

---

## 1. Nhiệm vụ chi tiết (Checklist)

- [ ] **T00.1 — Cập nhật `.gitignore`:**
  - Kiểm tra và thêm: `data/private/`, `eval/gold/*.json`, `!eval/gold/*.example.json`, `*.db`, `*.db-journal`, `*.db-wal`.
  - Đảm bảo tuyệt đối không theo dõi cơ sở dữ liệu thật, khóa API, hoặc tài liệu sinh viên chưa ẩn danh.
- [ ] **T00.2 — Đối chiếu và lập `docs/module_b/RECON.md`:**
  - Khảo sát `core/contracts.py`:
    - `ClassifiedEmail`: Kiểm tra các trường hiện có (`id`, `sender`, `subject`, `body`, `received_at`, `label`, `safety`, `summary`, `attachments`, `label_confidence`). Xác nhận timezone (naive hay tz-aware).
    - `ParsedDocument`: Kiểm tra `doc_id`, `filename`, `pages: list[Page(number, text)]`.
    - `Task`: Kiểm tra kiểu của `deadline` (bắt buộc `datetime`), `status` (`proposed`, `confirmed`, `cancelled`), `priority`.
    - Hàm quy tắc: `can_forward()`, `schedulable()`.
  - Khảo sát `core/llm_client.py`:
    - Xem cơ chế gọi client `get_client()`, các hàm `generate()`, cấu hình provider (`fake`, `gemini`), cache dir (`.cache/llm/`).
  - Khảo sát `core/mocks.py`:
    - Kiểm tra `emails()`, `documents()`, `tasks()`, mốc thời gian cơ sở `BASE_TIME`.
  - Khảo sát phiên bản thư viện:
    - Python runtime (>= 3.10), Pydantic (V2), Streamlit, SQLite.
- [ ] **T00.3 — Lập `docs/module_b/CONTRACT_REQUESTS.md`:**
  - Ghi nhận yêu cầu hỗ trợ `thread_id` / `in_reply_to` trong `ClassifiedEmail` để theo dõi chuỗi email dời hạn.
  - Ghi nhận việc xử lý `Task.deadline` không thể null: Module B sẽ lưu tạm trong CSDL nội bộ khi `deadline is None` và chỉ xuất `contracts.Task` khi đã có hạn nộp.
  - Ghi nhận cơ chế đồng bộ thời khóa biểu / ngày bắt đầu học kỳ (`SemesterConfig`).

---

## 2. Đầu ra & Tiêu chí nghiệm thu (Definition of Done)

1. File `.gitignore` được cập nhật đầy đủ các mẫu bảo vệ dữ liệu bí mật.
2. File `docs/module_b/RECON.md` được tạo với bảng đối chiếu giả định hoàn chỉnh, chỉ rõ các điểm tương thích và điểm lệch so với code thực tế.
3. File `docs/module_b/CONTRACT_REQUESTS.md` được tạo với danh sách các câu hỏi và đề xuất gửi tới nhóm phát triển.
