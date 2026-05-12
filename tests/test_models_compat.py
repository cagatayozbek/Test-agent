"""Verify v2.0 logging fields default safely and v1.x JSONs still load.

The point of the round-trip checks is to keep `results/` files (created
before this refactor) deserializable so the migration script can tag them
without rewriting their structure.
"""

from __future__ import annotations

import json

from bugtest.models import (
    AttemptRecord,
    RunRecord,
    ValidationResult,
)


def _v1_validation() -> dict:
    return {
        "buggy_passed": False,
        "buggy_output": "FAILED",
        "fixed_passed": True,
        "fixed_output": "ok",
        "is_bug_revealing": True,
    }


def _v1_attempt() -> dict:
    return {
        "attempt_number": 1,
        "test_code": "def test_x():\n    assert True\n",
        "validation": _v1_validation(),
        "timestamp": "2026-05-01T12:00:00Z",
    }


def _v1_run() -> dict:
    return {
        "task_id": "quixbugs_bitcount",
        "mode": "deep",
        "run_number": 1,
        "success": True,
        "attempts": [_v1_attempt()],
        "total_attempts": 1,
        "attempts_to_success": 1,
        "prompt_tokens_total": 1234,
        "completion_tokens_total": 567,
        "duration_seconds": 12.3,
        "timestamp": "2026-05-01T12:00:00Z",
    }


def test_v1_attempt_record_still_loads():
    rec = AttemptRecord.model_validate(_v1_attempt())
    assert rec.tool_call_count == 0
    assert rec.tool_failure_mode_count == {}
    assert rec.reasoning_filled is False


def test_v1_run_record_still_loads():
    rec = RunRecord.model_validate(_v1_run())
    assert rec.prompt_version == ""
    assert rec.prompt_template_hash == ""
    assert rec.capabilities_used == {}
    assert rec.tool_choice_mode == ""


def test_v2_round_trip():
    """A fully-instrumented v2.0 record survives JSON round-trip with all
    new fields intact — this is what production runs will emit."""
    payload = _v1_run()
    payload["prompt_version"] = "v2.0"
    payload["prompt_template_hash"] = "abc123def456"
    payload["capabilities_used"] = {
        "provider": "claude_cli",
        "supports_parallel_tools": True,
        "tool_names": {"read": "Read", "edit": "Edit", "run": "Bash"},
    }
    payload["tool_choice_mode"] = "auto"
    payload["attempts"][0]["tool_call_count"] = 3
    payload["attempts"][0]["tool_failure_mode_count"] = {"revert_syntax": 1}
    payload["attempts"][0]["reasoning_filled"] = True

    rec = RunRecord.model_validate(payload)
    serialized = json.loads(rec.model_dump_json())
    assert serialized["prompt_version"] == "v2.0"
    assert serialized["prompt_template_hash"] == "abc123def456"
    assert serialized["capabilities_used"]["supports_parallel_tools"] is True
    assert serialized["capabilities_used"]["provider"] == "claude_cli"
    assert serialized["capabilities_used"]["tool_names"]["read"] == "Read"
    assert serialized["tool_choice_mode"] == "auto"
    assert serialized["attempts"][0]["tool_call_count"] == 3
    assert serialized["attempts"][0]["tool_failure_mode_count"] == {"revert_syntax": 1}
    assert serialized["attempts"][0]["reasoning_filled"] is True


def test_tool_choice_mode_rejects_unknown_value():
    """Literal type guards against typos in future call sites."""
    payload = _v1_run()
    payload["tool_choice_mode"] = "definitely-not-a-real-mode"
    try:
        RunRecord.model_validate(payload)
    except Exception:
        return
    raise AssertionError("Expected validation error for bogus tool_choice_mode")