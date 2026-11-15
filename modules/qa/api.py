"""Small public handoff API for other modules consuming the current QA document."""


def get_current_document(session_state):
    return session_state.get("qa_document")
