"""Unit tests for bugtest.deep.builtin_tools.safe_edit_file.

These exercise each content mode + each error path the LLM might hit, so the
tool's contract stays stable as we iterate on UX. Each test builds its own
temp workspace; nothing here touches the real evaluation/ tree.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from bugtest.deep.builtin_tools import safe_edit_file


BASELINE = (
    "import source\n\n\n"
    "def test_source_module_imports():\n"
    "    assert source is not None\n"
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Build a workspace with a buggy source.py + baseline test file."""
    (tmp_path / "source.py").write_text(
        "def add(a, b):\n"
        "    return a - b  # buggy: should be a + b\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_benchmark.py").write_text(BASELINE, encoding="utf-8")
    return tmp_path


def _call(ws: Path, **kwargs) -> dict | str:
    """Invoke safe_edit_file and return the parsed JSON body when possible."""
    raw = safe_edit_file(
        file_path=kwargs.pop("file_path", "tests/test_benchmark.py"),
        workspace=str(ws),
        **kwargs,
    )
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def test_append_path_adds_after_baseline(workspace: Path):
    new_test = "\n\ndef test_add_correct():\n    assert source.add(2, 3) == 5\n"
    res = _call(workspace, append=new_test, allow_bug_revealing=True)
    assert isinstance(res, dict)
    assert res["status"] == "success"
    content = (workspace / "tests" / "test_benchmark.py").read_text(encoding="utf-8")
    assert "def test_source_module_imports" in content   # baseline preserved
    assert "def test_add_correct" in content             # appended


def test_new_content_full_rewrite(workspace: Path):
    body = (
        "import source\n\n"
        "def test_replaced():\n"
        "    assert source.add(2, 3) == 5\n"
    )
    res = _call(workspace, new_content=body, allow_bug_revealing=True)
    assert isinstance(res, dict)
    assert res["status"] == "success"
    content = (workspace / "tests" / "test_benchmark.py").read_text(encoding="utf-8")
    assert "test_source_module_imports" not in content   # baseline gone
    assert "def test_replaced" in content


def test_old_string_exact_match_succeeds(workspace: Path):
    old = "    assert source is not None\n"
    new = (
        "    assert source is not None\n\n\n"
        "def test_extra():\n"
        "    assert source.add(2, 3) == 5\n"
    )
    res = _call(workspace, old_string=old, new_string=new, allow_bug_revealing=True)
    assert isinstance(res, dict)
    assert res["status"] == "success"
    content = (workspace / "tests" / "test_benchmark.py").read_text(encoding="utf-8")
    assert "def test_extra" in content


def test_old_string_not_found_returns_diagnostic_tail(workspace: Path):
    res = _call(workspace, old_string="not present in file", new_string="x")
    assert isinstance(res, str)
    assert "old_string not found" in res
    assert "File ends with:" in res
    # The diagnostic should expose the actual file tail
    assert "assert source is not None" in res


def test_reasoning_fields_optional_defaults_apply(workspace: Path):
    # No hypothesis / why_this_action / expected_outcome — must NOT bounce.
    res = _call(
        workspace,
        append="\n\ndef test_noop():\n    assert True\n",
        allow_bug_revealing=True,
    )
    assert isinstance(res, dict)
    assert res["status"] == "success"


def test_path_outside_tests_rejected(workspace: Path):
    res = _call(workspace, file_path="source.py", new_content="x = 1\n")
    assert isinstance(res, str)
    assert "tests/" in res  # mentions the constraint


def test_syntax_error_reverts_and_returns_stderr_snippet(workspace: Path):
    # Deliberately broken Python (unterminated def)
    res = _call(
        workspace,
        new_content="def broken(:\n    pass\n",
        allow_bug_revealing=True,
    )
    assert isinstance(res, dict)
    assert res["status"] == "failed"
    assert res["reverted"] is True
    assert res.get("stderr_snippet")  # non-empty diagnostic
    # File should be back to the baseline content
    restored = (workspace / "tests" / "test_benchmark.py").read_text(encoding="utf-8")
    assert restored.strip() == BASELINE.strip()


def test_two_modes_at_once_rejected(workspace: Path):
    res = _call(
        workspace,
        append="x = 1\n",
        new_content="y = 2\n",
    )
    assert isinstance(res, str)
    assert "exactly one content mode" in res
