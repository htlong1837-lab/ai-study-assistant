"""Lớp truy xuất và quản lý cơ sở dữ liệu SQLite dùng chung cho đồ án.

Tuân thủ nguyên tắc:
- Bật PRAGMA foreign_keys = ON cho mọi kết nối.
- Bật journal_mode = WAL khi khởi tạo.
- Mở kết nối theo yêu cầu (per-call connection), an toàn với chu kỳ re-run của Streamlit.
- Mọi timestamp lưu ISO-8601 string.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_FILE = Path(__file__).parent / "schema.sql"


def init_db(db_path: Path | str) -> None:
    """Khởi tạo cơ sở dữ liệu và các bảng nếu chưa tồn tại (idempotent)."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            conn.executescript(f.read())


class Repository:
    """Lớp Repository tương tác với SQLite database."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    # --- Task CRUD ---

    def create_task(self, task_data: dict[str, Any]) -> str:
        """Tạo task mới. `deadline` có thể là None đối với task proposed."""
        now_iso = datetime.now(timezone.utc).isoformat()
        data = {
            "id": task_data["id"],
            "title": task_data["title"],
            "course": task_data.get("course"),
            "deadline": task_data.get("deadline"),
            "estimated_hours": task_data.get("estimated_hours"),
            "priority": task_data.get("priority", "medium"),
            "confidence": float(task_data.get("confidence", 1.0)),
            "status": task_data.get("status", "proposed"),
            "created_at": task_data.get("created_at", now_iso),
            "confirmed_at": task_data.get("confirmed_at"),
        }
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO tasks (id, title, course, deadline, estimated_hours, priority, confidence, status, created_at, confirmed_at)
                VALUES (:id, :title, :course, :deadline, :estimated_hours, :priority, :confidence, :status, :created_at, :confirmed_at)
                """,
                data,
            )
        return data["id"]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Lấy thông tin task theo ID."""
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        """Liệt kê danh sách tasks, có thể lọc theo status ('proposed', 'confirmed', 'cancelled')."""
        with self._conn() as conn:
            if status:
                cur = conn.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,))
            else:
                cur = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

    def update_task_fields(self, task_id: str, **fields: Any) -> None:
        """Cập nhật các trường cụ thể của task."""
        if not fields:
            return
        keys = list(fields.keys())
        set_clause = ", ".join(f"{k} = :{k}" for k in keys)
        params = {"task_id": task_id, **fields}
        with self._conn() as conn:
            conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = :task_id", params)

    def set_task_status(self, task_id: str, status: str, confirmed_at: str | None = None) -> None:
        """Cập nhật trạng thái của task."""
        params: dict[str, Any] = {"task_id": task_id, "status": status, "confirmed_at": confirmed_at}
        with self._conn() as conn:
            conn.execute("UPDATE tasks SET status = :status, confirmed_at = :confirmed_at WHERE id = :task_id", params)

    def delete_task(self, task_id: str) -> None:
        """Xoá task (tự động xoá cascade các bản ghi con liên quan)."""
        with self._conn() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    # --- Task Sources ---

    def add_sources(self, task_id: str, sources: list[dict[str, Any]]) -> None:
        """Thêm các nguồn trích xuất cho task."""
        with self._conn() as conn:
            for s in sources:
                conn.execute(
                    """
                    INSERT INTO task_sources (task_id, source, field, quote, kind)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (task_id, s["source"], s.get("field"), s.get("quote"), s["kind"]),
                )

    def get_sources(self, task_id: str) -> list[dict[str, Any]]:
        """Lấy danh sách nguồn trích xuất của task."""
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM task_sources WHERE task_id = ?", (task_id,))
            return [dict(r) for r in cur.fetchall()]

    # --- Assignment Details ---

    def save_assignment_details(self, task_id: str, details: dict[str, Any]) -> None:
        """Lưu hoặc cập nhật chi tiết yêu cầu bài tập mở rộng."""
        def _to_json(val: Any) -> str | None:
            if val is None:
                return None
            return val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)

        data = {
            "task_id": task_id,
            "raw_deadline_text": details.get("raw_deadline_text"),
            "submission_format": _to_json(details.get("submission_format")),
            "submission_platform": details.get("submission_platform"),
            "naming_convention": details.get("naming_convention"),
            "grading_criteria": _to_json(details.get("grading_criteria")),
            "assumptions": _to_json(details.get("assumptions")),
        }
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assignment_details 
                (task_id, raw_deadline_text, submission_format, submission_platform, naming_convention, grading_criteria, assumptions)
                VALUES (:task_id, :raw_deadline_text, :submission_format, :submission_platform, :naming_convention, :grading_criteria, :assumptions)
                """,
                data,
            )

    def get_assignment_details(self, task_id: str) -> dict[str, Any] | None:
        """Lấy chi tiết yêu cầu bài tập kèm parse JSON."""
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM assignment_details WHERE task_id = ?", (task_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            for k in ["submission_format", "grading_criteria", "assumptions"]:
                if res.get(k):
                    try:
                        res[k] = json.loads(res[k])
                    except Exception:
                        pass
            return res

    # --- Conflicts ---

    def add_conflict(self, conflict_data: dict[str, Any]) -> int:
        """Thêm báo cáo mâu thuẫn vào bảng conflicts."""
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO conflicts (task_id, kind, value_a, source_a, value_b, source_b, suggestion, resolution, resolved_at)
                VALUES (:task_id, :kind, :value_a, :source_a, :value_b, :source_b, :suggestion, :resolution, :resolved_at)
                """,
                {
                    "task_id": conflict_data["task_id"],
                    "kind": conflict_data["kind"],
                    "value_a": conflict_data.get("value_a"),
                    "source_a": conflict_data.get("source_a"),
                    "value_b": conflict_data.get("value_b"),
                    "source_b": conflict_data.get("source_b"),
                    "suggestion": conflict_data.get("suggestion"),
                    "resolution": conflict_data.get("resolution"),
                    "resolved_at": conflict_data.get("resolved_at"),
                },
            )
            return int(cur.lastrowid)

    def list_conflicts(self, task_id: str | None = None) -> list[dict[str, Any]]:
        """Lấy danh sách các mâu thuẫn (có thể lọc theo task_id)."""
        with self._conn() as conn:
            if task_id:
                cur = conn.execute("SELECT * FROM conflicts WHERE task_id = ?", (task_id,))
            else:
                cur = conn.execute("SELECT * FROM conflicts")
            return [dict(r) for r in cur.fetchall()]

    def resolve_conflict(self, conflict_id: int, resolution: str, resolved_at: str | None = None) -> None:
        """Đánh dấu đã giải quyết mâu thuẫn."""
        now_iso = resolved_at or datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE conflicts SET resolution = ?, resolved_at = ? WHERE id = ?",
                (resolution, now_iso, conflict_id),
            )

    # --- Task Update Proposals ---

    def add_update_proposal(self, proposal_data: dict[str, Any]) -> int:
        """Thêm đề xuất dời hạn / thay đổi yêu cầu cho bài tập đã tồn tại."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO task_update_proposals (task_id, field, old_value, new_value, source, quote, status, created_at)
                VALUES (:task_id, :field, :old_value, :new_value, :source, :quote, :status, :created_at)
                """,
                {
                    "task_id": proposal_data["task_id"],
                    "field": proposal_data["field"],
                    "old_value": proposal_data.get("old_value"),
                    "new_value": proposal_data.get("new_value"),
                    "source": proposal_data["source"],
                    "quote": proposal_data.get("quote"),
                    "status": proposal_data.get("status", "pending"),
                    "created_at": proposal_data.get("created_at", now_iso),
                },
            )
            return int(cur.lastrowid)

    def list_pending_proposals(self, task_id: str | None = None) -> list[dict[str, Any]]:
        """Lấy các đề xuất cập nhật đang chờ duyệt (status = 'pending')."""
        with self._conn() as conn:
            if task_id:
                cur = conn.execute("SELECT * FROM task_update_proposals WHERE task_id = ? AND status = 'pending'", (task_id,))
            else:
                cur = conn.execute("SELECT * FROM task_update_proposals WHERE status = 'pending'")
            return [dict(r) for r in cur.fetchall()]

    def set_update_proposal_status(self, proposal_id: int, status: str) -> None:
        """Cập nhật trạng thái đề xuất cập nhật ('accepted' hoặc 'rejected')."""
        with self._conn() as conn:
            conn.execute("UPDATE task_update_proposals SET status = ? WHERE id = ?", (status, proposal_id))

    # --- Extraction Logs & Cache ---

    def log_extraction(self, log_data: dict[str, Any]) -> int:
        """Lưu nhật ký gọi trích xuất LLM."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO extraction_logs 
                (source_type, source_id, content_hash, prompt_version, model_name, prompt_tokens, completion_tokens, execution_time_ms, raw_response, created_at)
                VALUES (:source_type, :source_id, :content_hash, :prompt_version, :model_name, :prompt_tokens, :completion_tokens, :execution_time_ms, :raw_response, :created_at)
                """,
                {
                    "source_type": log_data["source_type"],
                    "source_id": log_data["source_id"],
                    "content_hash": log_data["content_hash"],
                    "prompt_version": log_data["prompt_version"],
                    "model_name": log_data["model_name"],
                    "prompt_tokens": log_data.get("prompt_tokens", 0),
                    "completion_tokens": log_data.get("completion_tokens", 0),
                    "execution_time_ms": log_data.get("execution_time_ms", 0.0),
                    "raw_response": log_data.get("raw_response"),
                    "created_at": log_data.get("created_at", now_iso),
                },
            )
            return int(cur.lastrowid)

    def get_cached_extraction(self, source_id: str, content_hash: str, prompt_version: str) -> dict[str, Any] | None:
        """Tìm bản ghi trích xuất đã lưu đệm theo source_id, content_hash và prompt_version."""
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT * FROM extraction_logs 
                WHERE source_id = ? AND content_hash = ? AND prompt_version = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (source_id, content_hash, prompt_version),
            )
            row = cur.fetchone()
            return dict(row) if row else None
