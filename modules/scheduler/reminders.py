"""Nhắc nhở: sinh từ lịch, xuất iCalendar (.ics), gửi Telegram đúng một lần. Xem research R5."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from core import config
from core.contracts import Reminder, ReminderChannel, StudyBlock, Task, schedulable

STORE = config.CACHE_DIR / "reminders.json"       # nhắc nhở của lịch gần nhất
SENT_STORE = config.CACHE_DIR / "reminders_sent.json"


# --- sinh nhắc nhở ---

def make_reminders(blocks: list[StudyBlock], tasks: list[Task], before_block_min: int = 30,
                   before_deadline_h: int = 24,
                   channel: ReminderChannel = ReminderChannel.TELEGRAM) -> list[Reminder]:
    titles = {t.id: t.title for t in tasks}
    out = [Reminder(
        task_id=b.task_id, remind_at=b.start - timedelta(minutes=before_block_min), channel=channel,
        message=f"⏰ {b.start:%H:%M} học: {titles.get(b.task_id, b.task_id)} "
                f"({b.hours:g} giờ, đến {b.end:%H:%M})") for b in blocks]
    for t in schedulable(tasks):
        out.append(Reminder(
            task_id=t.id, remind_at=t.deadline - timedelta(hours=before_deadline_h), channel=channel,
            message=f"📌 Hạn nộp {t.title} ({t.course}): {t.deadline:%H:%M %d/%m}"))
    return sorted(out, key=lambda r: r.remind_at)


# --- iCalendar (RFC 5545) ---

def _escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\n", "\\n"))


def _fold(line: str) -> str:
    """Gập dòng dài hơn 75 byte (UTF-8), không cắt giữa ký tự."""
    parts, cur, limit = [], b"", 75
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > limit:
            parts.append(cur.decode("utf-8"))
            cur, limit = b"", 74  # dòng tiếp theo bắt đầu bằng một dấu cách
        cur += b
    parts.append(cur.decode("utf-8"))
    return "\r\n ".join(parts)


def _dt(d: datetime) -> str:
    return d.strftime("%Y%m%dT%H%M%S")  # giờ "floating" = giờ địa phương của thiết bị


def _event(uid, start, end, summary, description, alarm_minutes, stamp) -> list[str]:
    return [
        "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}", f"DTSTART:{_dt(start)}",
        f"DTEND:{_dt(end)}", f"SUMMARY:{_escape(summary)}", f"DESCRIPTION:{_escape(description)}",
        "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_escape(summary)}",
        f"TRIGGER:-PT{alarm_minutes}M", "END:VALARM", "END:VEVENT",
    ]


def to_ics(blocks: list[StudyBlock], tasks: list[Task], before_block_min: int = 30,
           before_deadline_h: int = 24, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%dT%H%M%SZ")
    by_id = {t.id: t for t in tasks}
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ai-study-assistant//vi",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:Lịch học (Trợ lý AI)"]
    for b in blocks:
        t = by_id.get(b.task_id)
        title = t.title if t else b.task_id
        desc = f"Môn: {t.course}\nHạn nộp: {t.deadline:%H:%M %d/%m/%Y}" if t else ""
        lines += _event(f"{b.task_id}-{_dt(b.start)}@ai-study-assistant", b.start, b.end,
                        f"📚 {title}", desc, before_block_min, stamp)
    for t in schedulable(tasks):
        lines += _event(f"{t.id}-deadline@ai-study-assistant", t.deadline,
                        t.deadline + timedelta(minutes=1), f"📌 Hạn nộp: {t.title}",
                        f"Môn: {t.course}\nNguồn: {t.source}", before_deadline_h * 60, stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


# --- Telegram ---

class TelegramSender:
    def __init__(self, token: str, chat_id: str, timeout: float = 10):
        self.token, self.chat_id, self.timeout = token, chat_id, timeout

    @classmethod
    def from_env(cls) -> "TelegramSender | None":
        token, chat = config.env("TELEGRAM_BOT_TOKEN"), config.env("TELEGRAM_CHAT_ID")
        return cls(token, chat) if token and chat else None

    def __call__(self, text: str) -> None:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=json.dumps({"chat_id": self.chat_id, "text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                ok = json.load(resp).get("ok")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Telegram từ chối ({e.code}): kiểm tra token và chat id") from None
        except urllib.error.URLError as e:
            raise RuntimeError(f"Không kết nối được Telegram: {e.reason}") from None
        if not ok:
            raise RuntimeError("Telegram trả về lỗi")


# --- gửi đúng một lần ---

def _key(r: Reminder) -> str:
    return f"{r.task_id}|{r.remind_at.isoformat()}|{r.channel.value}"


def _load_sent(path: Path) -> set[str]:
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def send_due(reminders: list[Reminder], now: datetime, send: Callable[[str], None],
             store_path: Path = SENT_STORE, grace: timedelta = timedelta(hours=1)) -> list[Reminder]:
    """Gửi nhắc nhở đã đến giờ (trễ tối đa `grace`) và chưa từng gửi. Trả danh sách đã gửi."""
    sent = _load_sent(store_path)
    done = []
    for r in sorted(reminders, key=lambda r: r.remind_at):
        if r.remind_at > now or now - r.remind_at > grace or _key(r) in sent:
            continue
        send(r.message)
        sent.add(_key(r))
        done.append(r)
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_text(json.dumps(sorted(sent)), encoding="utf-8")
    return done


# --- lưu nhắc nhở của lịch gần nhất (cho lệnh notify) ---

def save_reminders(reminders: list[Reminder], path: Path = STORE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([{
        "task_id": r.task_id, "remind_at": r.remind_at.isoformat(),
        "channel": r.channel.value, "message": r.message} for r in reminders],
        ensure_ascii=False, indent=1), encoding="utf-8")


def load_reminders(path: Path = STORE) -> list[Reminder]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [Reminder(task_id=d["task_id"], remind_at=datetime.fromisoformat(d["remind_at"]),
                     channel=d["channel"], message=d["message"]) for d in data]
