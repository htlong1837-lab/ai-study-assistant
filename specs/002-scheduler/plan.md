# Implementation Plan: Lập lịch học và nhắc nhở (Module C)

**Branch**: `002-scheduler` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

## Summary

Rời rạc hoá thời gian thành các ô 30 phút, bỏ các ô trùng giờ lên lớp và ngoài khung giờ học.
Hai bộ xếp lịch dùng chung đầu vào/đầu ra: **EDF** tham lam (baseline) và **CP-SAT** (OR-Tools)
mô hình hoá bài toán thỏa mãn ràng buộc có tối ưu với mục tiêu nhiều tầng. Một hàm `evaluate`
tính chỉ số giống nhau cho cả hai. Nhắc nhở sinh từ lịch, xuất `.ics` (viết tay theo RFC 5545)
và gửi Telegram qua Bot API (urllib, không thêm thư viện). Trang Streamlit vẽ lịch tuần bằng Altair.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: ortools ≥ 9.10 (CP-SAT); altair (đi kèm Streamlit) cho lịch tuần;
pandas. Không thêm thư viện cho `.ics` và Telegram.

**Storage**: Lịch gần nhất lưu `.cache/schedule.json` để lệnh gửi nhắc nhở chạy độc lập;
nhắc nhở đã gửi lưu `.cache/reminders_sent.json`.

**Testing**: pytest, offline; Telegram được thay bằng hàm gửi giả trong test.

**Performance Goals**: 4 tuần × 15 nhiệm vụ < 10 giây (giới hạn thời gian CP-SAT mặc định 10 s).

**Constraints**: Logic trong `modules/scheduler/` không import Streamlit.

**Scale/Scope**: 1 người dùng; ≤ 35 ngày; ≤ 30 nhiệm vụ; ≈ 1 000 ô thời gian.

## Constitution Check

| Nguyên tắc | Tuân thủ | Đạt |
|---|---|---|
| I. AI chỉ đề xuất | Đầu vào lọc qua `schedulable()`; UI cho xác nhận task trước khi xếp | ✅ |
| II. Chặn tại cổng | Không áp dụng (C không nhận email/file) | — |
| III. Hợp đồng chung | Dùng `Task`, `StudyBlock`, `Reminder`; không sửa `core/contracts.py` | ✅ |
| IV. Đo được | `evaluate()` + so sánh EDF/CP-SAT; test cho mọi ràng buộc | ✅ |
| V. Đơn giản, máy lạ | Không cần khóa API; Telegram tùy chọn | ✅ |

## Project Structure

```text
modules/scheduler/
├── model.py        # ClassSession, ScheduleSettings, Slot, ScheduleResult
├── timetable.py    # đọc CSV thời khoá biểu → ClassSession + danh sách lỗi
├── slots.py        # sinh ô rảnh; gộp ô liên tiếp thành StudyBlock
├── edf.py          # baseline Earliest Deadline First
├── cpsat.py        # mô hình CP-SAT
├── metrics.py      # evaluate(), validate()
├── reminders.py    # make_reminders, to_ics, TelegramSender, send_due, lưu/đọc lịch
├── notify.py       # python -m modules.scheduler.notify (chạy định kỳ bằng Task Scheduler)
└── __init__.py     # schedule(tasks, sessions, settings, algorithm)
views/scheduler.py
data/sample/thoi_khoa_bieu.csv
tests/scheduler/    # test từng file
```

## Complexity Tracking

Không có vi phạm.
