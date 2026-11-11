# AI-A002 — Thực thi fixes Module A theo review PR

| Trường thông tin | Nội dung |
|---|---|
| Mã tương tác | AI-A002 |
| Người thực hiện | Nam (A) / Codex hỗ trợ |
| Thời gian | 2026-11-09 16:04 ICT |
| Công cụ AI | Codex — GPT-6 |
| Mục đích | Thực hiện `docs/module-a/plan-fixes-from-review.md` sau khi người dùng duyệt. |
| Prompt đầy đủ | Xem Hội thoại bên dưới. |
| Phản hồi đầy đủ | Xem Hội thoại bên dưới. |
| Nhận xét, đánh giá | Chưa nhận được đánh giá của người dùng; không tự ghi thay người dùng. |
| Nội dung được sử dụng | Refactor QA sang kiến trúc chung, cập nhật test/imports, dọn SDK/spec/scripts và cập nhật audit bảo mật. |
| Nội dung chỉnh sửa hoặc loại bỏ | Xóa implementation trùng trong `src/`, SDK cũ khỏi requirements và sáu script Specify thuộc PR; giữ nguyên `.env` cục bộ và không rewrite lịch sử. |
| Cách kiểm chứng | `python -m pytest -q` từ repo root; khởi động `streamlit run app.py`; audit Git chỉ xuất metadata và tên file. |
| Kết quả áp dụng | Các thay đổi đang trong working tree của nhánh `feature/module-A-plan`; chưa commit. |

## Hội thoại

### Lượt 1

**Prompt:**

```
ok tôi đã duyệt file bạn tạo là plan-fixes-from-review. Bây giờ thực thi sửa dựa trên file này nhé
```

**Phản hồi:**

```
Đã thực hiện các blockers trong plan:

- Thay fixture key-like trong test bằng placeholder an toàn. Audit các refs Git local tìm thấy fixture trong một commit; không tìm thấy bằng chứng đủ để kết luận đó là credential hợp lệ. `.env` không được track và không bị đọc. Chủ sở hữu cần xác nhận; thu hồi key nếu từng là thật. Không rewrite lịch sử.
- Chuyển QA sang `modules/qa/`, dùng `ParsedDocument`/`Page` từ `core/contracts.py` và `LLMClient` từ `core/llm_client.py`. Tích hợp trang `views/qa.py` vào app chung, với dữ liệu mẫu từ contract dùng chung để không bỏ qua cổng file an toàn của Module D.
- Bỏ implementation `src/` trùng, dependency `google-generativeai`, đổi spec sang `specs/005-document-qna/`, và loại sáu script Python Specify khỏi nhánh.
- Cập nhật test/imports, verification log, `SECURITY_TODO.md` và checklist trong plan.

Kiểm chứng: `python -m pytest -q` đạt 91 passed; `streamlit run app.py` khởi động thành công. Có một cảnh báo FutureWarning từ PyMuPDF `fitz`.

Việc còn cần bạn xác nhận ngoài code: key-like fixture hoặc key trong `.env` trước đây có từng là credential thật không. Nếu có, hãy thu hồi key trong Google AI Studio.
```
