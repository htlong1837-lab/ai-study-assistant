"""Bộ trích xuất theo luật (chạy khi chưa có khóa LLM) và gộp đề bài vào nhiệm vụ của email."""
from datetime import datetime
from pathlib import Path

from core.contracts import ClassifiedEmail, EmailLabel, Page, ParsedDocument, SafetyStatus
from db.repository import Repository
from modules.extraction import workflow
from modules.extraction.prompts import build_extraction_prompt
from modules.extraction.rule_extractor import NoCacheRepository, RuleBasedLLM, _source

SENT = datetime(2026, 11, 23, 8, 0)


def _email(eid, subject, body):
    return ClassifiedEmail(id=eid, sender="gv@uni.edu.vn", subject=subject, body=body,
                           received_at=SENT, label=EmailLabel.ASSIGNMENT, safety=SafetyStatus.SAFE)


def _doc(text):
    return ParsedDocument(doc_id="doc-1", filename="de_bai.pdf", pages=[Page(number=1, text=text)])


ASSIGN = _email("e-1", "[AI] Bài tập lớn số 2 - thuật toán A*",
                "Chào các em,\nCác em nộp trước 23h59 ngày 05/12/2026 trên LMS.")
DOC = _doc("ĐỀ BÀI TẬP LỚN SỐ 2\nNộp: báo cáo PDF và mã nguồn nén .zip, đặt tên MSSV_HoTen_BTL2.zip.\n"
           "Hạn nộp: 23h59 ngày 05/12/2026 trên LMS của trường.\n"
           "Tiêu chí chấm: đúng thuật toán (4 điểm), thí nghiệm (4 điểm), báo cáo (2 điểm).")


def test_reads_data_block_not_the_security_note():
    src = "Người gửi: a\nTiêu đề: X\nNội dung:\nBody"
    assert _source(build_extraction_prompt(src)) == src


def test_email_extraction_is_grounded(tmp_path):
    repo = Repository(tmp_path / "b.db")
    (tid,) = workflow.process_email(ASSIGN, RuleBasedLLM(), repo)
    t = repo.get_task(tid)
    assert t["title"] == "Bài tập lớn số 2 - thuật toán A*"
    assert t["course"] == "AI"
    assert t["deadline"].startswith("2026-12-05T23:59")
    assert t["status"] == "proposed"  # AI chỉ đề xuất
    full = f"Tiêu đề: {ASSIGN.subject}\n{ASSIGN.body}"
    assert all(s["quote"] in full for s in repo.get_sources(tid))  # câu trích có thật


def test_non_assignment_email_gives_nothing(tmp_path):
    e = _email("e-2", "Đổi phòng học", "Lớp chuyển sang phòng B203.")
    assert workflow.process_email(e, RuleBasedLLM(), Repository(tmp_path / "b.db")) == []


def test_document_merges_into_email_task(tmp_path):
    repo = Repository(tmp_path / "b.db")
    llm = RuleBasedLLM()
    (tid,) = workflow.process_email(ASSIGN, llm, repo)
    assert workflow.process_document(DOC, llm, repo, linked_email=ASSIGN) == [tid]
    assert len(repo.list_tasks()) == 1  # không tạo bản trùng
    d = repo.get_assignment_details(tid)
    assert d["submission_format"] == [".pdf", ".zip"]
    assert d["naming_convention"] == "MSSV_HoTen_BTL2.zip"
    assert len(d["grading_criteria"]) == 3
    assert repo.list_conflicts() == []  # cùng hạn, "LMS" và "LMS của trường" là một


def test_document_with_other_deadline_raises_conflict(tmp_path):
    repo = Repository(tmp_path / "b.db")
    llm = RuleBasedLLM()
    (tid,) = workflow.process_email(ASSIGN, llm, repo)
    other = _doc("ĐỀ BÀI TẬP LỚN SỐ 2\nHạn nộp: 23h59 ngày 12/12/2026.")
    workflow.process_document(other, llm, repo, linked_email=ASSIGN)
    (c,) = repo.list_conflicts()
    assert c["task_id"] == tid and c["kind"] == "deadline"


def test_extension_email_proposes_update(tmp_path):
    repo = Repository(tmp_path / "b.db")
    llm = RuleBasedLLM()
    (tid,) = workflow.process_email(ASSIGN, llm, repo)
    ext = _email("e-3", "[AI] Dời hạn bài tập lớn số 2",
                 "Hạn nộp bài tập lớn số 2 được dời sang 23h59 ngày 12/12/2026.")
    workflow.process_email(ext, llm, repo)
    (p,) = repo.list_pending_proposals()
    assert p["task_id"] == tid and p["new_value"].startswith("2026-12-12T23:59")


def test_no_cache_wrapper_keeps_cache_clean(tmp_path):
    repo = Repository(tmp_path / "b.db")
    workflow.process_email(ASSIGN, RuleBasedLLM(), NoCacheRepository(repo))
    assert repo.list_tasks()  # vẫn ghi nhiệm vụ
    with repo._conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM extraction_logs").fetchone()[0] == 0


def test_demo_emails_exist():
    assert len(list((Path(__file__).resolve().parents[2] / "data" / "demo").glob("*.eml"))) == 3
