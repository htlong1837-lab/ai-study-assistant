"""Security test: ensure no hardcoded API secrets exist anywhere in the codebase."""
from __future__ import annotations

import re
from pathlib import Path

# Patterns that match real API keys:
# - Google GenAI API keys with AQ. prefix
# - Google API keys with AIza prefix (followed by 35 base64url characters)
# - OpenAI keys with sk- prefix
SECRET_PATTERNS = [
    re.compile(r"AQ\.[A-Za-z0-9_\-]{30,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

def test_no_hardcoded_secrets() -> None:
    root = Path(__file__).resolve().parent.parent
    violations: list[str] = []
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".cache"}
    ignored_names = {"test_no_secrets.py", ".env"}
    text_extensions = {".py", ".yaml", ".yml", ".json", ".txt", ".md", ".sh", ".ps1"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root)
        if (any(part in ignored_dirs for part in rel_path.parts)
                or rel_path.name in ignored_names
                or rel_path.suffix.lower() not in text_extensions):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            violations.append(rel_path.as_posix())

    assert not violations, "Potential API key pattern found in tracked files: " + ", ".join(violations)
