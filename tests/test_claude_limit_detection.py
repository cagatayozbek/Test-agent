"""Verify the tightened claude limit detection doesn't false-positive on
the agent's own response text while still catching real quota errors.
"""
from __future__ import annotations

import json

from bugtest.deep.llm import _is_claude_limit_error


def _ok_wrapper(text: str) -> str:
    """Mimic a normal --output-format json success envelope."""
    return json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "api_error_status": None,
        "result": text,
    })


def _error_wrapper(text: str, api_error_status: str = "rate_limit_error") -> str:
    """Mimic the envelope claude returns when the API itself errored."""
    return json.dumps({
        "type": "result",
        "subtype": "error",
        "is_error": True,
        "api_error_status": api_error_status,
        "result": text,
    })


# ── False-positive guards ──


def test_response_containing_quota_in_docstring_is_not_limit():
    """The agent wrote test code mentioning 'quota' in a comment — that
    is the bug we just hit on haiku and the v1.x detection mis-flagged."""
    stdout = _ok_wrapper(
        "import source\n\ndef test_rate_limit_quota():\n"
        "    # ensures the rate limit / quota math works correctly\n"
        "    assert source.fish_info() == 'Fish Shell 3.1.2'\n"
    )
    assert _is_claude_limit_error(stdout, stderr="", returncode=0) is False


def test_response_containing_429_in_test_code_is_not_limit():
    stdout = _ok_wrapper(
        'def test_429_status():\n    assert source.handle_429() == "retry"\n'
    )
    assert _is_claude_limit_error(stdout, stderr="", returncode=0) is False


def test_response_with_too_many_requests_in_description_is_not_limit():
    stdout = _ok_wrapper(
        "# Bug: server returns 'too many requests' even on the first call\n"
    )
    assert _is_claude_limit_error(stdout, stderr="", returncode=0) is False


def test_plain_success_with_no_signals_is_not_limit():
    stdout = _ok_wrapper("ok")
    assert _is_claude_limit_error(stdout, stderr="", returncode=0) is False


# ── Real-limit detection ──


def test_stderr_signal_always_counts():
    """Claude CLI writes operator errors to stderr — substring match there
    is safe."""
    assert _is_claude_limit_error(
        stdout=_ok_wrapper("hello"),
        stderr="You've reached your Claude usage limit. Try again in 4 hours.",
        returncode=0,
    ) is True


def test_nonzero_returncode_plus_signal_anywhere_counts():
    assert _is_claude_limit_error(
        stdout="claude: rate limit exceeded",
        stderr="",
        returncode=1,
    ) is True


def test_json_with_is_error_true_and_signal_counts():
    stdout = _error_wrapper("Claude usage limit reached — wait for window reset.")
    assert _is_claude_limit_error(stdout, stderr="", returncode=0) is True


def test_json_with_is_error_true_but_no_limit_signal_does_not_count():
    """An API error that's NOT a quota issue (e.g. validation) shouldn't
    trigger the 60-min sleep loop."""
    stdout = _error_wrapper(
        "Invalid model id 'haiku2' — pick a real model.",
        api_error_status="validation_error",
    )
    assert _is_claude_limit_error(stdout, stderr="", returncode=0) is False


def test_malformed_json_with_no_stderr_signal_is_not_limit():
    """Output isn't JSON at all — without an explicit error channel we
    must not assume the worst."""
    assert _is_claude_limit_error(
        stdout="not json, but contains the word quota inside test_code",
        stderr="",
        returncode=0,
    ) is False
