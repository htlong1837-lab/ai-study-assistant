"""Human-reviewed JSONL dataset validation for Module A."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TYPES = {"whole_document", "passage", "unanswerable"}
FULL_COUNTS = {"whole_document": 12, "passage": 12, "unanswerable": 6}
FIELDS = {
    "id",
    "type",
    "question",
    "gold_answer",
    "gold_pages",
    "gold_evidence",
    "needs_human_review",
    "review_notes",
    "passage_page",
    "passage_text",
}


@dataclass
class DatasetReport:
    records: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def validate_dataset(path: str | Path, *, full: bool = False) -> DatasetReport:
    report = DatasetReport()
    dataset_path = Path(path)
    try:
        lines = dataset_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        report.errors.append(f"{dataset_path}: cannot read dataset: {exc}")
        return report

    seen: set[str] = set()
    counts: Counter[str] = Counter()
    for line_num, raw in enumerate(lines, 1):
        if not raw.strip():
            report.errors.append(f"line {line_num}: blank JSONL lines are not allowed")
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            report.errors.append(
                f"line {line_num}: invalid JSON: {exc.msg} (column {exc.colno})"
            )
            continue
        if not isinstance(obj, dict):
            report.errors.append(f"line {line_num}: expected a JSON object")
            continue
        record_id = obj.get("id")
        label = (
            f"record {record_id!r}"
            if isinstance(record_id, str)
            else "record with missing/invalid id"
        )
        prefix = f"line {line_num}, {label}: "
        missing = FIELDS - obj.keys()
        if missing:
            report.errors.append(
                prefix + "missing fields: " + ", ".join(sorted(missing))
            )
            continue
        if not isinstance(record_id, str) or not record_id.strip():
            report.errors.append(prefix + "id must be a non-empty string")
        elif record_id in seen:
            report.errors.append(prefix + "duplicate id")
        else:
            seen.add(record_id)

        kind = obj["type"]
        if not isinstance(kind, str) or kind not in TYPES:
            report.errors.append(
                prefix + f"type must be one of {', '.join(sorted(TYPES))}"
            )
        else:
            counts[kind] += 1
        for field_name in ("question", "review_notes"):
            if not isinstance(obj[field_name], str):
                report.errors.append(prefix + f"{field_name} must be a string")
        if not isinstance(obj["needs_human_review"], bool):
            report.errors.append(prefix + "needs_human_review must be boolean")
        if obj["gold_answer"] is not None and not isinstance(obj["gold_answer"], str):
            report.errors.append(prefix + "gold_answer must be a string or null")
        if not isinstance(obj["passage_text"], str):
            report.errors.append(prefix + "passage_text must be a string")

        pages, evidence = obj["gold_pages"], obj["gold_evidence"]
        if not isinstance(pages, list) or any(
            type(page) is not int or page < 1 for page in pages
        ):
            report.errors.append(
                prefix + "gold_pages must be a list of positive page integers"
            )
        if not isinstance(evidence, list) or any(
            not isinstance(item, str) for item in evidence
        ):
            report.errors.append(prefix + "gold_evidence must be a list of strings")

        answer = obj["gold_answer"]
        pending = obj["needs_human_review"] is True
        if pending:
            report.pending.append(f"line {line_num}, {label}: pending human review")
        elif not isinstance(answer, str) or not answer.strip():
            report.errors.append(
                prefix + "reviewed gold_answer must be a non-empty string"
            )
        if kind == "unanswerable":
            if pages != []:
                report.errors.append(
                    prefix + "unanswerable records must have empty gold_pages"
                )
            if evidence != []:
                report.errors.append(
                    prefix + "unanswerable records must have empty gold_evidence"
                )
        elif not pending:
            if not isinstance(pages, list) or not pages:
                report.errors.append(
                    prefix + "reviewed answerable records need at least one gold page"
                )
            if (
                not isinstance(evidence, list)
                or not evidence
                or any(not e.strip() for e in evidence)
            ):
                report.errors.append(
                    prefix + "reviewed answerable records need non-empty gold evidence"
                )
        passage_page, passage_text = obj["passage_page"], obj["passage_text"]
        if kind == "passage":
            if passage_page is not None and (
                type(passage_page) is not int or passage_page < 1
            ):
                report.errors.append(
                    prefix + "passage_page must be a positive integer or null"
                )
            if not pending and (type(passage_page) is not int or passage_page < 1):
                report.errors.append(
                    prefix + "reviewed passage records need a positive passage_page"
                )
            if not pending and (
                not isinstance(passage_text, str) or not passage_text.strip()
            ):
                report.errors.append(
                    prefix + "reviewed passage records need non-empty passage_text"
                )
        elif passage_page is not None or passage_text != "":
            report.errors.append(
                prefix
                + "passage_page/text must be null/empty except for passage records"
            )
        if not pending:
            text_fields = [("question", obj["question"]), ("gold_answer", answer)]
            if isinstance(evidence, list):
                text_fields.extend(
                    ("gold_evidence", item)
                    for item in evidence
                    if isinstance(item, str)
                )
            for field_name, value in text_fields:
                if isinstance(value, str) and value.strip().lower() in {
                    "todo",
                    "tbd",
                    "placeholder",
                    "fill me",
                    "n/a",
                }:
                    report.errors.append(
                        prefix + f"{field_name} still contains a placeholder"
                    )
        if (
            not pending
            and isinstance(obj["question"], str)
            and not obj["question"].strip()
        ):
            report.errors.append(prefix + "reviewed question must be non-empty")
        report.records.append(obj)

    if full:
        if len(report.records) != 30:
            report.errors.append(
                f"full benchmark requires exactly 30 records; found {len(report.records)}"
            )
        for kind, expected in FULL_COUNTS.items():
            if counts[kind] != expected:
                report.errors.append(
                    f"full benchmark requires {expected} {kind} records; found {counts[kind]}"
                )
        if report.pending:
            report.errors.append(
                f"full benchmark has {len(report.pending)} record(s) pending human review"
            )
    return report
