"""Isolated child process used to parse untrusted PDF files."""

from __future__ import annotations

import json
import sys

from .document_parser import parse_document


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("Expected temporary PDF path and document ID.", file=sys.stderr)
        return 2
    try:
        document = parse_document(args[0], args[1])
        print(
            json.dumps(
                {
                    "doc_id": document.doc_id,
                    "filename": document.filename,
                    "pages": [
                        {"number": page.number, "text": page.text}
                        for page in document.pages
                    ],
                },
                ensure_ascii=True,
            )
        )
        return 0
    except Exception as exc:
        print(f"{type(exc).__name__}: {str(exc)[:1000]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
