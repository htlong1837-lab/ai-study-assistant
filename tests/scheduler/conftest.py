from datetime import date, datetime, time

import pytest

from core.contracts import Priority, Task, TaskStatus
from modules.scheduler.model import ClassSession, ScheduleSettings

MONDAY = date(2026, 11, 9)


def task(id, deadline, hours, priority=Priority.MEDIUM, status=TaskStatus.CONFIRMED):
    return Task(id=id, title=f"Việc {id}", course="AI", deadline=deadline,
                estimated_hours=hours, source="test", confidence=1.0,
                priority=priority, status=status)


@pytest.fixture
def sessions():
    return [
        ClassSession(0, time(7, 0), time(9, 30), "AI", "A203"),        # thứ 2
        ClassSession(0, time(13, 0), time(15, 30), "CSDL", "B203"),    # thứ 2
        ClassSession(2, time(13, 0), time(15, 30), "CSDL TH", "Lab"),  # thứ 4
    ]


@pytest.fixture
def settings():
    return ScheduleSettings(start=MONDAY, days=7, day_start=time(8, 0), day_end=time(20, 0),
                            max_hours_per_day=3, time_limit_s=10)


@pytest.fixture
def easy_tasks():
    """Đủ thời gian: 3 + 4 + 2 = 9 giờ trong một tuần, tối đa 3 giờ/ngày."""
    return [
        task("a", datetime(2026, 11, 11, 23, 59), 3, Priority.HIGH),
        task("b", datetime(2026, 11, 14, 23, 59), 4),
        task("c", datetime(2026, 11, 15, 23, 59), 2, Priority.LOW),
        task("p", datetime(2026, 11, 12, 23, 59), 2, status=TaskStatus.PROPOSED),
    ]


@pytest.fixture
def overload_tasks():
    """Quá tải: trước 23h59 thứ Ba chỉ có 2 ngày × 3 giờ = 6 giờ, cần 4 + 4 = 8 giờ."""
    return [
        task("low", datetime(2026, 11, 10, 23, 59), 4, Priority.LOW),
        task("high", datetime(2026, 11, 10, 23, 59), 4, Priority.HIGH),
    ]
