from __future__ import annotations

from .models import RejectionReason

_REJECTION_MESSAGES = {
    RejectionReason.NO_CITATION: "Câu trả lời chưa có trích dẫn nguồn.",
    RejectionReason.CITATION_NOT_FOUND: "Không tìm thấy đoạn trích trong trang được dẫn.",
    RejectionReason.CITATION_OUTSIDE_CONTEXT: "Trích dẫn không thuộc phần tài liệu đã gửi để kiểm tra.",
    RejectionReason.WEAK_SUPPORT: "Đoạn trích chưa đủ hỗ trợ cho nội dung trả lời.",
    RejectionReason.EMPTY_PAGE: "Trang không có lớp văn bản đọc được; có thể đây là PDF scan.",
    RejectionReason.LLM_UNAVAILABLE: "Dịch vụ AI chưa trả lời được yêu cầu này.",
    RejectionReason.INVALID_INPUT: "Yêu cầu hoặc dữ liệu trả về không hợp lệ.",
}


def rejection_message(reason: RejectionReason | str | None) -> str:
    if reason is None:
        return "Câu trả lời chưa được xác minh."
    try:
        normalized = RejectionReason(reason)
    except (TypeError, ValueError):
        return "Câu trả lời chưa được xác minh."
    return _REJECTION_MESSAGES[normalized]
