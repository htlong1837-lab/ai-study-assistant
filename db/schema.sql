-- Schema SQLite dùng chung cho Trợ lý AI học tập
-- Thiết lập tính toàn vẹn dữ liệu: PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    course TEXT,
    deadline TEXT,                  -- NULL khi proposed mà chưa có hạn nộp cụ thể
    estimated_hours REAL,           -- Số giờ ước tính, NULL khi chưa ước lượng
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    confidence REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('proposed', 'confirmed', 'cancelled')),
    created_at TEXT NOT NULL,
    confirmed_at TEXT
);

CREATE TABLE IF NOT EXISTS task_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    source TEXT NOT NULL,           -- 'email:<id>' | 'doc:<doc_id>#p<n>'
    field TEXT,                     -- Tên trường được trích xuất từ nguồn này
    quote TEXT,                     -- Đoạn trích dẫn nguyên văn trong văn bản gốc
    kind TEXT NOT NULL              -- 'email' | 'document'
);

CREATE TABLE IF NOT EXISTS assignment_details (
    task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
    raw_deadline_text TEXT,
    submission_format TEXT,         -- JSON array: [".pdf", ".zip"]
    submission_platform TEXT,      -- Nền tảng: 'LMS', 'Google Drive', 'Email'...
    naming_convention TEXT,        -- Quy cách đặt tên file
    grading_criteria TEXT,         -- JSON array các tiêu chí đánh giá / rubric
    assumptions TEXT               -- JSON array các giả định khi chuẩn hoá thời gian
);

CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('deadline', 'submission', 'ambiguity', 'outdated')),
    value_a TEXT,
    source_a TEXT,
    value_b TEXT,
    source_b TEXT,
    suggestion TEXT,                -- 'a' | 'b' | NULL
    resolution TEXT,                -- 'a' | 'b' | 'manual' | NULL
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS task_update_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    field TEXT NOT NULL,            -- Trường thay đổi (ví dụ: 'deadline', 'submission_platform')
    old_value TEXT,
    new_value TEXT,
    source TEXT NOT NULL,
    quote TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extraction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    execution_time_ms REAL,
    raw_response TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (source_id, content_hash, prompt_version)
);
