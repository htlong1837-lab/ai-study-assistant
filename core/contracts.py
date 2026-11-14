"""Hợp đồng dữ liệu giữa 4 module (constitution, nguyên tắc III).

Luồng: D → ClassifiedEmail/SafeAttachment → A, B;  A → ParsedDocument → B;
       B → Task → C;  C → StudyBlock, Reminder → người dùng.

Đổi một trường ở đây là thay đổi phá vỡ: cần PR riêng, cả nhóm đồng ý, sửa mock cùng lúc.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Iterable


class SafetyStatus(str, Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"


class EmailLabel(str, Enum):
    ASSIGNMENT = "assignment"      # thông báo bài tập
    SCHEDULE = "schedule"          # lịch học, đổi lịch
    ANNOUNCEMENT = "announcement"  # thông báo chung
    SPAM = "spam"
    PHISHING = "phishing"
    OTHER = "other"


class TaskStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReminderChannel(str, Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    ICS = "ics"
    IN_APP = "in_app"


# --- tiện ích kiểm tra ---

def _enum(cls: type[Enum], value, name: str):
    try:
        return cls(value)
    except ValueError:
        allowed = ", ".join(m.value for m in cls)
        raise ValueError(f"{name}: '{value}' không hợp lệ (cho phép: {allowed})") from None


def _not_blank(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} không được rỗng")


def _ratio(value: float, name: str) -> None:
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} phải trong khoảng 0–1, nhận {value}")


def _datetime(value, name: str) -> None:
    if not isinstance(value, datetime):
        raise ValueError(f"{name} phải là datetime")


# --- D → B ---

@dataclass
class ClassifiedEmail:
    id: str
    sender: str
    subject: str
    body: str
    received_at: datetime
    label: EmailLabel
    safety: SafetyStatus
    summary: str | None = None
    attachments: list[str] = field(default_factory=list)
    label_confidence: float = 1.0

    def __post_init__(self):
        _not_blank(self.id, "id")
        _datetime(self.received_at, "received_at")
        self.label = _enum(EmailLabel, self.label, "label")
        self.safety = _enum(SafetyStatus, self.safety, "safety")
        _ratio(self.label_confidence, "label_confidence")


# --- D → A ---

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class SafeAttachment:
    path: str
    sha256: str
    email_id: str

    def __post_init__(self):
        _not_blank(self.path, "path")
        _not_blank(self.email_id, "email_id")
        if not _SHA256.match(self.sha256.lower()):
            raise ValueError("sha256 phải là 64 ký tự hex")
        self.sha256 = self.sha256.lower()


# --- A → B ---

@dataclass
class Page:
    number: int
    text: str

    def __post_init__(self):
        if self.number < 1:
            raise ValueError(f"number phải ≥ 1, nhận {self.number}")


@dataclass
class ParsedDocument:
    doc_id: str
    filename: str
    pages: list[Page] = field(default_factory=list)

    def __post_init__(self):
        _not_blank(self.doc_id, "doc_id")
        numbers = [p.number for p in self.pages]
        if len(numbers) != len(set(numbers)):
            raise ValueError("pages có số trang bị trùng")

    def text_of(self, numbers: Iterable[int]) -> str:
        wanted = set(numbers)
        return "\n".join(p.text for p in self.pages if p.number in wanted)


# --- B → C ---

@dataclass
class Task:
    id: str
    title: str
    course: str
    deadline: datetime
    estimated_hours: float
    source: str
    confidence: float
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PROPOSED

    def __post_init__(self):
        _not_blank(self.id, "id")
        _not_blank(self.title, "title")
        _not_blank(self.source, "source")
        _datetime(self.deadline, "deadline")
        if float(self.estimated_hours) <= 0:
            raise ValueError("estimated_hours phải > 0")
        _ratio(self.confidence, "confidence")
        self.priority = _enum(Priority, self.priority, "priority")
        self.status = _enum(TaskStatus, self.status, "status")

    def confirm(self) -> None:
        """Người dùng xác nhận đề xuất của AI (nguyên tắc I)."""
        if self.status is not TaskStatus.PROPOSED:
            raise ValueError(f"chỉ xác nhận được task 'proposed', task đang '{self.status.value}'")
        self.status = TaskStatus.CONFIRMED

    def cancel(self) -> None:
        if self.status is TaskStatus.CANCELLED:
            raise ValueError("task đã bị huỷ")
        self.status = TaskStatus.CANCELLED


# --- C → người dùng ---

@dataclass
class StudyBlock:
    task_id: str
    start: datetime
    end: datetime

    def __post_init__(self):
        _not_blank(self.task_id, "task_id")
        _datetime(self.start, "start")
        _datetime(self.end, "end")
        if self.end <= self.start:
            raise ValueError("end phải sau start")

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600


@dataclass
class Reminder:
    task_id: str
    remind_at: datetime
    channel: ReminderChannel
    message: str

    def __post_init__(self):
        _not_blank(self.task_id, "task_id")
        _datetime(self.remind_at, "remind_at")
        self.channel = _enum(ReminderChannel, self.channel, "channel")


# --- quy tắc chung ---

def can_forward(email: ClassifiedEmail, allow_suspicious: bool = False) -> bool:
    """Cổng chặn (nguyên tắc II): malicious không bao giờ đi tiếp."""
    if email.safety is SafetyStatus.SAFE:
        return True
    if email.safety is SafetyStatus.SUSPICIOUS:
        return allow_suspicious
    return False


def schedulable(tasks: Iterable[Task]) -> list[Task]:
    """Chỉ task đã được người dùng xác nhận mới được xếp lịch (nguyên tắc I)."""
    return [t for t in tasks if t.status is TaskStatus.CONFIRMED]
