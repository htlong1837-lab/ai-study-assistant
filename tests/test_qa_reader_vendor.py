from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "modules" / "qa" / "reader" / "frontend"
VENDOR = FRONTEND / "vendor" / "pdfjs"


def test_pdfjs_version_and_required_assets_are_present():
    assert "pdfjs-dist 6.4.299" in (VENDOR / "VERSION").read_text(encoding="utf-8")
    assert (VENDOR / "pdf.mjs").is_file()
    assert (VENDOR / "pdf.worker.mjs").is_file()
    assert "Apache License" in (VENDOR / "LICENSE").read_text(encoding="utf-8")


def test_reader_frontend_uses_text_apis_not_html_injection():
    source = (FRONTEND / "app" / "reader.js").read_text(encoding="utf-8")
    assert "innerHTML" not in source
    assert "insertAdjacentHTML" not in source
    assert "textContent" in source
    assert "new pdfjs.TextLayer" in source
    assert "event.source!==window.parent" in source
    assert "isEvalSupported:false" in source and "enableScripting:false" in source
    assert "releasePage" in source
