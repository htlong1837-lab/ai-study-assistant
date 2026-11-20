# Nhật ký sử dụng AI (SP3)

Bắt buộc theo đề bài mục II. Mỗi phiên dùng chatbot cho đồ án = một file `AI-XXX-<ten>.md`
theo [TEMPLATE.md](TEMPLATE.md), ghi **ngay sau phiên**.

- Mã tăng dần toàn nhóm, không trùng. Lấy mã kế tiếp trong bảng dưới rồi thêm dòng của mình.
- Dán nguyên văn prompt và phản hồi; hội thoại dài có thể xuất file gốc và đính kèm.
- Phần "Nhận xét", "Chỉnh sửa/loại bỏ", "Cách kiểm chứng" do **người dùng tự viết** —
  đây là phần được chấm, không nhờ AI viết.
- Đề cấm nhật ký giả: không viết lại, không "làm đẹp" hội thoại.

| Mã | Người | Ngày | Công cụ | Mục đích |
|---|---|---|---|---|
| AI-001 | Long | 2026-10-27 | | Lập kế hoạch đồ án |
| AI-002 | Long | 2026-11-06 | Claude Code (Opus 5.5) | Chiến lược, repo, khung dự án, module C, thí nghiệm, nháp SP2 phần C — [chi tiết](AI-002-long-claude-code.md) |
| AI-A001 | Hưng | 2026-11-08 | Antigravity | Module A Phase 0: Phân tích kiến trúc & chuẩn bị tài liệu — [chi tiết](AI-A001-module-a-phase0.md) |
| AI-A002 | Hưng | 2026-11-09 | Codex | Review và sửa lỗi Module A — [chi tiết](AI-A002-codex-module-a-review-fixes.md) |
| AI-A003 | Hưng | 2026-11-10 | Antigravity | Xác nhận thu hồi key an toàn — [chi tiết](AI-A003-key-revocation-confirmed.md) |
| AI-A004 | Hưng | 2026-11-11 | Antigravity | Xử lý fixture chưa chắc chắn — [chi tiết](AI-A004-fixture-uncertain.md) |
| AI-A005 | Hưng | 2026-11-12 | Antigravity | Hoàn thiện fixture và test Module A — [chi tiết](AI-A005-fixture-confirmed-fake.md) |
| AI-B001 | Duy | 2026-11-08 | Antigravity (Gemini 3.8 Flash) | Toàn bộ Phase 1–7 Module B: CSDL SQLite, chuẩn hoá ngày giờ tiếng Việt, trích xuất LLM có cấu trúc, phát hiện mâu thuẫn & dời hạn, máy trạng thái duyệt task, benchmark 20 bài tập thật, tích hợp email đã duyệt từ Module D — [chi tiết](AI-B001-duy-antigravity-code.md) |
| AI-D001 | Hoàng Minh | 2026-11-08 | Antigravity (Claude Sonnet 4.6 Thinking) | Phân tích chức năng module D — [chi tiết](AI-D001-minh-antigravity-review.md) |
| AI-D002 | Hoàng Minh | 2026-11-08 | Claude Web (như ghi trong nhật ký) | Kế hoạch chi tiết module D — [chi tiết](AI-D002-minh-claude-plan.md) |
| AI-D003 | Hoàng Minh | 2026-11-09 | Antigravity (Claude Sonnet 4.6 Thinking) | Khung pipeline, đọc .eml (WP-00, WP-01) — [chi tiết](AI-D003-minh-antigravity-code.md) |
| AI-D004 | Hoàng Minh | 2026-11-11 | Antigravity | Phân loại TF-IDF + LR, LLM zero-shot, so sánh F1 — [chi tiết](AI-D004-minh-antigravity-classifiers.md) |
| AI-A001 | Nam | 2026-11-08 | Google Antigravity (Gemini 3.8 Flash) | Rà soát bảo mật và lập kế hoạch Module A — [chi tiết](AI-A001-module-a-phase0.md) |
| AI-A002 | Nam | 2026-11-09 | Codex (GPT-6) | Thực thi fixes Module A theo review — [chi tiết](AI-A002-codex-module-a-review-fixes.md) |
| AI-A003 | Nam | 2026-11-09 | Codex (GPT-6) | Ghi nhận thu hồi API key cũ — [chi tiết](AI-A003-key-revocation-confirmed.md) |
| AI-A004 | Nam | 2026-11-09 | Codex (GPT-6) | Ghi nhận fixture lịch sử chưa xác định — [chi tiết](AI-A004-fixture-uncertain.md) |
| AI-A005 | Nam | 2026-11-09 | Codex (GPT-6) | Xác nhận fixture key-like là dữ liệu giả — [chi tiết](AI-A005-fixture-confirmed-fake.md) |
| AI-D005 | Hoàng Minh | 2026-11-14 | Antigravity | Ẩn danh PII, tóm tắt email, quét URL heuristic — [chi tiết](AI-D005-minh-antigravity-wp05-wp06.md) |
| AI-D006 | Hoàng Minh | 2026-11-17 | Gemini | VirusTotal, cache SQLite, quét file đính kèm — [chi tiết](AI-D006-minh-gemini-wp07-wp08.md) |
