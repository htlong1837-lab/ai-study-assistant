from __future__ import annotations

import json

import fitz
import pytest

from core.contracts import Page
from core.llm_client import LLMResponse


@pytest.fixture
def vietnamese_pages():
    return [
        Page(1, "Đây là nội dung mẫu về học tập và quản lý thời gian."),
        Page(2, "Người học nên chia nhiệm vụ lớn thành các bước nhỏ."),
    ]


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "sample-vietnamese.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Tai lieu mau de kiem thu bo doc PDF.")
    document.save(path)
    document.close()
    return path


@pytest.fixture
def fake_llm():
    class FakeLLM:
        model = "pytest-fake"

        def __init__(self):
            self.prompts = []

        def generate(
            self, prompt, *, system=None, temperature=0.0, use_cache=True, timeout=None
        ):
            self.prompts.append(prompt)
            return LLMResponse(
                json.dumps(
                    {
                        "can_answer": True,
                        "answer": "Đây là nội dung mẫu về học tập.",
                        "citations": [
                            {
                                "page_num": 1,
                                "evidence_text": "Đây là nội dung mẫu về học tập",
                            }
                        ],
                        "background_note": "",
                    },
                    ensure_ascii=False,
                )
            )

    return FakeLLM()


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests that take longer to run")
