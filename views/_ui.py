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

/* Xuất hiện dần khi phần tử mới được gắn vào trang */
@keyframes nh-rise {from {opacity: 0; transform: translateY(10px);} to {opacity: 1; transform: none;}}
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"],
[data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"] {
  animation: nh-rise .45s cubic-bezier(.2,.7,.2,1) both;
}

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


# --------------------------------------------------------------------------- màn mở đầu
INTRO_JS = """
<div class="nh-invisible" data-page="__PAGE__"></div>
<script>
window.__nhIntroRun = function () {
  const KEY = 'nhip-intro-v2:__PAGE__';
  if (window.__nhIntro || sessionStorage.getItem(KEY)) return;
  window.__nhIntro = true;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const CURSORS = __CURSORS__;
  const main = () => document.querySelector('[data-testid="stMainBlockContainer"]');

  // Mục tiêu: từng thẻ nhỏ (hero, ô số liệu, thẻ viền, thẻ module, nhãn mục), chỉ lấy lớp ngoài cùng.
  const SEL = ['.nh-hero', '.nh-head', '.tl', '[data-testid="stMetric"]', '[data-testid="stVerticalBlockBorderWrapper"]',
    '[data-testid="stHeading"]', '[data-testid="stExpander"]', '[data-testid="stPageLink"]', '[data-testid="stAlert"]',
    '[data-testid="stForm"]', '[data-testid="stDataFrame"]', '[data-testid="stTable"]', '[data-testid="stFileUploader"]',
    '[data-testid="stButton"]', '[data-testid="stDownloadButton"]', '[data-testid="stTextInput"]',
    '[data-testid="stTextArea"]', '[data-testid="stSelectbox"]', '[data-testid="stRadio"]',
    '[data-testid="stSlider"]', '[data-testid="stNumberInput"]', '[data-testid="stDateInput"]',
    '[data-testid="stCheckbox"]', '[data-testid="stButtonGroup"]', '[data-testid="stCaptionContainer"]',
    '[data-testid="stArrowVegaLiteChart"]', '[data-testid="stVegaLiteChart"]', '[data-testid="stIFrame"]',
    '[data-testid="stCustomComponentV1"]', '[data-testid="stCode"]', '[data-testid="stHtml"]'].join(', ');
  function blocks() {
    const m = main();
    if (!m) return [];
    const all = Array.from(m.querySelectorAll(SEL)).filter(el => {
      const r = el.getBoundingClientRect();
      return r.height > 8 && r.width > 8;
    });
    return all.filter(el => !all.some(o => o !== el && o.contains(el)));
  }

  function waitStable(cb) {
    let last = -1, same = 0, tries = 0;
    const t = setInterval(() => {
      const n = blocks().length; tries++;
      same = (n === last && n > 0) ? same + 1 : 0; last = n;
      if (same >= 3 || tries > 40) { clearInterval(t); cb(); }
    }, 100);
  }

  function finish(els, overlay) {
    els.forEach(el => { el.style.opacity = ''; el.style.transform = ''; el.style.filter = '';
      el.style.animation = ''; el.style.transition = ''; });
    if (overlay) { overlay.style.opacity = '0'; setTimeout(() => overlay.remove(), 500); }
    sessionStorage.setItem(KEY, '1');
    window.__nhIntro = false;
  }

  waitStable(() => {
    const els = blocks();
    if (reduce || !els.length) { finish(els, null); return; }
    const vh = window.innerHeight;
    const visible = els.filter(el => el.getBoundingClientRect().top < vh - 40);
    els.forEach(el => {
      el.style.animation = 'none';  // hiệu ứng CSS "xuất hiện dần" sẽ đè lên lệnh ẩn nếu không tắt
      el.style.transition = 'opacity .55s ease, transform .6s cubic-bezier(.2,.8,.2,1), filter .6s ease';
      el.style.opacity = '0'; el.style.transform = 'translateY(26px) scale(.97)'; el.style.filter = 'blur(4px)';
    });

    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;pointer-events:none;transition:opacity .5s';
    document.body.appendChild(overlay);
    const skip = document.createElement('button');
    skip.textContent = 'Bỏ qua ›';
    skip.style.cssText = 'position:fixed;right:22px;bottom:22px;pointer-events:auto;border:none;' +
      'border-radius:999px;padding:8px 16px;background:#2B2D42;color:#fff;font:600 13px "Be Vietnam Pro",sans-serif;' +
      'cursor:pointer;opacity:.85;box-shadow:0 6px 18px rgba(0,0,0,.2)';
    overlay.appendChild(skip);
    let done = false;
    const end = () => { if (done) return; done = true; finish(els, overlay); };
    skip.onclick = end;

    const W = window.innerWidth, H = window.innerHeight;
    const starts = [[-60, H * .25], [W + 40, H * .15], [W * .3, H + 50], [W + 40, H * .8]];
    const cs = CURSORS.map((c, i) => {
      const el = document.createElement('div');
      el.style.cssText = 'position:fixed;left:0;top:0;will-change:transform;' +
        'transition:transform .75s cubic-bezier(.65,0,.35,1)';
      el.innerHTML = '<svg width="22" height="24" viewBox="0 0 22 24" style="filter:drop-shadow(0 2px 3px rgba(0,0,0,.25))">' +
        '<path d="M2 2 L2 20 L7 15.5 L10.5 22.5 L13.5 21 L10 14 L17 14 Z" fill="' + c.color + '" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>' +
        '<span style="position:absolute;left:16px;top:20px;white-space:nowrap;padding:3px 9px;border-radius:999px;' +
        'background:' + c.color + ';color:#fff;font:600 12px \\'Be Vietnam Pro\\',sans-serif;box-shadow:0 3px 8px rgba(0,0,0,.15)">' +
        c.label + '</span>';
      const s = starts[i % starts.length];
      el.style.transform = 'translate(' + s[0] + 'px,' + s[1] + 'px)';
      overlay.appendChild(el);
      return {el, color: c.color};
    });

    function ripple(x, y, color) {
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;left:' + (x - 6) + 'px;top:' + (y - 6) + 'px;width:12px;height:12px;' +
        'border-radius:50%;border:2px solid ' + color + ';opacity:.9;transition:transform .5s ease,opacity .5s ease';
      overlay.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(4)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }
    function frame(rect, color) {
      const f = document.createElement('div');
      f.style.cssText = 'position:fixed;left:' + (rect.left - 4) + 'px;top:' + (rect.top - 4) + 'px;width:' +
        (rect.width + 8) + 'px;height:' + (rect.height + 8) + 'px;border:2px dashed ' + color +
        ';border-radius:14px;opacity:0;transition:opacity .25s ease';
      overlay.appendChild(f);
      requestAnimationFrame(() => f.style.opacity = '1');
      setTimeout(() => { f.style.opacity = '0'; setTimeout(() => f.remove(), 300); }, 520);
    }
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    function typeText(h) {
      const full = Array.from(h.textContent); let i = 0;
      h.textContent = '';
      const t = setInterval(() => { h.textContent = full.slice(0, ++i).join(''); if (i >= full.length) clearInterval(t); }, 38);
    }

    async function work(ci, queue) {
      const c = cs[ci];
      await sleep(ci * 160);
      for (const el of queue) {
        if (done) return;
        const r = el.getBoundingClientRect();
        const x = r.left + Math.min(r.width * (.25 + Math.random() * .5), r.width - 30);
        const y = r.top + Math.min(Math.max(r.height * .4, 14), 60);
        c.el.style.transform = 'translate(' + x + 'px,' + y + 'px)';
        await sleep(780);
        if (done) return;
        c.el.firstChild.style.transform = 'scale(.82)';
        ripple(x, y, c.color); frame(r, c.color);
        el.style.opacity = '1'; el.style.transform = 'none'; el.style.filter = 'none';
        const h = el.querySelector('.nh-hero h1');
        if (h) typeText(h);
        await sleep(160);
        c.el.firstChild.style.transform = '';
        await sleep(220);
      }
    }

    const queues = cs.map(() => []);
    // Chia theo cột: con trỏ gần mục nào thì dựng mục đó, để các con trỏ không bay chéo nhau.
    visible.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    visible.forEach((el, i) => queues[i % cs.length].push(el));
    Promise.all(cs.map((_, i) => work(i, queues[i]))).then(async () => {
      if (done) return;
      els.forEach(el => { el.style.opacity = '1'; el.style.transform = 'none'; el.style.filter = 'none'; });
      cs.forEach((c, i) => { c.el.style.transform = 'translate(' + (i % 2 ? W + 80 : -80) + 'px,' + (H * (.2 + i * .2)) + 'px)'; });
      await sleep(700);
      end();
    });
    setTimeout(end, 12000);  // lưới an toàn
  });
};
window.__nhIntroRun();
</script>
"""


def intro(page: str = "home") -> None:
    """Màn mở đầu: các con trỏ mang tên công cụ bay vào, bấm dựng từng phần trang.

    Mỗi trang chạy một lần mỗi phiên trình duyệt (khoá theo ``page``). ``page`` cũng làm nội dung
    khối HTML khác nhau giữa các trang, để Streamlit dựng lại khối và chạy lại script khi chuyển trang.
    """
    page = re.sub(r"[^\w-]", "", page) or "home"
    cursors = ", ".join(f'{{label: "{icon} {name}", color: "{color}"}}'
                        for _, name, icon, color, _ in MODULES)
    st.html(_js(INTRO_JS.replace("__CURSORS__", f"[{cursors}]").replace("__PAGE__", page)),
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
