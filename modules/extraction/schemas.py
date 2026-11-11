"""Pydantic schemas cho LLM trích xuất thông tin bài tập có cấu trúc.

Nguyên tắc bất biến: Mọi trường đều nullable, null là giá trị hợp lệ khi văn bản không đề cập.
"""
from __future__ import annotations

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

from core.contracts import Priority

T = TypeVar("T")


class Evidence(BaseModel):
    """Bằng chứng trích xuất nguyên văn từ văn bản nguồn."""
    quote: str = Field(description="Trích nguyên văn cụm từ trong văn bản, không diễn đạt lại")
    location: str = Field(description="'email' hoặc 'p<số trang>' ví dụ 'p1', 'p2'")


class ExField(BaseModel, Generic[T]):
    """Trường trích xuất kèm bằng chứng."""
    value: T | None = None
    evidence: Evidence | None = None


class RawDeadline(BaseModel):
    """Cụm thời gian hạn nộp nguyên văn trước khi chuẩn hoá."""
    label: str | None = Field(default=None, description="Nhãn giai đoạn (ví dụ: 'nộp báo cáo', 'demo').")
    raw_text: str = Field(description="Cụm thời gian nguyên văn trong tài liệu (ví dụ: '23h59 thứ 6 tuần sau').")
    evidence: Evidence


class RawAssignment(BaseModel):
    """Thông tin bài tập trích xuất thô từ LLM."""
    title: ExField[str] = Field(default_factory=lambda: ExField[str]())
    course: ExField[str] = Field(default_factory=lambda: ExField[str]())
    deadlines: list[RawDeadline] = Field(default_factory=list)
    submission_platform: ExField[str] = Field(default_factory=lambda: ExField[str]())
    submission_format: ExField[list[str]] = Field(default_factory=lambda: ExField[list[str]]())
    naming_convention: ExField[str] = Field(default_factory=lambda: ExField[str]())
    grading_criteria: ExField[list[str]] = Field(default_factory=lambda: ExField[list[str]]())
    estimated_hours: float | None = Field(default=None, description="Số giờ ước tính do LLM gợi ý.")
    priority_suggestion: Priority | None = Field(default=None, description="Độ ưu tiên gợi ý.")
    is_extension_notice: bool = Field(default=False, description="True nếu đây là email đính chính / dời hạn nộp.")
    refers_to: str | None = Field(default=None, description="Mô tả hoặc tên bài tập cũ được nhắc tới.")


class ExtractionResult(BaseModel):
    """Kết quả trích xuất tổng thể từ một nguồn tài liệu."""
    assignments: list[RawAssignment] = Field(default_factory=list)
    not_assignment: bool = Field(default=False, description="True nếu nguồn không chứa bất kỳ bài tập nào.")
