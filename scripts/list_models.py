#!/usr/bin/env python
"""CLI script: list Gemini models available on a given API key.

Usage
-----
    python scripts/list_models.py --api-key YOUR_KEY
    python scripts/list_models.py          # prompts securely
"""
from __future__ import annotations

import argparse
import getpass
import sys


def _list_via_genai(api_key: str) -> bool:
    """Try to list models via the ``google-genai`` SDK.  Returns True on success."""
    try:
        from google import genai  # type: ignore[import-untyped]
    except ImportError:
        return False

    client = genai.Client(api_key=api_key, http_options={"timeout": 15_000})
    try:
        models = list(client.models.list())
    except Exception as exc:
        print(f"[google-genai] Error: {exc}", file=sys.stderr)
        return False

    print(f"\n{'Model ID':<45} {'Display Name':<50} {'Methods'}")
    print("-" * 120)
    for m in models:
        model_id = getattr(m, "name", "") or ""
        display = getattr(m, "display_name", "") or ""
        methods = ", ".join(getattr(m, "supported_generation_methods", []) or [])
        marker = "  ✅" if "generateContent" in (methods or "") else "    "
        print(f"{marker} {model_id:<43} {display:<50} {methods}")
    print(f"\nTotal: {len(models)} models listed.\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="List available Gemini models for a given API key.")
    parser.add_argument("--api-key", help="Gemini API key (omit to be prompted securely)")
    args = parser.parse_args()

    api_key = args.api_key
    if not api_key:
        api_key = getpass.getpass("Enter your Gemini API key: ")

    if not api_key.strip():
        print("Error: API key cannot be empty.", file=sys.stderr)
        sys.exit(1)

    print("Fetching available Gemini models…")

    if not _list_via_genai(api_key):
        print("Error: google-genai is not installed or could not list models.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
