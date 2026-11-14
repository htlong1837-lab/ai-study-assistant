from core import mocks
from core.contracts import SafetyStatus, TaskStatus, can_forward

FACTORIES = [mocks.emails, mocks.attachments, mocks.documents,
             mocks.tasks, mocks.study_blocks, mocks.reminders]


def test_each_mock_has_at_least_three_records():
    for factory in FACTORIES:
        assert len(factory()) >= 3, factory.__name__


def test_emails_cover_all_safety_states():
    assert {e.safety for e in mocks.emails()} == set(SafetyStatus)


def test_attachments_only_from_forwardable_emails():
    ok = {e.id for e in mocks.emails() if can_forward(e)}
    assert all(a.email_id in ok for a in mocks.attachments())


def test_tasks_have_proposed_and_confirmed_with_source():
    tasks = mocks.tasks()
    assert {TaskStatus.PROPOSED, TaskStatus.CONFIRMED} <= {t.status for t in tasks}
    assert all(t.source and 0 <= t.confidence <= 1 for t in tasks)


def test_blocks_and_reminders_point_to_confirmed_tasks():
    confirmed = {t.id for t in mocks.tasks() if t.status is TaskStatus.CONFIRMED}
    assert all(b.task_id in confirmed for b in mocks.study_blocks())
    assert all(r.task_id in confirmed for r in mocks.reminders())


def test_mocks_return_fresh_copies():
    first = mocks.tasks()
    first[0].title = "đã sửa"
    assert mocks.tasks()[0].title != "đã sửa"
