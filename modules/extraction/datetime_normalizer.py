"""Động cơ luật tất định chuẩn hoá ngày giờ tiếng Việt học vụ.

Ràng buộc kỹ thuật bất biến:
- Hàm thuần (pure function), tuyệt đối KHÔNG gọi datetime.now().
- Không bao giờ ném ngoại lệ ra ngoài (mọi input lạ đều trả về value=None và cờ tương ứng).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

HO_CHI_MINH_TZ = timezone(timedelta(hours=7))


@dataclass
class SemesterConfig:
    start_date: date  # Thứ Hai tuần 1
    timezone_name: str = "Asia/Ho_Chi_Minh"
    weeks_in_semester: int = 15


@dataclass
class NormalizedDeadline:
    value: datetime | None
    anchor: datetime
    rule_id: str | None = None
    assumptions: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    time_defaulted: bool = False


def _strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt phục vụ so khớp linh hoạt."""
    s = s.replace("đ", "d").replace("Đ", "d")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=HO_CHI_MINH_TZ)
    return dt


def normalize(text: str, anchor: datetime, semester: SemesterConfig | None = None) -> NormalizedDeadline:
    """Phân giải chuỗi thời gian tự nhiên thành mốc datetime chuẩn dựa vào mốc neo."""
    if not isinstance(text, str) or not text.strip():
        return NormalizedDeadline(value=None, anchor=anchor, flags=["UNRESOLVED"])

    anchor_tz = _ensure_tz(anchor)
    assumptions: list[str] = []
    flags: list[str] = []
    rule_id: str | None = None
    time_defaulted = False

    raw_lower = text.strip().lower()
    raw_no_accent = _strip_accents(raw_lower)

    # 1. Kiểm tra các cụm từ mơ hồ đứng độc lập
    ambiguous_patterns = [
        r"^(nop vao )?tuan sau$",
        r"^buoi hoc (sau|toi|tiep theo)$",
        r"^tiet hoc (sau|toi|tiep theo)$",
        r"^khi nao xong",
    ]
    for pat in ambiguous_patterns:
        if re.search(pat, raw_no_accent):
            return NormalizedDeadline(
                value=None,
                anchor=anchor_tz,
                rule_id="ambiguous_generic",
                assumptions=["Thời gian diễn đạt quá mơ hồ, không xác định được mốc cụ thể"],
                flags=["AMBIGUOUS"],
            )

    # 2. Tách và phân tích Giờ (Time)
    extracted_time: time | None = None
    is_midnight = False

    # 2.1. 12h đêm
    if re.search(r"\b12\s*(?:h|g|:00|gio)?\s*dem\b", raw_no_accent):
        extracted_time = time(0, 0, 0)
        is_midnight = True
        flags.append("AMBIGUOUS")
        assumptions.append("12h đêm quy ước là 00:00 của ngày tiếp theo")
    # 2.2. 12h trưa
    elif re.search(r"\b12\s*(?:h|g|:00|gio)?\s*trua\b", raw_no_accent):
        extracted_time = time(12, 0, 0)
    else:
        # 2.3. Cú pháp giờ có buổi (sáng/chiều/tối): ví dụ "8 giờ tối", "8h tối", "3h chiều", "8g30 sáng"
        m_session = re.search(r"\b(\d{1,2})(?:[:hg](\d{1,2}))?\s*(?:gio)?\s*(sang|chieu|toi)\b", raw_no_accent)
        if m_session:
            h = int(m_session.group(1))
            m = int(m_session.group(2)) if m_session.group(2) else 0
            session = m_session.group(3)
            if session in ("chieu", "toi") and h < 12:
                h += 12
            if 0 <= h <= 23 and 0 <= m <= 59:
                extracted_time = time(h, m, 0)

        # 2.4. Cú pháp giờ thông thường: "23:59", "17h00", "8g30", "15:30"
        if not extracted_time:
            m_time = re.search(r"\b(\d{1,2})[:hg](\d{2})(?:[:](\d{2}))?\b", raw_lower)
            if m_time:
                h = int(m_time.group(1))
                m = int(m_time.group(2))
                s = int(m_time.group(3)) if m_time.group(3) else 0
                # Kiểm tra xem có từ chiều/tối theo sau không
                if re.search(rf"\b{re.escape(m_time.group(0))}\s*(chieu|toi)\b", raw_no_accent) and h < 12:
                    h += 12
                if 0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59:
                    extracted_time = time(h, m, s)
            else:
                m_single_h = re.search(r"\b(\d{1,2})\s*(?:h|g|gio)\b", raw_no_accent)
                if m_single_h:
                    h = int(m_single_h.group(1))
                    if re.search(r"\b(chieu|toi)\b", raw_no_accent) and h < 12:
                        h += 12
                    if 0 <= h <= 23:
                        extracted_time = time(h, 0, 0)

    # 3. Tách và phân tích Ngày (Date)
    extracted_date: date | None = None

    # 3.1. Dạng tuyệt đối: DD/MM/YYYY hoặc DD-MM-YYYY hoặc DD.MM.YYYY
    m_full_date = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", raw_lower)
    if m_full_date:
        d, mo, y = int(m_full_date.group(1)), int(m_full_date.group(2)), int(m_full_date.group(3))
        try:
            extracted_date = date(y, mo, d)
            rule_id = "absolute_full"
        except ValueError:
            pass

    # 3.2. Dạng "ngày DD tháng MM năm YYYY"
    if not extracted_date:
        m_dm_text_y = re.search(r"\bngay\s*(\d{1,2})\s*thang\s*(\d{1,2})\s*nam\s*(\d{4})\b", raw_no_accent)
        if m_dm_text_y:
            d, mo, y = int(m_dm_text_y.group(1)), int(m_dm_text_y.group(2)), int(m_dm_text_y.group(3))
            try:
                extracted_date = date(y, mo, d)
                rule_id = "absolute_text_y"
            except ValueError:
                pass

    # 3.3. Dạng thiếu năm: "DD/MM", "DD-MM", "ngày DD tháng MM"
    if not extracted_date:
        d, mo = None, None
        m_dm = re.search(r"\b(\d{1,2})[-/](\d{1,2})\b", raw_lower)
        if m_dm:
            d, mo = int(m_dm.group(1)), int(m_dm.group(2))
        else:
            m_text_dm = re.search(r"\bngay\s*(\d{1,2})\s*thang\s*(\d{1,2})\b", raw_no_accent)
            if m_text_dm:
                d, mo = int(m_text_dm.group(1)), int(m_text_dm.group(2))

        if d and mo and 1 <= d <= 31 and 1 <= mo <= 12:
            anchor_year = anchor_tz.year
            try:
                cand_date = date(anchor_year, mo, d)
                # Kiểm tra bước nhảy năm: nếu anchor tháng 12 mà deadline tháng 1
                if anchor_tz.month == 12 and mo == 1:
                    cand_date = date(anchor_year + 1, mo, d)
                    assumptions.append(f"Chuyển tiếp năm học sang {anchor_year + 1}")
                extracted_date = cand_date
                rule_id = "absolute_inferred_year"
            except ValueError:
                pass

    # 3.4. Dạng tuần học kỳ: "tuần 10", "hết tuần 8"
    if not extracted_date:
        m_sem = re.search(r"\b(?:het\s*)?tuan\s*(\d{1,2})\b", raw_no_accent)
        if m_sem and not re.search(r"\b(tuan\s*(nay|sau|toi))\b", raw_no_accent):
            week_num = int(m_sem.group(1))
            if semester and semester.start_date:
                # Tuần 1 bắt đầu từ start_date, kết thúc vào Chủ nhật của tuần đó (+6 ngày)
                target_sunday = semester.start_date + timedelta(weeks=week_num - 1, days=6)
                extracted_date = target_sunday
                rule_id = "semester_week"
                assumptions.append(f"Quy đổi tuần {week_num} theo học kỳ (kết thúc Chủ Nhật)")
            else:
                return NormalizedDeadline(
                    value=None,
                    anchor=anchor_tz,
                    rule_id="unresolved_semester_week",
                    assumptions=[f"Thiếu cấu hình học kỳ để phân giải 'tuần {week_num}'"],
                    flags=["UNRESOLVED"],
                )

    # 3.5. Dạng tương đối theo ngày: "hôm nay", "ngày mai", "hôm qua", "sau N tiếng", "trong vòng N ngày"
    if not extracted_date:
        if "hom nay" in raw_no_accent:
            extracted_date = anchor_tz.date()
            rule_id = "relative_today"
        elif "ngay mai" in raw_no_accent:
            extracted_date = anchor_tz.date() + timedelta(days=1)
            rule_id = "relative_tomorrow"
        elif "hom qua" in raw_no_accent:
            extracted_date = anchor_tz.date() - timedelta(days=1)
            rule_id = "relative_yesterday"
        else:
            m_hours = re.search(r"\bsau\s*(\d+)\s*(?:tieng|gio|h)\b", raw_no_accent)
            if m_hours:
                h_offset = int(m_hours.group(1))
                computed = anchor_tz + timedelta(hours=h_offset)
                return NormalizedDeadline(
                    value=computed,
                    anchor=anchor_tz,
                    rule_id="relative_hours",
                    assumptions=[f"Cộng {h_offset} giờ từ mốc neo"],
                    time_defaulted=False,
                )

            m_days = re.search(r"\b(?:trong\s*vong|trong|sau)\s*(\d+)\s*ngay\b", raw_no_accent)
            if m_days:
                d_offset = int(m_days.group(1))
                computed = anchor_tz + timedelta(days=d_offset)
                return NormalizedDeadline(
                    value=computed,
                    anchor=anchor_tz,
                    rule_id="relative_days",
                    assumptions=[f"Cộng {d_offset} ngày từ mốc neo"],
                    time_defaulted=False,
                )

    # 3.6. Dạng thứ trong tuần: "thứ 6 tuần sau", "chủ nhật tuần này", "thứ 3 tuần tới"
    if not extracted_date:
        weekday_patterns = [
            (r"\b(?:thu\s*(?:chu\s*nhat|cn)|chu\s*nhat|cn)\b", 6),
            (r"\b(?:thu\s*(?:bay|7)|t7)\b", 5),
            (r"\b(?:thu\s*(?:sau|6)|t6)\b", 4),
            (r"\b(?:thu\s*(?:nam|5)|t5)\b", 3),
            (r"\b(?:thu\s*(?:tu|4)|t4)\b", 2),
            (r"\b(?:thu\s*(?:ba|3)|t3)\b", 1),
            (r"\b(?:thu\s*(?:hai|2)|t2)\b", 0),
        ]
        for pat, w_idx in weekday_patterns:
            if re.search(pat, raw_no_accent):
                anchor_w = anchor_tz.weekday()
                # Kiểm tra ngữ cảnh: tuần sau/tuần tới vs tuần này vs đơn lẻ
                if "tuan sau" in raw_no_accent or "tuan toi" in raw_no_accent:
                    # Thứ của tuần kế tiếp (ISO week kế tiếp bắt đầu sau (7 - anchor_w) ngày)
                    days_ahead = (7 - anchor_w) + w_idx
                    extracted_date = anchor_tz.date() + timedelta(days=days_ahead)
                    rule_id = "weekday_next_week"
                    assumptions.append("Xác định thứ thuộc tuần liền kề tiếp theo")
                    break
                elif "tuan nay" in raw_no_accent:
                    # Thứ của tuần hiện tại (bắt đầu từ Thứ Hai)
                    days_diff = w_idx - anchor_w
                    extracted_date = anchor_tz.date() + timedelta(days=days_diff)
                    rule_id = "weekday_this_week"
                    assumptions.append("Xác định thứ thuộc tuần hiện tại")
                    break
                else:
                    # Thứ đơn lẻ: lần xuất hiện gần nhất tiếp theo
                    days_ahead = (w_idx - anchor_w) % 7
                    if days_ahead == 0 and extracted_time and extracted_time < anchor_tz.time():
                        days_ahead = 7
                    elif days_ahead == 0 and not extracted_time:
                        flags.append("AMBIGUOUS")
                    extracted_date = anchor_tz.date() + timedelta(days=days_ahead if days_ahead > 0 else 7 if days_ahead == 0 and "AMBIGUOUS" not in flags else 0)
                    rule_id = "weekday_standalone"
                    assumptions.append("Lấy thứ gần nhất tiếp theo tính từ mốc neo")
                    break

    # 4. Tổng hợp Kết quả
    if not extracted_date:
        return NormalizedDeadline(
            value=None,
            anchor=anchor_tz,
            rule_id="unresolved",
            assumptions=["Không thể phân giải mốc ngày từ văn bản"],
            flags=["UNRESOLVED"],
        )

    # Xử lý trường hợp không có giờ: mặc định 23:59:00
    if not extracted_time:
        extracted_time = time(23, 59, 0)
        time_defaulted = True
        assumptions.append("Không ghi giờ, giả định 23:59")

    # Xử lý 12h đêm: nhảy sang ngày tiếp theo lúc 00:00
    if is_midnight:
        extracted_date = extracted_date + timedelta(days=1)

    result_dt = datetime.combine(extracted_date, extracted_time, tzinfo=anchor_tz.tzinfo)

    # 5. Kiểm tra Outdated (Hạn nộp nằm trong quá khứ so với anchor)
    if result_dt < anchor_tz and "OUTDATED_DEADLINE" not in flags:
        flags.append("OUTDATED_DEADLINE")
        assumptions.append("Hạn nộp đã trôi qua so với mốc neo thời gian")

    return NormalizedDeadline(
        value=result_dt,
        anchor=anchor_tz,
        rule_id=rule_id,
        assumptions=assumptions,
        flags=flags,
        time_defaulted=time_defaulted,
    )
