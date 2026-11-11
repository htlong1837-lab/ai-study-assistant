"""Tiện ích tổng hợp mức độ an toàn (plan_module_d.md § 6.1).

Quy tắc: SAFE < SUSPICIOUS < MALICIOUS.
``aggregate_safety`` luôn trả về mức nghiêm trọng nhất trong tập tín hiệu đầu vào.
Hàm này KHÔNG bao giờ làm giảm mức an toàn — đây là tính chất đơn điệu được test.
"""
from __future__ import annotations

from core.contracts import ClassifiedEmail, SafetyStatus

# Ánh xạ enum → số để so sánh thứ tự nghiêm trọng
_SEVERITY: dict[SafetyStatus, int] = {
    SafetyStatus.SAFE: 0,
    SafetyStatus.SUSPICIOUS: 1,
    SafetyStatus.MALICIOUS: 2,
}

_FROM_SEVERITY: dict[int, SafetyStatus] = {v: k for k, v in _SEVERITY.items()}


def max_status(*statuses: SafetyStatus) -> SafetyStatus:
    """Trả về trạng thái an toàn nghiêm trọng nhất trong danh sách.

    Nếu không có tín hiệu nào → SAFE (mặc định an toàn khi không có thông tin).

    >>> max_status(SafetyStatus.SAFE, SafetyStatus.SUSPICIOUS)
    <SafetyStatus.SUSPICIOUS: 'suspicious'>
    >>> max_status(SafetyStatus.SUSPICIOUS, SafetyStatus.MALICIOUS, SafetyStatus.SAFE)
    <SafetyStatus.MALICIOUS: 'malicious'>
    >>> max_status()
    <SafetyStatus.SAFE: 'safe'>
    """
    if not statuses:
        return SafetyStatus.SAFE
    return _FROM_SEVERITY[max(_SEVERITY[s] for s in statuses)]


def aggregate_safety(
    *statuses: SafetyStatus,
    label_is_phishing: bool = False,
) -> SafetyStatus:
    """Tổng hợp toàn bộ tín hiệu an toàn thành một trạng thái cuối.

    Ngoài max các status, áp dụng quy tắc nhãn (plan § 6.4):
    - Nếu nhãn là PHISHING → kết quả tối thiểu là SUSPICIOUS.

    LLM không bao giờ được hạ mức an toàn (ràng buộc C7 — caller chịu trách nhiệm
    chỉ truyền status từ scanner, không truyền status do LLM đề xuất).

    >>> aggregate_safety(SafetyStatus.SAFE, label_is_phishing=True)
    <SafetyStatus.SUSPICIOUS: 'suspicious'>
    >>> aggregate_safety(SafetyStatus.MALICIOUS, label_is_phishing=True)
    <SafetyStatus.MALICIOUS: 'malicious'>
    """
    base = max_status(*statuses)
    if label_is_phishing:
        # PHISHING nâng tối thiểu lên SUSPICIOUS; không hạ MALICIOUS
        base = _FROM_SEVERITY[max(_SEVERITY[base], _SEVERITY[SafetyStatus.SUSPICIOUS])]
    return base


def can_forward_email(email: ClassifiedEmail, user_approved: bool = False) -> bool:
    """Cổng chặn nội bộ Module D — bọc can_forward() từ core.contracts.

    ``user_approved=True`` cho phép chuyển email SUSPICIOUS sau khi người dùng
    xác nhận (giải quyết OQ1 trong plan: không sửa contract, dùng tham số nội bộ).
    Email MALICIOUS KHÔNG BAO GIỜ được chuyển bất kể user_approved.

    Lý do có hàm riêng thay vì gọi thẳng contracts.can_forward():
    - Thêm tham số user_approved mà không sửa contract.
    - Điểm duy nhất cần test quy tắc II cho Module D.
    """
    from core.contracts import can_forward as _contract_can_forward
    return _contract_can_forward(email, allow_suspicious=user_approved)
