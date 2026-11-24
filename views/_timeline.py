"""Dòng thời gian một ngày kiểu planner: mỗi việc là một viên tròn/viên thuốc màu trên trục dọc,
chiều cao theo thời lượng, khoảng trống giữa các việc ghi số giờ rảnh."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape

PALETTE = ["#F07167", "#4D96FF", "#6BCB77", "#FFB84C", "#9D79BC", "#00AFB9", "#F49CBB", "#7D8597"]
CLASS_COLOR = "#ADB5BD"
DEADLINE_COLOR = "#E63946"

CSS = """
<style>
.tl {font-family: inherit; max-width: 640px; margin: 4px 0 12px;}
.tl-row {display: grid; grid-template-columns: 52px 56px 1fr 28px; align-items: start;}
.tl-time {font-size: 12px; color: #8D99AE; text-align: right; padding: 6px 10px 0 0;}
.tl-axis {display: flex; flex-direction: column; align-items: center;}
.tl-pill {width: 44px; border-radius: 22px; display: flex; align-items: center;
          justify-content: center; font-size: 20px; color: #fff;
          box-shadow: 0 2px 6px rgba(0,0,0,.12);}
.tl-body {padding: 4px 0 0 12px;}
.tl-sub {font-size: 12px; color: #8D99AE;}
.tl-title {font-size: 15px; font-weight: 600; color: #2B2D42; line-height: 1.3;}
.tl-check {width: 20px; height: 20px; border-radius: 50%; border: 2px solid; margin-top: 8px;}
.tl-gap {display: grid; grid-template-columns: 52px 56px 1fr; min-height: 30px;}
.tl-line {justify-self: center; border-left: 2px dashed #DEE2E6; height: 100%; min-height: 30px;}
.tl-gaptext {font-size: 12px; color: #ADB5BD; align-self: center; padding-left: 12px;}
.tl-empty {color: #8D99AE; font-size: 14px; padding: 18px 0;}
</style>
"""


@dataclass
class Item:
    start: datetime
    end: datetime
    title: str
    subtitle: str
    icon: str
    color: str


def _dur(minutes: float) -> str:
    h, m = divmod(int(round(minutes)), 60)
    return f"{h} giờ {m} phút" if h and m else (f"{h} giờ" if h else f"{m} phút")


def render(items: list[Item]) -> str:
    """HTML của dòng thời gian một ngày (đã gồm CSS)."""
    items = sorted(items, key=lambda i: (i.start, i.end))
    if not items:
        return CSS + '<div class="tl"><div class="tl-empty">Ngày này trống — không có lịch.</div></div>'
    out = [CSS, '<div class="tl">']
    prev_end: datetime | None = None
    for it in items:
        if prev_end is not None and it.start > prev_end:
            gap = (it.start - prev_end).total_seconds() / 60
            out.append(f'<div class="tl-gap"><div></div><div class="tl-line"></div>'
                       f'<div class="tl-gaptext">{_dur(gap)} rảnh</div></div>')
        minutes = max((it.end - it.start).total_seconds() / 60, 0)
        height = 44 if minutes == 0 else max(44, min(160, minutes * 0.9))
        span = f"{it.start:%H:%M}" if minutes == 0 else f"{it.start:%H:%M} – {it.end:%H:%M} ({_dur(minutes)})"
        out.append(
            f'<div class="tl-row"><div class="tl-time">{it.start:%H:%M}</div>'
            f'<div class="tl-axis"><div class="tl-pill" style="height:{height:.0f}px;'
            f'background:{it.color}">{it.icon}</div></div>'
            f'<div class="tl-body"><div class="tl-sub">{escape(span)}</div>'
            f'<div class="tl-title">{escape(it.title)}</div>'
            f'<div class="tl-sub">{escape(it.subtitle)}</div></div>'
            f'<div class="tl-check" style="border-color:{it.color}"></div></div>')
        prev_end = max(prev_end, it.end) if prev_end else it.end
    out.append("</div>")
    return "".join(out)
