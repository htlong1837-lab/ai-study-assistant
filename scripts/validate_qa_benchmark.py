from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.qa.benchmark import validate_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the human-authored Module A QA JSONL benchmark."
    )
    parser.add_argument(
        "--dataset", default=str(ROOT / "benchmarks" / "qa" / "dataset.jsonl")
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="require the reviewed 30-record 12/12/6 dataset",
    )
    args = parser.parse_args()
    report = validate_dataset(args.dataset, full=args.full)
    for item in report.errors:
        print("ERROR: " + item)
    for item in report.pending:
        print("PENDING: " + item)
    if report.errors:
        return 1
    if report.pending:
        print(
            f"Structure valid: {len(report.records)} records; {len(report.pending)} await human review."
        )
    else:
        print(f"Dataset valid: {len(report.records)} records; all records reviewed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
