"""Dòng thời gian một ngày kiểu planner: mỗi việc là một viên màu trên trục dọc, chiều cao theo
thời lượng, khoảng trống giữa các việc ghi số giờ rảnh, vạch đỏ đánh dấu giờ hiện tại."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape

PALETTE = ["#F07167", "#4D96FF", "#6BCB77", "#FFB84C", "#9D79BC", "#00AFB9", "#F49CBB", "#7D8597"]
CLASS_COLOR = "#ADB5BD"
DEADLINE_COLOR = "#E63946"
EXAM_COLOR = "#9D79BC"

CSS = """
<style>
.tl {max-width: 680px; margin: 6px 0 14px;}
@keyframes tl-in {from {opacity: 0; transform: translateX(-10px);} to {opacity: 1; transform: none;}}
.tl-row, .tl-gap, .tl-now {animation: tl-in .45s cubic-bezier(.2,.7,.2,1) both;}
.tl-row {display: grid; grid-template-columns: 52px 56px 1fr 30px; align-items: start;}
.tl-time {font-size: 12px; color: #8D99AE; text-align: right; padding: 6px 10px 0 0;
          font-variant-numeric: tabular-nums;}
.tl-axis {display: flex; flex-direction: column; align-items: center;}
.tl-pill {width: 44px; border-radius: 22px; display: flex; align-items: center; justify-content: center;
          font-size: 20px; color: #fff; box-shadow: 0 3px 10px rgba(0,0,0,.12);
          transition: transform .2s ease, filter .2s ease;}
.tl-row:hover .tl-pill {transform: scale(1.06); filter: saturate(1.15);}
.tl-body {padding: 4px 0 0 12px;}
.tl-sub {font-size: 12px; color: #8D99AE;}
.tl-title {font-size: 15px; font-weight: 700; color: #2B2D42; line-height: 1.3;}
.tl-check {width: 22px; height: 22px; border-radius: 50%; border: 2px solid; margin-top: 8px;
           display: grid; place-items: center; font-size: 13px; color: #fff; font-weight: 800;}
.tl-done .tl-pill {opacity: .45;} .tl-done .tl-title {text-decoration: line-through; color: #8D99AE;}
.tl-gap {display: grid; grid-template-columns: 52px 56px 1fr; min-height: 30px;}
.tl-line {justify-self: center; border-left: 2px dashed #F3D9D2; height: 100%; min-height: 30px;}
.tl-gaptext {font-size: 12px; color: #ADB5BD; align-self: center; padding-left: 12px;}
.tl-now {display: grid; grid-template-columns: 52px 1fr; align-items: center; margin: 4px 0;}
.tl-now span {font-size: 11px; font-weight: 800; color: #E63946; text-align: right; padding-right: 8px;}
.tl-now i {height: 2px; background: linear-gradient(90deg, #E63946, rgba(230,57,70,0)); position: relative;}
.tl-now i::before {content: ""; position: absolute; left: 22px; top: -4px; width: 10px; height: 10px;
                   border-radius: 50%; background: #E63946; box-shadow: 0 0 0 4px rgba(230,57,70,.18);}
.tl-empty {color: #8D99AE; font-size: 14px; padding: 22px 0; text-align: center;}
@media (max-width: 640px) {
  .tl-row {grid-template-columns: 42px 48px 1fr 26px;}
  .tl-gap {grid-template-columns: 42px 48px 1fr;}
  .tl-pill {width: 38px;} .tl-title {font-size: 14px;}
}
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
    done: bool = False


def _dur(minutes: float) -> str:
    h, m = divmod(int(round(minutes)), 60)
    return f"{h} giờ {m} phút" if h and m else (f"{h} giờ" if h else f"{m} phút")


def _now_row(now: datetime) -> str:
    return f'<div class="tl-now"><span>{now:%H:%M}</span><i></i></div>'


def render(items: list[Item], now: datetime | None = None) -> str:
    """HTML của dòng thời gian một ngày (đã gồm CSS). ``now``: vẽ vạch giờ hiện tại nếu cùng ngày."""
    items = sorted(items, key=lambda i: (i.start, i.end))
    if not items:
        return CSS + '<div class="tl"><div class="tl-empty">🌤️ Ngày này trống — tận hưởng nhé.</div></div>'
    show_now = now is not None and items[0].start.date() == now.date()
    out = [CSS, '<div class="tl">']
    prev_end: datetime | None = None
    for n, it in enumerate(items):
        delay = f"animation-delay:{min(n, 12) * 60}ms"
        if show_now and now < it.start:
            out.append(_now_row(now))
            show_now = False
        if prev_end is not None and it.start > prev_end:
            gap = (it.start - prev_end).total_seconds() / 60
            out.append(f'<div class="tl-gap" style="{delay}"><div></div><div class="tl-line"></div>'
                       f'<div class="tl-gaptext">{_dur(gap)} rảnh</div></div>')
        minutes = max((it.end - it.start).total_seconds() / 60, 0)
        height = 44 if minutes == 0 else max(44, min(160, minutes * 0.9))
        span = f"{it.start:%H:%M}" if minutes == 0 else \
            f"{it.start:%H:%M} – {it.end:%H:%M} · {_dur(minutes)}"
        check = (f'<div class="tl-check" style="border-color:{it.color};background:{it.color}">✓</div>'
                 if it.done else f'<div class="tl-check" style="border-color:{it.color}"></div>')
        out.append(
            f'<div class="tl-row{" tl-done" if it.done else ""}" style="{delay}">'
            f'<div class="tl-time">{it.start:%H:%M}</div>'
            f'<div class="tl-axis"><div class="tl-pill" style="height:{height:.0f}px;'
            f'background:{it.color}">{it.icon}</div></div>'
            f'<div class="tl-body"><div class="tl-sub">{escape(span)}</div>'
            f'<div class="tl-title">{escape(it.title)}</div>'
            f'<div class="tl-sub">{escape(it.subtitle)}</div></div>{check}</div>')
        prev_end = max(prev_end, it.end) if prev_end else it.end
    if show_now:
        out.append(_now_row(now))
    out.append("</div>")
    return "".join(out)
