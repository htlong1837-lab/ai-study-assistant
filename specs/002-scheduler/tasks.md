# Tasks: Lập lịch học và nhắc nhở (Module C)

**Input**: `/specs/002-scheduler/` · **Tests**: có (constitution IV), viết trước khi cài đặt.

## Phase 1: Setup

- [x] T001 Thêm `ortools` vào `requirements.txt`; biến `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` vào `.env.example`
- [x] T002 [P] Tạo `data/sample/thoi_khoa_bieu.csv` (5–6 buổi/tuần)

## Phase 2: Foundational

- [x] T003 [P] Test + cài đặt `modules/scheduler/model.py` (ClassSession, ScheduleSettings kiểm tra hợp lệ)
- [x] T004 [P] Test + cài đặt `modules/scheduler/timetable.py` (đọc CSV, báo dòng lỗi)
- [x] T005 Test + cài đặt `modules/scheduler/slots.py` (ô rảnh, gộp ô thành khối)
- [x] T006 Test + cài đặt `modules/scheduler/metrics.py` (`validate`, `evaluate`)

## Phase 3: US1 + US2 — Xếp lịch và so sánh (P1) 🎯 MVP

- [x] T007 [US1] Test chung cho mọi thuật toán (tham số hoá): đủ giờ, không trùng lớp, ≤ giờ/ngày, trước hạn, chỉ task confirmed, quá tải ưu tiên việc quan trọng — `tests/scheduler/test_algorithms.py`
- [x] T008 [US1] Cài đặt `modules/scheduler/edf.py`
- [x] T009 [US1] Cài đặt `modules/scheduler/cpsat.py`
- [x] T010 [US2] Cài đặt `schedule()` trong `modules/scheduler/__init__.py`; test SC-004 (CP-SAT không thiếu nhiều hơn EDF) và SC-003 (thời gian)

## Phase 4: US3 — Nhắc nhở (P2)

- [x] T011 [US3] Test + cài đặt `make_reminders`, `to_ics` trong `modules/scheduler/reminders.py`
- [x] T012 [US3] Test + cài đặt `TelegramSender`, `send_due` (đúng một lần), lưu/đọc lịch
- [x] T013 [US3] Cài đặt `modules/scheduler/notify.py`

## Phase 5: US4 — Giao diện (P2)

- [x] T014 [US4] Viết lại `views/scheduler.py`: xác nhận task, TKB, cài đặt, chọn thuật toán, chỉ số, lịch tuần, nhắc nhở
- [x] T015 [US4] Cập nhật `tests/test_pages.py` cho trang mới

## Phase 6: Polish

- [x] T016 Chạy toàn bộ `pytest`, chạy app và kiểm tra bằng trình duyệt
- [x] T017 Cập nhật README (Telegram, lệnh notify)

## Dependencies

Setup → Foundational → US1/US2 → US3 → US4 → Polish.
