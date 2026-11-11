from modules.qa.models import Answer, Citation
from modules.qa.models.thread import PassageThread
from modules.qa.reader.threads import ThreadStore, export_markdown, make_thread_id


def test_thread_id_is_stable_for_normalized_passage_and_scoped_to_document():
    assert make_thread_id("doc", 2, "Tiếng Việt") == make_thread_id(
        "doc", 2, "  TIẾNG   VIỆT  "
    )
    assert make_thread_id("doc", 2, "text") != make_thread_id("other", 2, "text")
    assert make_thread_id("doc", 2, "text") != make_thread_id("doc", 3, "text")
    assert PassageThread("doc", 2, "text").thread_id == make_thread_id("doc", 2, "text")


def test_thread_store_reopens_same_passage_and_preserves_first_thread():
    state = {}
    store = ThreadStore(state)
    first = store.get_or_create("doc", 1, "A passage", [{"page": 1}])
    first.questions.append("Explain")
    second = store.get_or_create("doc", 1, " a  passage ", [{"page": 1}])
    assert second is first
    assert second.questions == ["Explain"]
    assert second.rects == [{"page": 1}]


def test_export_contains_conversation_citations_and_no_private_metadata():
    thread = PassageThread("doc", 3, "A selected sentence", thread_id="safe-id")
    thread.questions.append("What does it mean?")
    thread.answers.append(
        Answer(
            "answer-id",
            "doc",
            "question-id",
            "A supported explanation.",
            citations=[Citation(3, "A selected sentence")],
            background_note="Additional context.",
        )
    )
    markdown = export_markdown("sample.pdf", {thread.thread_id: thread})
    assert "**Bạn:** What does it mean?" in markdown
    assert "**Trợ lý:** A supported explanation." in markdown
    assert "trang 3" in markdown
    assert "Additional context." in markdown
    assert "answer-id" not in markdown and "question-id" not in markdown
