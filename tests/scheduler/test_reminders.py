from datetime import datetime


from core.contracts import Priority, ReminderChannel, StudyBlock
from modules.scheduler import notify
from modules.scheduler.reminders import (
    TelegramSender, _fold, load_reminders, make_reminders, save_reminders, send_due, to_ics,
)

from .conftest import task

TASKS = [task("a", datetime(2026, 11, 11, 23, 59), 2, Priority.HIGH)]
BLOCKS = [StudyBlock("a", datetime(2026, 11, 10, 9, 0), datetime(2026, 11, 10, 11, 0))]


def test_make_reminders_before_block_and_deadline():
    rs = make_reminders(BLOCKS, TASKS, before_block_min=30, before_deadline_h=24)
    assert [r.remind_at for r in rs] == [datetime(2026, 11, 10, 8, 30),
                                        datetime(2026, 11, 10, 23, 59)]
    assert "09:00" in rs[0].message and "Hạn nộp" in rs[1].message
    assert all(r.channel is ReminderChannel.TELEGRAM for r in rs)


def test_ics_structure():
    ics = to_ics(BLOCKS, TASKS, now=datetime(2026, 11, 6))
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert ics.count("BEGIN:VEVENT") == 2 and ics.count("BEGIN:VALARM") == 2
    assert "DTSTART:20261110T090000" in ics and "TRIGGER:-PT30M" in ics
    assert "TRIGGER:-PT1440M" in ics
    assert all(len(line.encode("utf-8")) <= 75 for line in ics.split("\r\n"))


def test_ics_escapes_special_chars():
    t = task("x", datetime(2026, 11, 11), 1)
    t.title = "Bài 1, 2; xong\\hết"
    ics = to_ics([], [t]).replace("\r\n ", "")
    assert "Bài 1\\, 2\\; xong\\\\hết" in ics


def test_fold_does_not_split_multibyte():
    folded = _fold("SUMMARY:" + "ộ" * 60)
    lines = folded.split("\r\n ")
    assert len(lines) > 1 and "".join(lines) == "SUMMARY:" + "ộ" * 60
    assert all(len(line.encode("utf-8")) <= 75 for line in lines)


def test_send_due_sends_each_once(tmp_path):
    rs = make_reminders(BLOCKS, TASKS)
    store, outbox = tmp_path / "sent.json", []
    now = datetime(2026, 11, 10, 8, 40)
    assert len(send_due(rs, now, outbox.append, store)) == 1
    assert send_due(rs, now, outbox.append, store) == []
    assert len(outbox) == 1 and "09:00" in outbox[0]


def test_send_due_skips_future_and_stale(tmp_path):
    rs = make_reminders(BLOCKS, TASKS)
    outbox = []
    send_due(rs, datetime(2026, 11, 10, 8, 0), outbox.append, tmp_path / "s.json")  # chưa tới
    send_due(rs, datetime(2026, 11, 10, 12, 0), outbox.append, tmp_path / "s.json")  # quá 1 giờ
    assert outbox == []


def test_save_and_load_roundtrip(tmp_path):
    rs = make_reminders(BLOCKS, TASKS)
    save_reminders(rs, tmp_path / "r.json")
    assert load_reminders(tmp_path / "r.json") == rs
    assert load_reminders(tmp_path / "missing.json") == []


def test_telegram_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    assert TelegramSender.from_env() is None
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    assert TelegramSender.from_env() is not None


def test_notify_without_config(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    assert notify.main() == 1
    assert "Chưa cấu hình" in capsys.readouterr().out
