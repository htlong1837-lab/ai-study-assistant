import json

from modules.qa.benchmark import validate_dataset


def record(record_id="q1", kind="whole_document", *, reviewed=False):
    return {
        "id": record_id,
        "type": kind,
        "question": "Question?" if reviewed else "",
        "gold_answer": "Gold answer." if reviewed else None,
        "gold_pages": [1] if reviewed and kind != "unanswerable" else [],
        "gold_evidence": ["Evidence."] if reviewed and kind != "unanswerable" else [],
        "needs_human_review": not reviewed,
        "review_notes": "",
        "passage_page": 1 if reviewed and kind == "passage" else None,
        "passage_text": "Source passage." if reviewed and kind == "passage" else "",
    }


def write(tmp_path, rows):
    path = tmp_path / "data.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return path


def test_draft_records_are_reported_pending_not_gold(tmp_path):
    report = validate_dataset(write(tmp_path, [record()]))
    assert report.valid
    assert len(report.pending) == 1


def test_reviewed_answerable_record_requires_gold_fields(tmp_path):
    row = record(reviewed=True)
    row["gold_evidence"] = []
    report = validate_dataset(write(tmp_path, [row]))
    assert any("gold evidence" in error for error in report.errors)


def test_unanswerable_must_have_empty_pages_and_evidence(tmp_path):
    row = record(kind="unanswerable")
    row["gold_pages"] = [2]
    report = validate_dataset(write(tmp_path, [row]))
    assert any("empty gold_pages" in error for error in report.errors)


def test_duplicate_ids_and_bad_json_have_line_numbers(tmp_path):
    path = tmp_path / "data.jsonl"
    path.write_text(
        json.dumps(record()) + "\n{" + "\n" + json.dumps(record()), encoding="utf-8"
    )
    report = validate_dataset(path)
    assert any("line 2" in error and "invalid JSON" in error for error in report.errors)
    assert any("duplicate id" in error for error in report.errors)


def test_full_mode_checks_distribution_and_review_completion(tmp_path):
    report = validate_dataset(write(tmp_path, [record()]), full=True)
    assert any("exactly 30" in error for error in report.errors)
    assert any("pending human review" in error for error in report.errors)


def test_complete_full_distribution_is_accepted(tmp_path):
    rows = (
        [record(f"w{i}", "whole_document", reviewed=True) for i in range(12)]
        + [record(f"p{i}", "passage", reviewed=True) for i in range(12)]
        + [record(f"u{i}", "unanswerable", reviewed=True) for i in range(6)]
    )
    report = validate_dataset(write(tmp_path, rows), full=True)
    assert report.valid
    assert not report.pending


def test_wrongly_typed_record_kind_fails_without_crashing(tmp_path):
    row = record()
    row["type"] = []
    report = validate_dataset(write(tmp_path, [row]))
    assert any("type must be one of" in error for error in report.errors)
