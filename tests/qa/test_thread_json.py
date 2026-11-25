import json

from modules.qa.models.answer import Answer, RejectionReason
from modules.qa.models.citation import Citation
from modules.qa.models.thread import PassageThread
from modules.qa.thread_json import threads_from_json, threads_to_json


def test_threads_round_trip_through_json():
    t = PassageThread(doc_id="d1", page_num=2, selected_text="Hạn nộp 23h59 ngày 05/12",
                      rects=[{"x": 1, "y": 2, "w": 3, "h": 4}], questions=["Hạn nộp khi nào?"],
                      history=[("user", "Hạn nộp khi nào?"), ("assistant", "05/12")], selection_verified=True)
    t.answers.append(Answer(answer_id="a1", doc_id="d1", question_id="q1", text="Hạn là 05/12.",
                            citations=[Citation(page_num=2, evidence_text="05/12")]))
    t.answers.append(Answer(answer_id="a2", doc_id="d1", question_id="q2", text="", can_answer=False,
                            rejection_reason=RejectionReason.NO_CITATION))
    restored = threads_from_json(json.loads(json.dumps(threads_to_json({t.thread_id: t}), ensure_ascii=False)))
    r = restored[t.thread_id]
    assert (r.doc_id, r.page_num, r.selected_text, r.rects, r.questions) == \
        (t.doc_id, t.page_num, t.selected_text, t.rects, t.questions)
    assert r.history == t.history and r.created_at == t.created_at and r.selection_verified
    assert r.answers[0].citations[0].evidence_text == "05/12"
    assert r.answers[1].rejection_reason is RejectionReason.NO_CITATION


def test_broken_records_are_skipped():
    assert threads_from_json([{"doc_id": "x"}, None and {}]) == {}
    assert threads_from_json(None) == {}
