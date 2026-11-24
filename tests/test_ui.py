"""Giao diện chung: chặn các lỗi khiến bộ lọc DOMPurify của st.html xoá mất CSS/JS/SVG."""
import re
from datetime import datetime

from views import _timeline, _ui

TAG_LIKE = re.compile(r"<[/\w!]")


def _blocks(html: str, tag: str) -> list[str]:
    return re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.S)


def test_style_blocks_have_no_tag_like_text():
    """DOMPurify (SAFE_FOR_XML) xoá cả thẻ <style> nếu bên trong có dạng `<number>`, `</x>`."""
    for html in (_ui.GLOBAL_CSS, _ui.FOCUS_HTML, _timeline.CSS):
        for css in _blocks(html, "style"):
            assert not TAG_LIKE.search(css)


def test_scripts_are_escaped_before_rendering():
    for html in (_ui.INTRO_JS, _ui.FOCUS_HTML):
        for js in _blocks(_ui._js(html), "script"):
            assert not TAG_LIKE.search(js)


def test_no_svg_outside_scripts():
    """Hồ sơ HTML của st.html không cho SVG: phần tĩnh phải vẽ bằng CSS."""
    for html in (_ui.GLOBAL_CSS, re.sub(r"<script.*?</script>", "", _ui.FOCUS_HTML, flags=re.S),
                 _ui.ring(3, 4, "tuần"), _timeline.render([])):
        assert "<svg" not in html


def test_ring_percent():
    assert "75%" in _ui.ring(3, 4, "tuần")
    assert "0%" in _ui.ring(0, 0, "tuần")


def test_greeting_by_hour():
    assert _ui.greeting(datetime(2026, 11, 25, 0, 50)).startswith("Khuya")
    assert _ui.greeting(datetime(2026, 11, 25, 8, 0)) == "Chào buổi sáng"
    assert _ui.greeting(datetime(2026, 11, 25, 20, 0)) == "Chào buổi tối"


def test_timeline_now_marker_and_gaps():
    day = datetime(2026, 11, 25)
    items = [
        _timeline.Item(day.replace(hour=7), day.replace(hour=9), "Ôn AI", "Tự học", "📖", "#F07167"),
        _timeline.Item(day.replace(hour=13), day.replace(hour=15), "CSDL", "Lên lớp", "🏫", "#ADB5BD",
                       done=True),
    ]
    html = _timeline.render(items, now=day.replace(hour=10, minute=30))
    assert html.index("Ôn AI") < html.index('<div class="tl-now">') < html.index("CSDL")  # vạch giờ nằm giữa
    assert "4 giờ rảnh" in html
    assert "tl-done" in html
    assert "<script" not in html and "&lt;" not in html.split("</style>")[0]


def test_timeline_escapes_titles():
    day = datetime(2026, 11, 25, 8)
    html = _timeline.render([_timeline.Item(day, day, "<b>x</b>", "", "📌", "#000")])
    assert "<b>x</b>" not in html and "&lt;b&gt;" in html
