import pytest

from modules.qa.messages import rejection_message
from modules.qa.models import RejectionReason


@pytest.mark.parametrize("reason", list(RejectionReason))
def test_each_rejection_reason_has_vietnamese_user_message(reason):
    message = rejection_message(reason)
    assert message and ("chưa" in message.lower() or "không" in message.lower())


def test_unknown_rejection_reason_uses_safe_fallback():
    assert rejection_message("future_reason") == "Câu trả lời chưa được xác minh."
