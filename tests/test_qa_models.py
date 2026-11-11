from modules.qa.models import Answer, RejectionReason


def test_rejection_reason_round_trips_and_reads_legacy_missing_fields():
    answer = Answer(
        answer_id="a",
        doc_id="d",
        question_id="q",
        text="No support",
        status="rejected",
        rejection_reason="WEAK_SUPPORT",
    )
    assert answer.rejection_reason is RejectionReason.WEAK_SUPPORT
    restored = Answer.from_dict(answer.to_dict())
    assert restored.rejection_reason is RejectionReason.WEAK_SUPPORT
    legacy = Answer.from_dict(
        {"answer_id": "old", "doc_id": "d", "question_id": "q", "text": "old"}
    )
    assert legacy.rejection_reason is None
