"""Gửi các nhắc nhở đến hạn qua Telegram.

    python -m modules.scheduler.notify

Đặt Windows Task Scheduler (hoặc cron) chạy lệnh này mỗi 5 phút. Lệnh đọc nhắc nhở của lịch được
lưu gần nhất trên trang "Lập lịch & nhắc nhở"; mỗi nhắc nhở chỉ được gửi một lần.
"""
from __future__ import annotations

import sys
from datetime import datetime

from .reminders import TelegramSender, load_reminders, send_due


def main() -> int:
    sender = TelegramSender.from_env()
    if sender is None:
        print("Chưa cấu hình TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID trong .env")
        return 1
    reminders = load_reminders()
    if not reminders:
        print("Chưa có lịch nào được lưu. Mở trang Lập lịch, xếp lịch và bấm 'Lưu nhắc nhở'.")
        return 1
    sent = send_due(reminders, datetime.now(), sender)
    print(f"Đã gửi {len(sent)} nhắc nhở.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
