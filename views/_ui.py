"""Hệ thống giao diện dùng chung: font, thẻ, hiệu ứng, màn mở đầu, pháo giấy, đồng hồ tập trung.

Chèn bằng ``st.html``. CSS áp cho cả trang; các đoạn JS (``unsafe_allow_javascript=True``) chạy
trong trang chính, nên mỗi đoạn tự chống chạy lặp khi Streamlit chạy lại script.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
import time as _time
from datetime import datetime

import streamlit as st

BRAND = "DP"
BRAND_FULL = "Daily Planner"
ASSETS = Path(__file__).resolve().parents[1] / "assets"
LOGO_PNG = ASSETS / "logo.png"
FAVICON = ASSETS / "favicon.png"
CORAL, TEAL, AMBER, BLUE, VIOLET = "#F07167", "#00AFB9", "#FFB84C", "#4D96FF", "#9D79BC"
MODULES = [  # (mã, tên, biểu tượng, màu, trang)
    ("D", "Hộp thư", "📬", TEAL, "views/email_security.py"),
    ("B", "Trích xuất bài tập", "📝", AMBER, "views/extraction.py"),
    ("C", "Lập lịch & nhắc nhở", "📅", CORAL, "views/scheduler.py"),
    ("A", "Hỏi đáp tài liệu", "💬", BLUE, "views/qa.py"),
]

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');
html, body, p, li, label, input, textarea, select, td, th, h1, h2, h3, h4, h5, h6,
.stMarkdown, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
  font-family: 'Be Vietnam Pro', 'Segoe UI', system-ui, sans-serif !important;
}
h1 {font-weight: 800 !important; letter-spacing: -0.02em;}
h2, h3 {font-weight: 700 !important; letter-spacing: -0.01em;}


/* Thẻ */
[data-testid="stMetric"] {
  background: #fff; border-radius: 18px; padding: 14px 18px;
  box-shadow: 0 1px 2px rgba(43,45,66,.06), 0 6px 18px rgba(240,113,103,.08);
  transition: transform .2s ease, box-shadow .2s ease;
}
[data-testid="stMetric"]:hover {transform: translateY(-3px);
  box-shadow: 0 2px 4px rgba(43,45,66,.06), 0 14px 28px rgba(240,113,103,.16);}
[data-testid="stMetricValue"] {font-weight: 800 !important;}
[data-testid="stVerticalBlockBorderWrapper"] {
  background: #fff; border-color: #F6DCD5 !important; border-radius: 20px !important;
  box-shadow: 0 6px 20px rgba(240,113,103,.07); transition: box-shadow .25s ease, transform .25s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {box-shadow: 0 12px 30px rgba(240,113,103,.13);}
[data-testid="stExpander"] details {background: #fff; border-radius: 16px; border-color: #F6DCD5;}

/* Nút */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {
  border-radius: 999px !important; font-weight: 600; transition: transform .15s ease, box-shadow .15s ease;
}
.stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {
  transform: translateY(-1px); box-shadow: 0 6px 16px rgba(240,113,103,.25);
}
.stButton button:active {transform: translateY(0) scale(.98);}
button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #F07167 0%, #F49CBB 100%) !important; border: none !important;
}

/* Thanh bên: thương hiệu lên trên danh sách trang */
[data-testid="stSidebarContent"] {display: flex; flex-direction: column;}
[data-testid="stSidebarHeader"] {order: 0;}
[data-testid="stSidebarUserContent"] {order: 1; padding-top: 0 !important; padding-bottom: 4px !important;}
[data-testid="stSidebarNav"] {order: 2;}
[data-testid="stSidebarNavItems"] {padding-top: 6px; gap: 4px; display: flex; flex-direction: column;}
[data-testid="stSidebarNavLink"] {border-radius: 14px; padding: 10px 12px !important; min-height: 46px;
  transition: background .2s ease, transform .2s ease, box-shadow .2s ease;}
[data-testid="stSidebarNavLink"] p {font-size: 15px; font-weight: 600; color: #4A4E69;}
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {font-size: 22px; color: #8D99AE;}
[data-testid="stSidebarNavLink"]:hover {background: rgba(240,113,103,.10); transform: translateX(2px);}
[data-testid="stSidebarNavLink"][aria-current="page"] {background: linear-gradient(135deg, #F07167, #F49CBB);
  box-shadow: 0 6px 16px rgba(240,113,103,.32);}
[data-testid="stSidebarNavLink"][aria-current="page"] p,
[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {color: #fff !important;}
.nh-brand {display: flex; gap: 10px; align-items: center; padding: 4px 6px 10px;}
.nh-brand .logo {width: 42px; height: 42px; border-radius: 12px;
  box-shadow: 0 6px 14px rgba(240,113,103,.35); transition: transform .3s ease;}
.nh-brand:hover .logo {transform: rotate(-6deg) scale(1.06);}
.nh-brand b {font-size: 22px; font-weight: 800; color: #2B2D42; letter-spacing: -0.01em; line-height: 1;}
.nh-brand small {display: block; color: #8D99AE; font-size: 11.5px; font-weight: 600; margin-top: 3px;
  letter-spacing: .04em; text-transform: uppercase;}

.nh-ver {position: absolute; left: 18px; bottom: 4px; font-size: 10.5px; color: #ADB5BD;}
/* Tài khoản ở đáy thanh bên */
[data-testid="stSidebarContent"] {position: relative; min-height: 100%;}
.st-key-acct_box {position: absolute; left: 16px; right: 16px; bottom: 18px; gap: 8px;}
.nh-acct {display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: 16px;
  background: rgba(255,255,255,.65); box-shadow: 0 2px 10px rgba(240,113,103,.10);}
.nh-acct img, .nh-acct > span {width: 36px; height: 36px; border-radius: 50%; flex: none; object-fit: cover;
  display: grid; place-items: center; background: linear-gradient(135deg, #F07167, #F49CBB); color: #fff; font-weight: 800;}
.nh-acct.guest > span {background: #FFE1DA; font-size: 18px;}
.nh-acct div {min-width: 0;}
.nh-acct b {display: block; font-size: 13.5px; color: #2B2D42; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.nh-acct small {display: block; font-size: 11.5px; color: #8D99AE; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.st-key-acct_box button {border-radius: 12px !important; font-size: 13.5px !important;}

/* Thẻ đăng nhập Google ở trang Hộp thư */
.st-key-google_card {align-items: center; text-align: center; padding: 26px 18px !important;}
.nh-login {display: flex; flex-direction: column; align-items: center; gap: 8px;}
.nh-login .i {width: 58px; height: 58px; border-radius: 18px; display: grid; place-items: center; font-size: 30px;
  background: linear-gradient(135deg, #FDECE7, #E3F6F8); box-shadow: 0 8px 20px rgba(0,175,185,.15);}
.nh-login b {font-size: 19px; color: #2B2D42;}
.st-key-google_login button {background: #fff !important; color: #2B2D42 !important;
  border: 1.5px solid #DADCE0 !important; border-radius: 999px !important; padding: 10px 26px !important;
  font-weight: 600 !important; min-width: 260px; box-shadow: 0 2px 6px rgba(60,64,67,.12) !important;}
.st-key-google_login button:hover {border-color: #4285F4 !important; box-shadow: 0 6px 16px rgba(66,133,244,.22) !important;}
.st-key-google_login [data-testid="stIconMaterial"] {color: #4285F4;}
.st-key-google_card [data-testid="stCaptionContainer"] {text-align: center;}

/* Ẩn khoảng trống của các khối st.html chỉ chứa CSS/JS */
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > style:only-child),
[data-testid="stElementContainer"]:has(.nh-invisible) {display: none;}

/* Thành phần riêng */
.nh-hero {display: flex; justify-content: space-between; align-items: center; gap: 24px;
  padding: 26px 30px; border-radius: 26px; color: #2B2D42;
  background: radial-gradient(120% 140% at 0% 0%, #FFE3DC 0%, #FFF4EC 45%, #EAF6FF 100%);
  box-shadow: 0 10px 30px rgba(240,113,103,.12);}
.nh-hero h1 {margin: 0; font-size: 34px;}
.nh-chips {display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px;}
.nh-chip {display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 999px;
  font-size: 12.5px; font-weight: 600; background: #fff; color: #5C677D;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);}
/* Vòng tiến độ vẽ bằng CSS (bộ lọc của st.html xoá thẻ SVG) */
.nh-ring {position: relative; width: 112px; height: 112px; flex: none; border-radius: 50%;
  background: conic-gradient(#F07167 0%, #F49CBB calc(var(--nh-p) * 1%), #fff calc(var(--nh-p) * 1%) 100%);
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 11px), #000 calc(100% - 10px));
          mask: radial-gradient(farthest-side, transparent calc(100% - 11px), #000 calc(100% - 10px));
  animation: nh-ring 1.2s cubic-bezier(.2,.7,.2,1) both;}
.nh-ringwrap {position: relative; width: 112px; height: 112px; flex: none;}
.nh-ringwrap .v {position: absolute; inset: 0; display: grid; place-items: center; text-align: center;
  font-weight: 800; font-size: 22px; color: #2B2D42; line-height: 1.1;}
.nh-ringwrap .v small {display: block; font-size: 11px; font-weight: 500; color: #8D99AE;}
@keyframes nh-ring {from {transform: rotate(-90deg) scale(.6); opacity: 0;}}
.nh-head {display: flex; align-items: center; gap: 14px; margin: 2px 0 6px;}
.nh-head .ic {width: 52px; height: 52px; border-radius: 16px; display: grid; place-items: center;
  font-size: 26px; flex: none;}
.nh-head h1 {margin: 0 !important; padding: 0 !important; font-size: 30px;}
.nh-head p {margin: 2px 0 0; color: #8D99AE; font-size: 13.5px;}
.nh-due {display: flex; align-items: flex-start; gap: 12px; padding: 10px 4px; border-bottom: 1px dashed #F3D9D2;}
.nh-due .dot {margin-top: 6px;}
.nh-due:last-child {border-bottom: none;}
.nh-due .dot {width: 10px; height: 10px; border-radius: 50%; flex: none;}
.nh-due .t {flex: 1; font-weight: 600; color: #2B2D42; font-size: 14.5px;}
.nh-due .c {font-size: 12px; color: #8D99AE; font-weight: 500;}
.nh-due .left {display: inline-block; margin-top: 6px; font-size: 11.5px; font-weight: 700;
  padding: 2px 10px; border-radius: 999px; white-space: nowrap;}
.nh-mod {display: block; padding: 16px 18px; border-radius: 20px; background: #fff; min-height: 138px;
  box-shadow: 0 6px 20px rgba(43,45,66,.06); transition: transform .2s ease, box-shadow .2s ease;
  border-top: 4px solid var(--c);}
.nh-mod:hover {transform: translateY(-4px); box-shadow: 0 16px 32px rgba(43,45,66,.10);}
.nh-mod .i {font-size: 24px;} .nh-mod b {display: block; margin-top: 6px; color: #2B2D42;}
.nh-mod span {font-size: 12.5px; color: #8D99AE;}
.nh-week {display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; align-items: end;
  height: 150px; padding: 6px 4px 0;}
.nh-week .col {display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%;}
.nh-week .stack {width: 62%; min-width: 16px; max-width: 38px; display: flex; flex-direction: column-reverse; border-radius: 10px;
  overflow: hidden; transform-origin: bottom; animation: nh-grow .8s cubic-bezier(.2,.7,.2,1) both;}
.nh-week .stack i {display: block;}
.nh-week .h {font-size: 11px; font-weight: 700; color: #5C677D; margin-bottom: 4px;}
.nh-week .d {font-size: 11.5px; color: #8D99AE; margin-top: 6px; font-weight: 600;}
.nh-week .today .d {color: #F07167;} .nh-week .today .stack {box-shadow: 0 0 0 3px rgba(240,113,103,.25);}
.nh-legend {display: flex; gap: 14px; font-size: 12px; color: #8D99AE; margin-top: 8px;}
.nh-legend span::before {content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 3px;
  margin-right: 5px; vertical-align: -1px; background: var(--c);}
@keyframes nh-grow {from {transform: scaleY(0);}}
/* Màn nhỏ (điện thoại) */
@media (max-width: 640px) {
  .nh-hero {flex-direction: column; align-items: flex-start; padding: 20px 18px; gap: 14px;}
  .nh-hero h1 {font-size: 25px;}
  .nh-hero p {font-size: 14px;}
  .nh-ringwrap {align-self: flex-end; margin-top: -8px;}
  .nh-head .ic {width: 42px; height: 42px; font-size: 21px; border-radius: 13px;}
  .nh-head h1 {font-size: 23px;}
  .nh-week {gap: 5px;}
}
@media (prefers-reduced-motion: reduce) {* {animation: none !important; transition: none !important;}}
</style>
"""


def _js(html: str) -> str:
    r"""Đổi ``<`` đứng trước chữ hoặc ``/`` trong <script> thành mã thoát JS ``\x3c``.

    Bộ lọc DOMPurify của st.html xoá cả thẻ <script> nếu nội dung có dạng ``<span``/``</svg>``
    (chống mXSS), nên chuỗi HTML dựng trong JS phải viết bằng mã thoát.
    """
    def fix(m: re.Match) -> str:
        body = re.sub(r"<(?=[/\w!])", lambda _: "\\x3c", m.group(2))
        return m.group(1) + body + m.group(3)
    return re.sub(r"(<script[^>]*>)(.*?)(</script>)", fix, html, flags=re.S)


def apply() -> None:
    """CSS chung + thương hiệu ở thanh bên. Gọi một lần mỗi lần chạy, trước khi chạy trang."""
    st.html(GLOBAL_CSS)
    st.sidebar.html(
        f'<div class="nh-brand"><img class="logo" src="{logo_data_uri()}" alt="{BRAND}">'
        f'<div><b>{BRAND}</b><small>{BRAND_FULL}</small></div></div>')


def logo_data_uri() -> str:
    """Logo nhúng thẳng vào HTML (bộ lọc của st.html xoá thẻ SVG nên dùng ảnh PNG)."""
    return "data:image/png;base64," + base64.b64encode(LOGO_PNG.read_bytes()).decode()


FILE_ICONS = {".pdf": "📕", ".docx": "📘", ".xlsx": "📊", ".csv": "📊", ".tsv": "📊", ".pptx": "📙",
              ".png": "🖼️", ".jpg": "🖼️", ".jpeg": "🖼️", ".webp": "🖼️", ".gif": "🖼️", ".heic": "🖼️",
              ".mp4": "🎬", ".mov": "🎬", ".webm": "🎬", ".mp3": "🎧", ".m4a": "🎧", ".wav": "🎧", ".ogg": "🎧"}


def file_label(filename: str) -> str:
    """Tên tệp cho người dùng: bỏ tiền tố mã băm D thêm khi lưu, kèm biểu tượng theo loại."""
    name = re.sub(r"^[0-9a-f]{16}_", "", Path(filename).name)
    return f"{FILE_ICONS.get(Path(name).suffix.lower(), '📄')} {name}"


def page_header(icon: str, title: str, color: str) -> None:
    st.html(f'<div class="nh-head"><div class="ic" style="background:{color}22">{icon}</div>'
            f'<div><h1>{title}</h1></div></div>')


def ring(done: int, total: int, label: str) -> str:
    pct = done / total if total else 0.0
    return (f'<div class="nh-ringwrap"><div class="nh-ring" style="--nh-p:{pct * 100:.1f}"></div>'
            f'<div class="v"><div>{round(pct * 100)}%<small>{label}</small></div></div></div>')


def greeting(now: datetime) -> str:
    h = now.hour
    if h < 5:
        return "Khuya rồi, nghỉ sớm nhé"
    return "Chào buổi sáng" if h < 11 else "Chào buổi trưa" if h < 14 else \
        "Chào buổi chiều" if h < 18 else "Chào buổi tối"


# --------------------------------------------------------------------------- con trỏ dựng giao diện
# Bộ điều khiển cài một lần vào trang (giữ qua các lần chạy lại). Mỗi lần Streamlit chạy lại, khối
# script nhỏ (có mã lần chạy riêng nên luôn chạy lại) báo cho bộ điều khiển:
#   - đổi trang / mở lần đầu: mọi khối đang thấy được các con trỏ mang từ ngoài màn hình vào;
#   - tương tác thường: các khối vừa thay đổi được mang vào (không khối nào đổi thì mang lại chính
#     khối vừa bấm), để tương tác nào cũng có hiệu ứng;
#   - đổi tác vụ gấp (bấm tiếp khi con trỏ còn đang mang, hoặc hai lần bấm sát nhau): các khối
#     rơi nhanh ra từ vị trí con trỏ chuột thật.
MOTION_JS = """
<div class="nh-invisible" data-run="__RUN__"></div>
<script>
(function () {
  const V = 'dp-motion-8';
  if (!window.__dpMotion || window.__dpMotion.v !== V) {
    if (window.__dpMotion && window.__dpMotion.destroy) window.__dpMotion.destroy();
    window.__dpMotion = install(V, __CURSORS__);
  }
  window.__dpMotion.onRun('__PAGE__');

  function install(v, CURSORS) {
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const SEL = ['.nh-hero', '.nh-head', '.tl', '[data-testid="stMetric"]', '[data-testid="stVerticalBlockBorderWrapper"]',
      '[data-testid="stHeading"]', '[data-testid="stExpander"]', '[data-testid="stPageLink"]', '[data-testid="stAlert"]',
      '[data-testid="stForm"]', '[data-testid="stDataFrame"]', '[data-testid="stTable"]', '[data-testid="stFileUploader"]',
      '[data-testid="stButton"]', '[data-testid="stDownloadButton"]', '[data-testid="stTextInput"]',
      '[data-testid="stTextArea"]', '[data-testid="stSelectbox"]', '[data-testid="stRadio"]', '[data-testid="stTabs"]',
      '[data-testid="stSlider"]', '[data-testid="stNumberInput"]', '[data-testid="stDateInput"]',
      '[data-testid="stCheckbox"]', '[data-testid="stButtonGroup"]', '[data-testid="stCaptionContainer"]',
      '[data-testid="stMarkdown"]', '[data-testid="stImage"]', '[data-testid="stChatMessage"]',
      '[data-testid="stArrowVegaLiteChart"]', '[data-testid="stVegaLiteChart"]', '[data-testid="stIFrame"]',
      '[data-testid="stCustomComponentV1"]', '[data-testid="stCode"]', '[data-testid="stHtml"]'].join(', ');
    const S = {page: null, ptr: {x: innerWidth / 2, y: innerHeight / 3}, lastAct: null, lastRunT: 0,
      collecting: false, full: false, quick: false, act: null, batch: new Set(), hidden: new Set(), frames: new Map(),
      startT: 0, lastMut: 0, done: false, loop: null, queue: [], running: new Set(), cursors: [], overlay: null, gen: 0};
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const mainEl = () => document.querySelector('[data-testid="stMainBlockContainer"]');

    function sized(el) { const r = el.getBoundingClientRect(); return r.width > 8 && r.height > 8; }
    function own(el) { return el.classList.contains('nh-invisible') || !!el.querySelector('.nh-invisible'); }
    function typing(el) {
      const a = document.activeElement;
      if (!a || !el.contains(a)) return false;
      return a.tagName === 'TEXTAREA' || (a.tagName === 'INPUT' && a.getAttribute('role') !== 'combobox' &&
        /^(text|password|search|email|number|url|tel)$/.test(a.type));
    }
    // Khối ngoài cùng (trong vùng nội dung chính) chứa nút này.
    function topBlock(node) {
      const m = mainEl();
      let el = node && (node.nodeType === 1 ? node : node.parentElement), best = null;
      if (!m || !el) return null;
      while (el && el !== m) { if (el.matches && el.matches(SEL)) best = el; el = el.parentElement; }
      return el === m ? best : null;
    }
    function blocksIn(node) {
      if (!node || node.nodeType !== 1) return [];
      const all = node.matches(SEL) ? [node] : Array.from(node.querySelectorAll(SEL));
      return all.filter(el => !all.some(o => o !== el && o.contains(el)));
    }
    function allBlocks() { const m = mainEl(); return m ? blocksIn(m).filter(el => sized(el) && !own(el)) : []; }

    function hide(el) {
      if (S.hidden.has(el)) return;
      S.hidden.add(el); el.style.animation = 'none'; el.style.opacity = '0';
    }
    function show(el) { S.hidden.delete(el); el.style.opacity = ''; }
    // Khung viền (st.container(border=True)): ẩn viền, để con trỏ vẽ lại viền trước khi mang nội dung vào.
    const FRAME = '[data-testid="stVerticalBlock"]';
    function isFrame(el) {
      const c = getComputedStyle(el);
      return parseFloat(c.borderTopWidth) > 0 && c.borderTopStyle !== 'none' && c.borderTopColor !== 'rgba(0, 0, 0, 0)';
    }
    function framesIn(node) {
      if (!node || node.nodeType !== 1) return [];
      const list = (node.matches(FRAME) ? [node] : []).concat(Array.from(node.querySelectorAll(FRAME)));
      return list.filter(f => S.frames.has(f) || isFrame(f));
    }
    function hideFrame(f) {
      if (S.frames.has(f) || own(f)) return;
      const c = getComputedStyle(f);
      let resolve;
      const ready = new Promise(r => { resolve = r; });
      S.frames.set(f, {ready, resolve, radius: parseFloat(c.borderTopLeftRadius) || 0});
      f.style.transition = 'none'; f.style.borderColor = 'transparent';
      f.style.backgroundColor = 'transparent'; f.style.boxShadow = 'none';
    }
    function showFrame(f) {
      const info = S.frames.get(f);
      if (!info) return;
      S.frames.delete(f);
      f.style.transition = 'border-color .3s ease, background-color .3s ease, box-shadow .3s ease';
      f.style.borderColor = ''; f.style.backgroundColor = ''; f.style.boxShadow = '';
      setTimeout(() => { f.style.transition = ''; }, 400);
      info.resolve();
    }
    function framesReady(el) {
      const waits = [];
      S.frames.forEach((info, f) => { if (f !== el && f.contains(el)) waits.push(info.ready); });
      return waits.length ? Promise.race([Promise.all(waits), sleep(3000)]) : null;
    }
    function add(el) {
      if (!el || own(el) || typing(el)) return;
      S.batch.add(el); hide(el);
    }

    // Ghi lại mọi khối thay đổi trong lúc Streamlit đang chạy lại, ẩn ngay để khỏi chớp.
    const obs = new MutationObserver(muts => {
      if (!S.collecting) return;
      const m = mainEl();
      if (!m) return;
      let touched = false;
      for (const mu of muts) {
        if (!m.contains(mu.target) || (S.overlay && S.overlay.contains(mu.target))) continue;
        const nodes = mu.type === 'childList' && mu.addedNodes.length ? Array.from(mu.addedNodes) : [mu.target];
        for (const n of nodes) {
          const b = topBlock(n);
          (b ? [b] : blocksIn(n)).forEach(add);
          if (mu.type === 'childList') framesIn(n).forEach(hideFrame);
          touched = true;
        }
      }
      if (touched) S.lastMut = Date.now();
    });
    obs.observe(document.body, {childList: true, subtree: true, characterData: true});

    function onAct(e) {
      if (S.overlay && S.overlay.contains(e.target)) return;
      const now = Date.now();
      const busy = animating() || S.collecting || (S.lastAct && now - S.lastAct.t < 900);
      if (e.clientX !== undefined && e.type === 'pointerdown') S.ptr = {x: e.clientX, y: e.clientY};
      S.lastAct = {t: now, target: e.target, busy: !!busy};
      if (animating()) interrupt();
    }
    const onMove = e => { S.ptr = {x: e.clientX, y: e.clientY}; };
    const onKey = e => { if (e.key === 'Enter' || e.key === ' ') onAct(e); };
    document.addEventListener('pointerdown', onAct, true);
    document.addEventListener('keydown', onKey, true);
    document.addEventListener('pointermove', onMove, {capture: true, passive: true});

    function onRun(page) {
      const now = Date.now();
      const act = S.lastAct && S.lastAct.t > S.lastRunT - 50 ? S.lastAct : null;
      S.lastRunT = now;
      const changed = page !== S.page;
      S.page = page;
      if (reduce) return;
      if (!S.collecting) {
        S.collecting = true; S.batch = new Set(); S.full = false; S.quick = false; S.act = null; S.startT = now;
      }
      S.full = S.full || changed;
      if (act) { S.act = act; S.quick = S.quick || act.busy; }
      S.lastMut = now; S.done = false;
      if (changed) { allBlocks().forEach(add); framesIn(mainEl()).forEach(hideFrame); }
      if (!S.loop) S.loop = setInterval(check, 60);
    }

    function check() {
      const now = Date.now();
      // Chờ Streamlit chạy xong cả trang (tín hiệu onDone), rồi thêm một nhịp yên để các khối kịp vẽ.
      const quiet = now - S.lastMut;
      if (!((S.done && quiet >= 150) || quiet >= 1500 || now - S.startT > 6000)) return;
      clearInterval(S.loop); S.loop = null; S.collecting = false;
      settle();
    }

    function inView(el) { const r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight - 10; }
    function actBlock() {
      // Khối vừa được bấm (để tương tác nào cũng có hiệu ứng, kể cả khi phần thay đổi nằm ngoài màn hình).
      const t = S.act && Date.now() - S.act.t < 6000 ? S.act.target : null;
      if (!t || !t.isConnected) return null;
      const b = topBlock(t) || (t.closest && t.closest('[data-testid="stSidebar"] [data-testid="stElementContainer"]'));
      return b && sized(b) && !own(b) && !typing(b) ? b : null;
    }
    function settle() {
      let targets = S.full ? allBlocks() : Array.from(S.batch).filter(el => el.isConnected && sized(el));
      targets = targets.filter(el => !own(el) && !typing(el));
      let vis = targets.filter(inView);
      if (!vis.length) { const b = actBlock(); if (b && inView(b)) vis = [b]; }
      Array.from(S.hidden).forEach(el => { if (!vis.includes(el) && !S.queue.includes(el)) show(el); });
      const frames = S.quick ? [] : Array.from(S.frames.keys()).filter(f => f.isConnected && sized(f) && inView(f));
      Array.from(S.frames.keys()).forEach(f => { if (!frames.includes(f)) showFrame(f); });
      if (!vis.length && !frames.length) return;
      vis.forEach(hide);
      if (S.quick) drop(vis); else carry(vis, frames);
      setTimeout(safety, 9000);
    }
    function onDone() { S.done = true; S.lastMut = Date.now(); }
    function safety() {
      if (animating() || S.collecting) return;
      Array.from(S.hidden).forEach(show); Array.from(S.frames.keys()).forEach(showFrame);
    }

    // ---- lớp phủ + các con trỏ
    function overlay() {
      if (S.overlay && S.overlay.isConnected) return S.overlay;
      const o = document.createElement('div');
      o.style.cssText = 'position:fixed;inset:0;z-index:99999;pointer-events:none;overflow:hidden';
      document.body.appendChild(o);
      S.overlay = o;
      S.cursors = CURSORS.map(c => {
        const el = document.createElement('div');
        el.style.cssText = 'position:absolute;left:0;top:0;will-change:transform;transform:translate(-200px,-200px)';
        el.innerHTML = '<svg width="22" height="24" viewBox="0 0 22 24" style="filter:drop-shadow(0 2px 3px rgba(0,0,0,.25))">' +
          '<path d="M2 2 L2 20 L7 15.5 L10.5 22.5 L13.5 21 L10 14 L17 14 Z" fill="' + c.color +
          '" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>' +
          '<span style="position:absolute;left:16px;top:20px;white-space:nowrap;padding:3px 9px;border-radius:999px;' +
          'background:' + c.color + ';color:#fff;font:600 12px Be Vietnam Pro,sans-serif;box-shadow:0 3px 8px rgba(0,0,0,.15)">' +
          c.label + '</span>';
        o.appendChild(el);
        return {el, color: c.color, x: -200, y: -200, busy: false, holding: null};
      });
      return o;
    }
    function place(c, x, y) {
      c.el.getAnimations().forEach(a => a.cancel());
      c.x = x; c.y = y; c.el.style.transform = 'translate(' + x + 'px,' + y + 'px)';
    }
    function move(c, x, y, ms, ease) {
      const a = c.el.animate([{transform: 'translate(' + c.x + 'px,' + c.y + 'px)'},
        {transform: 'translate(' + x + 'px,' + y + 'px)'}], {duration: ms, easing: ease, fill: 'forwards'});
      c.x = x; c.y = y; c.el.style.transform = 'translate(' + x + 'px,' + y + 'px)';
      return a.finished.catch(() => {});
    }
    function offscreen(c) { return c.x < -20 || c.y < -20 || c.x > innerWidth + 20 || c.y > innerHeight + 20; }
    function ripple(x, y, color, size) {
      const r = document.createElement('div');
      r.style.cssText = 'position:absolute;left:' + (x - 6) + 'px;top:' + (y - 6) + 'px;width:12px;height:12px;' +
        'border-radius:50%;border:2px solid ' + color;
      overlay().appendChild(r);
      r.animate([{transform: 'scale(1)', opacity: .9}, {transform: 'scale(' + (size || 4) + ')', opacity: 0}],
        {duration: 480, easing: 'ease-out', fill: 'forwards'}).finished.then(() => r.remove(), () => r.remove());
    }
    function animating() { return S.cursors.some(c => c.busy); }

    // ---- mang khối từ ngoài màn hình vào
    function carry(els, frames) {
      overlay();
      const byTop = (a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top;
      // Vẽ khung trước, rồi mới mang nội dung vào.
      (frames || []).sort(byTop).concat(els.sort(byTop)).forEach(el => {
        if (!S.queue.includes(el) && !S.cursors.some(c => c.holding === el)) S.queue.push(el);
      });
      let k = 0;
      S.cursors.forEach(c => {
        if (!c.busy && S.queue.length > k) { worker(c, k * 90, S.gen); k++; }
      });
    }
    async function worker(c, delay, gen) {
      c.busy = true;
      await sleep(delay);
      while (S.queue.length && gen === S.gen) {
        const el = S.queue.shift();
        if (!el.isConnected) { show(el); showFrame(el); continue; }
        c.holding = el;
        if (S.frames.has(el)) await drawFrame(c, el, gen);
        else {
          const wait = framesReady(el);
          if (wait) { await wait; if (gen !== S.gen) return; }
          await carryOne(c, el, gen);
        }
        if (gen !== S.gen) return;
        c.holding = null;
      }
      if (gen !== S.gen) return;
      await move(c, c.x < innerWidth / 2 ? -90 : innerWidth + 90, c.y + 50, 360, 'cubic-bezier(.5,0,.75,0)');
      if (gen === S.gen) c.busy = false;
    }
    async function carryOne(c, el, gen) {
      const W = innerWidth, H = innerHeight;
      const r = el.getBoundingClientRect();
      const gx = r.left + Math.min(36, r.width * .3), gy = r.top + Math.min(16, r.height * .4);
      let dx, dy = (Math.random() - .5) * 140;
      if (r.top > H * .62) { dx = (Math.random() - .5) * 200; dy = H - r.top + 50; }
      else if (r.left + r.width / 2 < W / 2) dx = -(r.right + 60);
      else dx = W - r.left + 60;
      // Ra ngoài lấy khối (con trỏ đang khuất thì đặt luôn ở chỗ lấy).
      if (offscreen(c)) place(c, gx + dx, gy + dy);
      else await move(c, gx + dx, gy + dy, 300, 'cubic-bezier(.55,0,.8,.2)');
      if (gen !== S.gen) return;
      const rot = (dx > 0 ? 1 : -1) * (2 + Math.random() * 4);
      const D = 520, ease = 'cubic-bezier(.22,.8,.25,1)';
      const a = el.animate([{transform: 'translate(' + dx + 'px,' + dy + 'px) rotate(' + rot + 'deg)'},
        {transform: 'translate(0,0) rotate(0deg)'}], {duration: D, easing: ease});
      S.running.add(a);
      show(el);
      move(c, gx, gy, D, ease);
      await a.finished.catch(() => {});
      S.running.delete(a);
      if (gen !== S.gen) return;
      // Thả khối: nhấn chuột, gợn sóng, khối nảy nhẹ.
      ripple(gx, gy, c.color);
      c.el.firstChild.animate([{transform: 'scale(.78)'}, {transform: 'scale(1)'}], {duration: 180, easing: 'ease-out'});
      el.animate([{transform: 'translateY(-5px)'}, {transform: 'translateY(0)'}], {duration: 200, easing: 'cubic-bezier(.3,1.6,.5,1)'});
      await sleep(120);
    }

    // Con trỏ vẽ viền khung: chạy dọc theo viền, nét vẽ hiện ra theo sau.
    async function drawFrame(c, f, gen) {
      const info = S.frames.get(f);
      const r = f.getBoundingClientRect();
      const w = r.width, h = r.height, rr = Math.min(info.radius, w / 2, h / 2);
      const NS = 'http://www.w3.org/2000/svg';
      const svg = document.createElementNS(NS, 'svg');
      svg.setAttribute('class', 'dp-draw');
      svg.setAttribute('width', String(w + 2)); svg.setAttribute('height', String(h + 2));
      svg.style.cssText = 'position:absolute;overflow:visible;left:' + (r.left - 1) + 'px;top:' + (r.top - 1) + 'px';
      const path = document.createElementNS(NS, 'path');
      const x0 = 1, y0 = 1, x1 = w, y1 = h;
      path.setAttribute('d', ['M', x0 + rr, y0, 'H', x1 - rr, 'A', rr, rr, 0, 0, 1, x1, y0 + rr, 'V', y1 - rr,
        'A', rr, rr, 0, 0, 1, x1 - rr, y1, 'H', x0 + rr, 'A', rr, rr, 0, 0, 1, x0, y1 - rr, 'V', y0 + rr,
        'A', rr, rr, 0, 0, 1, x0 + rr, y0, 'Z'].join(' '));
      path.setAttribute('fill', 'none'); path.setAttribute('stroke', c.color);
      path.setAttribute('stroke-width', '2.2'); path.setAttribute('stroke-linecap', 'round');
      svg.appendChild(path); overlay().appendChild(svg);
      const len = path.getTotalLength();
      path.style.strokeDasharray = String(len); path.style.strokeDashoffset = String(len);
      const at = d => { const q = path.getPointAtLength(d); return [r.left - 1 + q.x, r.top - 1 + q.y]; };
      const [sx, sy] = at(0);
      if (offscreen(c)) place(c, sx < innerWidth / 2 ? -60 : innerWidth + 60, sy - 60);
      await move(c, sx, sy, 340, 'cubic-bezier(.3,.7,.3,1)');
      if (gen !== S.gen) { svg.remove(); return; }
      c.el.firstChild.animate([{transform: 'scale(1)'}, {transform: 'scale(.8)'}], {duration: 120, fill: 'forwards'});
      const D = Math.min(1100, 420 + len * .15), t0 = performance.now();
      for (;;) {
        const k = Math.min(1, (performance.now() - t0) / D);
        const e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        path.style.strokeDashoffset = String(len - e * len);
        const [x, y] = at(e * len);
        place(c, x, y);
        if (k >= 1) break;
        await sleep(16);
        if (gen !== S.gen) { svg.remove(); return; }
      }
      c.el.firstChild.animate([{transform: 'scale(.8)'}, {transform: 'scale(1)'}], {duration: 160, fill: 'forwards'});
      ripple(sx, sy, c.color);
      showFrame(f);
      svg.animate([{opacity: 1}, {opacity: 0}], {duration: 380, fill: 'forwards'})
        .finished.then(() => svg.remove(), () => svg.remove());
    }

    // ---- đổi tác vụ gấp: khối rơi nhanh ra từ vị trí con trỏ chuột
    function drop(els) {
      overlay();
      const p = S.ptr;
      ripple(p.x, p.y, '#F07167', 6);
      const dist = el => { const r = el.getBoundingClientRect(); return Math.hypot(r.left + r.width / 2 - p.x, r.top - p.y); };
      els.sort((a, b) => dist(a) - dist(b));
      els.forEach((el, i) => {
        const r = el.getBoundingClientRect();
        const dx = p.x - (r.left + r.width / 2), dy = p.y - (r.top + Math.min(20, r.height / 2));
        el.style.animation = 'none';
        el.animate([{transform: 'translate(' + dx + 'px,' + dy + 'px) scale(.1)', opacity: 0},
          {opacity: 1, offset: .3}, {transform: 'translate(0,0) scale(1)', opacity: 1}],
          {duration: 330, delay: Math.min(i * 26, 320), easing: 'cubic-bezier(.3,1.25,.55,1)', fill: 'backwards'});
        show(el);
      });
    }

    // Bấm tiếp khi con trỏ đang mang: dừng mang, phần còn lại rơi ra từ chỗ con trỏ chuột.
    function interrupt() {
      S.gen++;
      const rest = S.queue.splice(0);
      S.cursors.forEach(c => {
        if (c.holding) { rest.push(c.holding); c.holding = null; }
        c.busy = false;
        place(c, -200, -200);
      });
      S.running.forEach(a => a.finish());
      S.running.clear();
      if (S.overlay) S.overlay.querySelectorAll('.dp-draw').forEach(x => x.remove());
      Array.from(S.frames.keys()).forEach(showFrame);
      const live = rest.filter(el => el.isConnected && !S.frames.has(el) && el.matches(SEL));
      if (live.length) drop(live);
    }

    function destroy() {
      obs.disconnect();
      document.removeEventListener('pointerdown', onAct, true);
      document.removeEventListener('keydown', onKey, true);
      document.removeEventListener('pointermove', onMove, {capture: true});
      if (S.loop) clearInterval(S.loop);
      S.gen++;
      Array.from(S.hidden).forEach(show);
      Array.from(S.frames.keys()).forEach(showFrame);
      if (S.overlay) S.overlay.remove();
    }
    return {v, onRun, onDone, destroy, state: S};
  }
})();
</script>
"""


def intro(page: str = "home") -> None:
    """Các con trỏ mang tên công cụ dựng giao diện sau mỗi lần trang chạy lại (xem MOTION_JS)."""
    page = re.sub(r"[^\w-]", "", page) or "home"
    cursors = ", ".join(f'{{label: "{icon} {name}", color: "{color}"}}'
                        for _, name, icon, color, _ in MODULES)
    st.html(_js(MOTION_JS.replace("__CURSORS__", f"[{cursors}]").replace("__PAGE__", page)
                .replace("__RUN__", str(_time.time_ns()))),
            unsafe_allow_javascript=True)


def motion_done() -> None:
    """Báo cho bộ điều khiển hiệu ứng là trang đã chạy xong (gọi sau khi trang chạy, kể cả khi st.stop)."""
    st.html(_js(f'<div class="nh-invisible" data-run="{_time.time_ns()}"></div><script>'
                'if (window.__dpMotion && window.__dpMotion.onDone) window.__dpMotion.onDone();</script>'),
            unsafe_allow_javascript=True)


# --------------------------------------------------------------------------- pháo giấy
def confetti() -> None:
    nonce = _time.time_ns()
    st.html(_js(f"""<div class="nh-invisible" data-n="{nonce}"></div><script>
(function () {{
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const colors = ['#F07167','#FFB84C','#4D96FF','#6BCB77','#9D79BC','#F49CBB','#00AFB9'];
  const box = document.createElement('div');
  box.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:99998;overflow:hidden';
  document.body.appendChild(box);
  for (let i = 0; i < 140; i++) {{
    const p = document.createElement('i');
    const s = 6 + Math.random() * 7, x = Math.random() * 100, d = 1.6 + Math.random() * 1.6;
    p.style.cssText = 'position:absolute;top:-20px;left:' + x + 'vw;width:' + s + 'px;height:' + (s * .45) +
      'px;background:' + colors[i % colors.length] + ';border-radius:2px;opacity:.95';
    p.animate([{{transform: 'translate(0,0) rotate(0)'}},
      {{transform: 'translate(' + (Math.random() * 160 - 80) + 'px,' + (window.innerHeight + 60) + 'px) rotate(' + (Math.random() * 720) + 'deg)'}}],
      {{duration: d * 1000, delay: Math.random() * 400, easing: 'cubic-bezier(.25,.6,.4,1)', fill: 'forwards'}});
    box.appendChild(p);
  }}
  setTimeout(() => box.remove(), 4000);
}})();
</script>"""), unsafe_allow_javascript=True)


# --------------------------------------------------------------------------- đồng hồ tập trung
FOCUS_HTML = """
<div class="nh-focus" id="nh-focus">
  <style>
  .nh-focus {background:#fff;border-radius:22px;padding:18px 18px 16px;text-align:center;
    box-shadow:0 6px 20px rgba(240,113,103,.10);font-family:'Be Vietnam Pro',sans-serif;}
  .nh-focus .ttl {font-weight:700;color:#2B2D42;font-size:15px;margin-bottom:2px}
  .nh-focus .sub {font-size:12px;color:#8D99AE;margin-bottom:8px}
  .nh-focus .dial {position:relative;width:180px;height:180px;margin:0 auto}
  .nh-focus .bar {position:absolute;inset:0;border-radius:50%;
    background:conic-gradient(#F07167 calc(var(--p,100)*1%), #FDECE7 0);
    -webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 13px),#000 calc(100% - 12px));
            mask:radial-gradient(farthest-side,transparent calc(100% - 13px),#000 calc(100% - 12px))}
  .nh-focus .time {position:absolute;inset:0;display:grid;place-items:center;font-weight:800;
    font-size:36px;color:#2B2D42;font-variant-numeric:tabular-nums}
  .nh-focus .mode {position:absolute;left:0;right:0;top:118px;font-size:12px;color:#8D99AE;font-weight:600}
  .nh-focus .row {display:flex;gap:8px;justify-content:center;margin-top:12px;flex-wrap:wrap}
  .nh-focus button {border:none;border-radius:999px;padding:7px 14px;font:600 13px 'Be Vietnam Pro',sans-serif;
    cursor:pointer;background:#FDECE7;color:#C2410C;transition:transform .15s ease}
  .nh-focus button:hover {transform:translateY(-1px)}
  .nh-focus button.go {background:linear-gradient(135deg,#F07167,#F49CBB);color:#fff;min-width:92px}
  .nh-focus button.on {outline:2px solid #F07167}
  </style>
  <div class="ttl">⏱️ Tập trung</div>
  <div class="sub">Pomodoro: làm liền một khối, rồi nghỉ ngắn</div>
  <div class="dial">
    <div class="bar"></div>
    <div class="time">25:00</div><div class="mode">Sẵn sàng</div>
  </div>
  <div class="row">
    <button data-m="25" class="on">25 phút</button><button data-m="50">50 phút</button><button data-m="5">Nghỉ 5</button>
  </div>
  <div class="row"><button class="go">Bắt đầu</button><button class="reset">Đặt lại</button></div>
</div>
<script>
(function () {
  const root = document.getElementById('nh-focus');
  if (!root) return;
  if (window.__nhFocusTick) clearInterval(window.__nhFocusTick);
  const K = 'nhip-focus';
  const load = () => { try { return JSON.parse(localStorage.getItem(K)) || {}; } catch (e) { return {}; } };
  const save = s => localStorage.setItem(K, JSON.stringify(s));
  let s = Object.assign({minutes: 25, end: null, left: null}, load());
  const $ = q => root.querySelector(q);
  const bar = $('.bar'), time = $('.time'), mode = $('.mode'), go = $('.go');
  function chime() {
    try { const a = new (window.AudioContext || window.webkitAudioContext)();
      [660, 880, 990].forEach((f, i) => { const o = a.createOscillator(), g = a.createGain();
        o.frequency.value = f; o.connect(g); g.connect(a.destination);
        g.gain.setValueAtTime(.0001, a.currentTime + i * .18);
        g.gain.exponentialRampToValueAtTime(.2, a.currentTime + i * .18 + .02);
        g.gain.exponentialRampToValueAtTime(.0001, a.currentTime + i * .18 + .35);
        o.start(a.currentTime + i * .18); o.stop(a.currentTime + i * .18 + .4); });
    } catch (e) {}
  }
  function render() {
    const total = s.minutes * 60;
    let left = s.end ? Math.max(0, (s.end - Date.now()) / 1000) : (s.left ?? total);
    if (s.end && left <= 0) { s.end = null; s.left = null; save(s); chime(); mode.textContent = 'Xong! 🎉'; left = 0; }
    const m = Math.floor(left / 60), sec = Math.floor(left % 60);
    time.textContent = String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
    bar.style.setProperty('--p', (100 * left / total).toFixed(2));
    if (s.end) { mode.textContent = s.minutes === 5 ? 'Đang nghỉ' : 'Đang tập trung'; go.textContent = 'Tạm dừng'; }
    else { go.textContent = (s.left != null && s.left < total) ? 'Tiếp tục' : 'Bắt đầu';
      if (mode.textContent !== 'Xong! 🎉') mode.textContent = s.left != null && s.left < total ? 'Tạm dừng' : 'Sẵn sàng'; }
    root.querySelectorAll('[data-m]').forEach(b => b.classList.toggle('on', +b.dataset.m === s.minutes));
  }
  root.querySelectorAll('[data-m]').forEach(b => b.onclick = () => {
    s = {minutes: +b.dataset.m, end: null, left: null}; save(s); mode.textContent = 'Sẵn sàng'; render(); });
  go.onclick = () => {
    if (s.end) { s.left = Math.max(0, (s.end - Date.now()) / 1000); s.end = null; }
    else { const left = s.left ?? s.minutes * 60; s.end = Date.now() + left * 1000; s.left = null; mode.textContent = ''; }
    save(s); render(); };
  $('.reset').onclick = () => { s = {minutes: s.minutes, end: null, left: null}; save(s); mode.textContent = 'Sẵn sàng'; render(); };
  render();
  window.__nhFocusTick = setInterval(render, 250);
})();
</script>
"""


def focus_timer() -> None:
    st.html(_js(FOCUS_HTML), unsafe_allow_javascript=True)


def link(page: str, label: str, icon: str | None = None) -> None:
    """st.page_link nhưng không lỗi khi trang được chạy riêng lẻ (ngoài app.py, ví dụ trong test)."""
    from streamlit.errors import StreamlitPageNotFoundError

    try:
        st.page_link(page, label=label, icon=icon)
    except StreamlitPageNotFoundError:
        pass


def week_bars(days: list, study: dict, classes: dict, today) -> str:
    """Biểu đồ cột 7 ngày: giờ tự học (san hô) chồng lên giờ lên lớp (xám)."""
    from modules.scheduler.model import WEEKDAY_VN

    peak = max([study.get(d, 0) + classes.get(d, 0) for d in days] + [4])
    cols = []
    for i, d in enumerate(days):
        s_h, c_h = study.get(d, 0), classes.get(d, 0)
        total = s_h + c_h
        px = lambda h: f"{h / peak * 110:.0f}px"  # noqa: E731
        cols.append(
            f'<div class="col{" today" if d == today else ""}"><div class="h">{round(total, 1):g}h</div>'
            f'<div class="stack" style="animation-delay:{i * 70}ms">'
            f'<i style="height:{px(c_h)};background:#ADB5BD"></i>'
            f'<i style="height:{px(s_h)};background:linear-gradient(180deg,#F49CBB,#F07167)"></i></div>'
            f'<div class="d">{WEEKDAY_VN[d.weekday()].replace("Thứ ", "T")}</div></div>')
    return ('<div class="nh-week">' + "".join(cols) + '</div><div class="nh-legend">'
            '<span style="--c:#F07167">Tự học</span><span style="--c:#ADB5BD">Lên lớp</span></div>')
