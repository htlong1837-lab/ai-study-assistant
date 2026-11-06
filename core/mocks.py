"""Dữ liệu giả cho từng hợp đồng, để mỗi module làm việc mà không chờ module bên cạnh.

Mỗi hàm trả bản mới mỗi lần gọi. Thời gian tính từ BASE_TIME cố định để test ổn định.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .contracts import (
    ClassifiedEmail, EmailLabel, Page, ParsedDocument, Priority, Reminder, ReminderChannel,
    SafeAttachment, SafetyStatus, StudyBlock, Task, TaskStatus,
)

BASE_TIME = datetime(2026, 11, 9, 8, 0)  # thứ Hai


def _t(days: float = 0, hours: float = 0) -> datetime:
    return BASE_TIME + timedelta(days=days, hours=hours)


def emails() -> list[ClassifiedEmail]:
    return [
        ClassifiedEmail(
            id="e-001", sender="gv.ai@uni.edu.vn", subject="[AI] Đề bài tập lớn giữa kỳ",
            body="Các nhóm nộp báo cáo SP1 trước 23h59 thứ Sáu tuần sau. Đề bài đính kèm.",
            received_at=_t(-3), label=EmailLabel.ASSIGNMENT, safety=SafetyStatus.SAFE,
            summary="Nộp SP1 trước 23h59 thứ Sáu tuần sau.",
            attachments=["data/sample/de_bai_ai.pdf"], label_confidence=0.95),
        ClassifiedEmail(
            id="e-002", sender="phongdaotao@uni.edu.vn", subject="Đổi phòng học CSDL",
            body="Lớp CSDL chiều thứ Tư chuyển sang phòng B203.",
            received_at=_t(-2), label=EmailLabel.SCHEDULE, safety=SafetyStatus.SAFE,
            summary="CSDL thứ Tư chuyển phòng B203.", label_confidence=0.9),
        ClassifiedEmail(
            id="e-003", sender="hoc-bong@uni-edu-vn.top", subject="Nhận học bổng 10 triệu",
            body="Bấm vào link và nhập mật khẩu email trường để nhận học bổng.",
            received_at=_t(-1), label=EmailLabel.PHISHING, safety=SafetyStatus.MALICIOUS,
            label_confidence=0.88),
        ClassifiedEmail(
            id="e-004", sender="clb.tinhoc@gmail.com", subject="Tài liệu ôn thi",
            body="Tải tài liệu ôn thi tại link rút gọn bit.ly/xxxx",
            received_at=_t(-1, 3), label=EmailLabel.ANNOUNCEMENT, safety=SafetyStatus.SUSPICIOUS,
            attachments=["data/sample/on_thi.zip"], label_confidence=0.6),
    ]


def attachments() -> list[SafeAttachment]:
    return [
        SafeAttachment(path="data/sample/de_bai_ai.pdf", sha256="1" * 64, email_id="e-001"),
        SafeAttachment(path="data/sample/giao_trinh_csdl.pdf", sha256="2" * 64, email_id="e-001"),
        SafeAttachment(path="data/sample/lich_thi.pdf", sha256="3" * 64, email_id="e-002"),
    ]


def documents() -> list[ParsedDocument]:
    return [
        ParsedDocument(doc_id="d-001", filename="de_bai_ai.pdf", pages=[
            Page(1, "ĐỀ BÀI TẬP LỚN – HỌC PHẦN TRÍ TUỆ NHÂN TẠO"),
            Page(2, "Sản phẩm 1 – Báo cáo phân tích sự cần thiết của hệ thống."),
            Page(5, "Nhật ký sử dụng AI là sản phẩm bắt buộc."),
        ]),
        ParsedDocument(doc_id="d-002", filename="giao_trinh_csdl.pdf", pages=[
            Page(1, "Chương 1. Tổng quan cơ sở dữ liệu"),
            Page(2, "Chương 2. Mô hình quan hệ, khóa chính, khóa ngoại"),
        ]),
        ParsedDocument(doc_id="d-003", filename="lich_thi.pdf", pages=[
            Page(1, "Thi cuối kỳ CSDL: 8h00 ngày 15/12/2026, phòng A101"),
        ]),
    ]


def tasks() -> list[Task]:
    return [
        Task(id="t-001", title="Báo cáo SP1 – phân tích sự cần thiết", course="Trí tuệ nhân tạo",
             deadline=_t(11, 15 + 59 / 60), estimated_hours=6, source="email:e-001",
             confidence=0.92, priority=Priority.HIGH, status=TaskStatus.CONFIRMED),
        Task(id="t-002", title="Bài tập chương 2 CSDL", course="Cơ sở dữ liệu",
             deadline=_t(4, 15 + 59 / 60), estimated_hours=3, source="giao_trinh_csdl.pdf#p2",
             confidence=0.85, priority=Priority.MEDIUM, status=TaskStatus.CONFIRMED),
        Task(id="t-003", title="Ôn thi cuối kỳ CSDL", course="Cơ sở dữ liệu",
             deadline=_t(36), estimated_hours=12, source="lich_thi.pdf#p1",
             confidence=0.97, priority=Priority.HIGH, status=TaskStatus.CONFIRMED),
        Task(id="t-004", title="Nhật ký sử dụng AI (bản chốt)", course="Trí tuệ nhân tạo",
             deadline=_t(28), estimated_hours=4, source="de_bai_ai.pdf#p5",
             confidence=0.7, priority=Priority.MEDIUM, status=TaskStatus.PROPOSED),
    ]


def study_blocks() -> list[StudyBlock]:
    return [
        StudyBlock(task_id="t-002", start=_t(0, 11), end=_t(0, 13)),
        StudyBlock(task_id="t-001", start=_t(1, 6), end=_t(1, 9)),
        StudyBlock(task_id="t-001", start=_t(2, 11), end=_t(2, 14)),
        StudyBlock(task_id="t-002", start=_t(3, 12), end=_t(3, 13)),
    ]


def reminders() -> list[Reminder]:
    return [
        Reminder(task_id="t-002", remind_at=_t(0, 10.5), channel=ReminderChannel.TELEGRAM,
                 message="30 phút nữa: Bài tập chương 2 CSDL (2 giờ)"),
        Reminder(task_id="t-001", remind_at=_t(1, 5.5), channel=ReminderChannel.TELEGRAM,
                 message="30 phút nữa: Báo cáo SP1 (3 giờ)"),
        Reminder(task_id="t-001", remind_at=_t(10, 12), channel=ReminderChannel.EMAIL,
                 message="Còn 1 ngày: hạn nộp Báo cáo SP1 lúc 23h59 ngày mai"),
    ]
