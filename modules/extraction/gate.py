"""Cổng chặn bảo mật cho Module B (Nguyên tắc II: Chặn tại cổng).

Chỉ xử lý dữ liệu an toàn; nội dung độc hại (malicious) tuyệt đối không đi tiếp.
"""
from __future__ import annotations

import logging
from core.contracts import ClassifiedEmail, can_forward

logger = logging.getLogger(__name__)


class UnsafeSourceError(ValueError):
    """Ngoại lệ ném ra khi cố tình gửi nguồn dữ liệu không an toàn vào Module B."""


def ensure_safe(email: ClassifiedEmail, allow_suspicious: bool = False) -> None:
    """Kiểm tra tính an toàn của email thông qua hợp đồng can_forward().
    
    Nếu không an toàn, lập tức raise UnsafeSourceError và ghi log cảnh báo,
    tuyệt đối không cho phép tiếp tục luồng xử lý hoặc gọi LLM.
    """
    if not can_forward(email, allow_suspicious=allow_suspicious):
        msg = f"Cổng bảo mật chặn email '{email.id}': trạng thái an toàn là '{email.safety.value}'."
        logger.warning(msg)
        raise UnsafeSourceError(msg)
