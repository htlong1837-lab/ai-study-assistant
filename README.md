# Trợ lý AI học tập và lịch trình

Bài tập lớn môn Trí tuệ nhân tạo (Application Track). Hệ thống gom email, đề bài và giáo trình
thành lịch học có nhắc nhở, kèm hỏi đáp có trích dẫn trang. AI chỉ đề xuất, người dùng xác nhận.

| Module | Phụ trách | Thư mục | Trang |
|---|---|---|---|
| A — Hỏi đáp tài liệu qua API | Nam | `modules/qa/` | `views/qa.py` |
| B — Trích xuất yêu cầu bài tập | Trường | `modules/extraction/` | `views/extraction.py` |
| C — Lập lịch & nhắc nhở, khung giao diện | Long | `modules/scheduler/` | `views/scheduler.py` |
| D — Email & bảo mật | Hoàng Minh | `modules/email_security/` | `views/email_security.py` |

## Cài đặt và chạy

Cần Python 3.11 trở lên.

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
streamlit run app.py
```

Không có khóa API thì ứng dụng vẫn chạy, các chức năng AI báo "đang tắt". Muốn bật: điền
`GEMINI_API_KEY` vào `.env` (lấy miễn phí tại Google AI Studio). Muốn thử giao diện mà không tốn
lượt gọi: đặt `LLM_PROVIDER=fake`.

Chạy kiểm thử (không cần mạng): `pytest`

### Nhắc nhở qua Telegram (tuỳ chọn)

1. Nhắn `/newbot` cho @BotFather để lấy token; nhắn @userinfobot để lấy chat id.
2. Điền `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` vào `.env`, rồi nhắn một tin bất kỳ cho bot.
3. Trên trang "Lập lịch & nhắc nhở": xếp lịch → "Gửi tin thử" để kiểm tra.
4. Gửi tự động: bấm "Lưu nhắc nhở cho lệnh gửi định kỳ", rồi cho Windows Task Scheduler chạy
   `.venv\Scripts\python -m modules.scheduler.notify` mỗi 5 phút trong thư mục repo.

Không cần Telegram vẫn có thể tải file `.ics` và nhập vào Google Calendar / lịch điện thoại.

## Module A: đọc PDF và hỏi đáp có trích dẫn

Trang QA nằm trong app chung. Chạy `streamlit run app.py`, mở **Hỏi đáp tài liệu**, tải PDF/TXT/MD lên rồi đọc trong viewer. Bôi đen đoạn để hỏi theo ngữ cảnh; cũng có chế độ hỏi toàn tài liệu. Để gọi AI, nhập API key trực tiếp trong giao diện. PDF.js 6.4.299 được vendored trong repo, không cần CDN.

Giới hạn hiện tại: upload tối đa 50 MB/1000 trang; PDF.js viewer chuyển tối đa 30 MB; OCR và hỏi theo ảnh/crop chưa có. PDF được parse trong process riêng với timeout 60 giây. Hãy chạy [manual QA checklist](docs/module-a/manual-qa-checklist.md) trên trình duyệt thật; tình trạng hiện tại ở [Module A status](docs/module-a/status.md).

Benchmark cần gold answers được người dùng xác nhận từ PDF có quyền sử dụng:

```bash
python scripts/validate_qa_benchmark.py --dataset benchmarks/qa/dataset.template.jsonl
python scripts/run_qa_benchmark.py --pdf path/to/authorized.pdf --dataset benchmarks/qa/dataset.jsonl
```

Copy template thành `dataset.jsonl`, điền/review đủ gold answer, page và evidence trước khi chạy. PDF cùng benchmark cá nhân đã được gitignore. Công cụ lint/coverage tùy chọn: `pip install -e ".[dev]"`.

## Cấu trúc

```text
app.py              điểm vào, điều hướng 5 trang
core/contracts.py   6 hợp đồng dữ liệu giữa module + cổng chặn + quy tắc xác nhận
core/mocks.py       dữ liệu giả cho từng hợp đồng — dùng khi module bên cạnh chưa xong
core/llm_client.py  cửa gọi LLM chung: cache, đếm token, chạy được khi thiếu khóa
core/config.py      đọc .env, đường dẫn
modules/<module>/   logic của từng người (không import streamlit, để test được)
views/<module>.py   giao diện của từng người
tests/              pytest
specs/              đặc tả spec-kit theo từng tính năng
ai-log/             nhật ký sử dụng AI (SP3)
```

## Bắt đầu làm module của bạn

1. `git checkout main && git pull`, tạo nhánh `NNN-ten-tinh-nang`.
2. Mở Claude Code trong repo, chạy `/speckit-specify <mô tả>` → `/speckit-plan` →
   `/speckit-tasks` → `/speckit-implement`. Luật chung ở `.specify/memory/constitution.md`.
3. Lấy dữ liệu đầu vào từ `core.mocks` (ví dụ module C: `mocks.tasks()`), viết logic trong
   `modules/<module>/`, giao diện trong `views/<module>.py`.
4. `pytest` pass → mở pull request, nhờ một người khác review.
5. Ghi nhật ký AI vào `ai-log/` ngay sau mỗi phiên.

Không sửa `core/contracts.py` một mình: đổi hợp đồng cần cả nhóm đồng ý (constitution, III).
Không commit `.env`, dữ liệu thật, email thật.
