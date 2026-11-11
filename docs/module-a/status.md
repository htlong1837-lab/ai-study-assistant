# Module A status

Cập nhật: 2026-11-11

| Hạng mục | Trạng thái | Bằng chứng / giới hạn |
|---|---|---|
| Phase G: kiểm tra nền tảng | G.2–G.5 đạt; G.1 một phần | Bằng chứng chi tiết ở `docs/qa/review-compliance.md`. G.1 còn browser/remote CI/team review. Không có file `src/` được track; thư mục ignored cục bộ giữ cache và PDF người dùng. |
| Phase 1: nền tảng tin cậy | Code và test đã triển khai | NFC/ligature/hyphenation, model/rejection, parser schema + một lần sửa JSON, prompt injection, verifier và cache verified theo session. Core disk response cache tắt cho QA. |
| Phase 2: backend reader | Code hoàn tất; có kiểm thử | Actions, BM25, QA service, validation/dedup event, matching qua trang lân cận và hai trang liền kề, stable ThreadStore, lịch sử và export Markdown. |
| Phase 3: PDF reader | Code đã triển khai; cần browser QA | Upload tối đa 50 MB/1000 trang; reader transport tối đa 30 MB. PDF.js 6.4.299; text layer, toolbar trang/zoom/theme, popup chọn, chat, citation goto/highlight, release canvas ngoài vùng nhìn. Node chưa cài cục bộ nên test JS skip; CI cài Node. Chưa xác nhận browser, PDF 300 trang và Chrome/Edge/Firefox. |
| Phase 4.1–4.2: benchmark | Validator/runner đã triển khai; chưa có benchmark thật | Template 30 dòng còn `needs_human_review`; cần điền gold answers/evidence từ PDF có quyền sử dụng. Answer score hiện là normalized exact match (không phải judge ngữ nghĩa); cost để `null` vì chưa xác minh giá model. |
| Phase 4.3: latency và SC | Chưa đo | Cần API key do người dùng tự nhập và dataset đã review. Không ghi SC là Met khi chưa có kết quả. |
| Phase 4.4: scan/crop | Một phần | Phát hiện thiếu lớp text/trang rỗng, báo PDF scan. OCR và hỏi theo ảnh/crop còn cần binary/model và đồng ý mở rộng core từ nhóm. |
| Phase 4.5: upload an toàn | Code hoàn tất cho upload dạng bytes | Whitelist, PDF magic bytes, 50 MB/1000 trang, temp file cleanup và parser process timeout 60 giây. Path traversal/symlink không áp dụng vì ứng dụng không nhận đường dẫn từ người dùng. |
| Phase 4.6: logging | Đã triển khai và có test | JSON logging metadata, che API key; không ghi nội dung câu hỏi/tài liệu. |
| Phase 5.1: kiểm tra tự động | Đạt cục bộ | `pytest --cov=modules/qa --cov-fail-under=80 -q`: **206 passed, 1 skipped, coverage 86.94%**. Ruff pass. JS logic test skip vì Node chưa cài cục bộ; CI cài Node. |
| Phase 5.2: tích hợp app và module khác | Một phần | AppTest cho `app.py`, QA view, điều hướng và xóa key khi rời trang đều pass. Cần bạn xác minh browser và chuyển qua lại với B/D. |
| Phase 5.3: tài liệu | Code/docs hoàn tất | README, changelog, quyết định, trạng thái, compliance report và checklist được đồng bộ; benchmark thật ghi rõ chưa đo. |
| Phase 5.4–5.6: nhật ký và bàn giao | Còn việc người dùng/nhóm | Người dùng điền nội dung nhật ký AI đúng sự thật; cần checklist trình duyệt, review nhóm và merge/PR. |

## Việc còn cần người dùng thực hiện

1. Mở `streamlit run app.py`, thử reader trên Chrome/Edge/Firefox và điền `manual-qa-checklist.md`.
2. Dùng PDF được phép chia sẻ, hoàn thành 30 câu hỏi cùng gold answer/page/evidence trong `benchmarks/qa/dataset.jsonl`.
3. Chạy benchmark với API key nhập cục bộ, sau đó mới báo latency/cost và kết quả chất lượng.
4. Cung cấp kết quả thử PDF 300 trang, nhiều cột, công thức và PDF scan. OCR/crop ảnh cần nhóm đồng ý và môi trường có công cụ phù hợp trước khi phát triển.
5. Hoàn thiện nhật ký AI theo trải nghiệm thực tế và xin review/merge theo quy trình nhóm.
