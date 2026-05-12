"""Unit tests for bugtest.deep.builtin_tools.safe_edit_file (v2.0 schema).

Exercises both modes (`append`, `replace`), every error path the LLM might
hit, and the failure-mode tagging the agent loop reads to populate
AttemptRecord. Each test builds its own temp workspace; nothing here
touches the real evaluation/ tree.
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


@pytest.fixture
def ctx() -> dict:
    """Fresh per-test context dict so failure-mode counts don't leak."""
    return {}


def _call(ws: Path, ctx: dict, **kwargs) -> dict | str:
    """Invoke safe_edit_file with a context and parse JSON when possible."""
    raw = safe_edit_file(
        file_path=kwargs.pop("file_path", "tests/test_benchmark.py"),
        workspace=str(ws),
        context=ctx,
        **kwargs,
    )
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def test_append_path_adds_after_baseline(workspace: Path, ctx: dict):
    new_test = "\n\ndef test_add_correct():\n    assert source.add(2, 3) == 5\n"
    res = _call(workspace, ctx, append=new_test, allow_bug_revealing=True)
    assert isinstance(res, dict)
    assert res["status"] == "success"
    content = (workspace / "tests" / "test_benchmark.py").read_text(encoding="utf-8")
    assert "def test_source_module_imports" in content
    assert "def test_add_correct" in content


def test_append_is_default_mode(workspace: Path, ctx: dict):
    """mode='append' is the default — callers may omit `mode` entirely."""
    res = _call(workspace, ctx, append="\n\ndef test_default():\n    assert True\n")
    assert isinstance(res, dict)
    assert res["status"] == "success"


def test_replace_mode_substitutes_old_string(workspace: Path, ctx: dict):
    old = "    assert source is not None\n"
    new = (
        "    assert source is not None\n\n\n"
        "def test_extra():\n"
        "    assert source.add(2, 3) == 5\n"
    )
    res = _call(
        workspace, ctx,
        mode="replace", old_string=old, new_string=new,
        allow_bug_revealing=True,
    )
    assert isinstance(res, dict)
    assert res["status"] == "success"
    content = (workspace / "tests" / "test_benchmark.py").read_text(encoding="utf-8")
    assert "def test_extra" in content


def test_replace_with_missing_old_string_returns_diagnostic(workspace: Path, ctx: dict):
    res = _call(
        workspace, ctx,
        mode="replace", old_string="not present in file", new_string="x",
    )
    assert isinstance(res, str)
    assert "old_string not found" in res
    assert "File ends with:" in res
    assert "assert source is not None" in res


def test_invalid_mode_string_tags_mode_conflict(workspace: Path, ctx: dict):
    res = _call(workspace, ctx, mode="rewrite", append="x = 1\n")
    assert isinstance(res, str)
    assert "must be 'append' or 'replace'" in res
    assert ctx["tool_failure_mode_count"]["mode_conflict"] == 1


def test_append_with_old_string_tags_mode_conflict(workspace: Path, ctx: dict):
    res = _call(
        workspace, ctx,
        mode="append", append="x = 1\n",
        old_string="anything", new_string="else",
    )
    assert isinstance(res, str)
    assert "mode='append' must not pass" in res
    assert ctx["tool_failure_mode_count"]["mode_conflict"] == 1


def test_replace_without_new_string_tags_mode_conflict(workspace: Path, ctx: dict):
    res = _call(workspace, ctx, mode="replace", old_string="foo")
    assert isinstance(res, str)
    assert "requires both `old_string` and `new_string`" in res
    assert ctx["tool_failure_mode_count"]["mode_conflict"] == 1


def test_append_without_append_param_tags_mode_conflict(workspace: Path, ctx: dict):
    res = _call(workspace, ctx, mode="append")
    assert isinstance(res, str)
    assert "requires the `append` parameter" in res
    assert ctx["tool_failure_mode_count"]["mode_conflict"] == 1


def test_path_outside_tests_tags_path_failure(workspace: Path, ctx: dict):
    res = _call(workspace, ctx, file_path="source.py", append="x = 1\n")
    assert isinstance(res, str)
    assert "tests/" in res
    assert ctx["tool_failure_mode_count"]["path_outside_tests"] == 1


def test_syntax_error_reverts_and_tags_revert_syntax(workspace: Path, ctx: dict):
    # Append valid-looking but malformed Python (unterminated def signature)
    res = _call(
        workspace, ctx,
        mode="replace",
        old_string=BASELINE,
        new_string="def broken(:\n    pass\n",
        allow_bug_revealing=True,
    )
    assert isinstance(res, dict)
    assert res["status"] == "failed"
    assert res["reverted"] is True
    assert res["failure_mode"] == "revert_syntax"
    assert ctx["tool_failure_mode_count"]["revert_syntax"] == 1
    restored = (workspace / "tests" / "test_benchmark.py").read_text(encoding="utf-8")
    assert restored.strip() == BASELINE.strip()


def test_reasoning_filled_true_when_any_field_set(workspace: Path, ctx: dict):
    _call(
        workspace, ctx,
        append="\n\ndef test_x():\n    assert True\n",
        hypothesis="add a smoke test",
    )
    assert ctx["last_reasoning_filled"] is True


def test_reasoning_filled_false_when_all_fields_empty(workspace: Path, ctx: dict):
    _call(
        workspace, ctx,
        append="\n\ndef test_x():\n    assert True\n",
    )
    assert ctx["last_reasoning_filled"] is False


def test_no_context_does_not_crash(workspace: Path):
    """Tool must remain callable when invoked outside an agent run."""
    raw = safe_edit_file(
        file_path="tests/test_benchmark.py",
        append="\n\ndef test_no_ctx():\n    assert True\n",
        workspace=str(workspace),
    )
    parsed = json.loads(raw)
    assert parsed["status"] == "success"
