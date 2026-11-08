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

# Files/directories that are allowed to mention regexes, placeholders, or security docs
EXCLUDED_PATTERNS = [
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "test_no_secrets.py",  # This file itself contains the regex patterns
    "test_api_key_lifecycle.py", # Tests masking of sample key strings
    "security.py",        # Contains regex patterns for masking
    "SECURITY_TODO.md",   # Contains the revoked key for documentation purposes
    "verification-log.md",# Contains audit log of the revoked key
]


def test_no_hardcoded_secrets() -> None:
    root = Path(__file__).resolve().parent.parent
    violations: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        # Skip excluded dirs/files
        rel_str = str(path.relative_to(root)).replace("\\", "/")
        if any(excluded in rel_str for excluded in EXCLUDED_PATTERNS):
            continue
        # Only check text-based files
        if path.suffix in {".py", ".yaml", ".yml", ".json", ".env", ".txt", ".md", ".sh", ".ps1"}:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for pattern in SECRET_PATTERNS:
                matches = pattern.findall(content)
                for match in matches:
                    # Ignore obvious placeholders
                    if "FAKE" in match or "PLACEHOLDER" in match or "YOUR_KEY" in match:
                        continue
                    violations.append(f"{rel_str}: found potential secret pattern '{match[:8]}...'")

    assert not violations, "Found potential hardcoded API secrets in codebase:\n" + "\n".join(violations)
