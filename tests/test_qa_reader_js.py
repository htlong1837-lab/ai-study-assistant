import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_reader_javascript_logic():
    node = shutil.which("node")
    if node is None:
        pytest.skip(
            "Node.js is not installed; run node --test tests/js/reader_logic.test.mjs locally."
        )
    result = subprocess.run(
        [node, "--test", str(ROOT / "tests" / "js" / "reader_logic.test.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
