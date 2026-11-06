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
