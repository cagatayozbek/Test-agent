"""Verify that every model_id used by smoke and benchmark configs has a
capability row and that resolution falls back safely for unknown ids."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from bugtest.deep import capabilities


REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_KEYS = {
    "provider",
    "supports_parallel_tools",
    "supports_tool_choice_auto",
    "supports_structured_tools",
    "supports_system_role",
    "tool_names",
}
TOOL_NAME_SLOTS = {"read", "edit", "run"}


def _resolve_provider_prefix(raw_model_id: str) -> str:
    """Map a bare YAML model_id to its provider-prefixed form, mirroring
    the routing rules in bugtest/agents/deep_agent.py:_resolve_deep_model_name.
    """
    if raw_model_id in {"sonnet", "opus", "haiku"}:
        return f"claude:{raw_model_id}"
    # Anything containing "/" is a Hugging-Face-style org/model id and
    # currently routes through the OpenAI-compatible Together endpoint
    # in our smoke/benchmark configs.
    if "/" in raw_model_id:
        return f"openai:{raw_model_id}"
    return raw_model_id


def _yaml_model_ids() -> list[str]:
    """Scan every YAML config for `model_id:` lines and return resolved ids."""
    pattern = re.compile(r"^\s*model_id:\s*(\S+)\s*$")
    raw: set[str] = set()
    for path in REPO_ROOT.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = pattern.match(line)
            if m:
                raw.add(m.group(1))
    return sorted(_resolve_provider_prefix(r) for r in raw)


def test_for_model_returns_complete_dict_for_default():
    caps = capabilities.for_model("openai:unknown/model-id-not-listed")
    assert CAP_KEYS <= caps.keys()
    assert TOOL_NAME_SLOTS <= caps["tool_names"].keys()


@pytest.mark.parametrize("model_id", _yaml_model_ids())
def test_every_yaml_model_has_capability_row(model_id):
    caps = capabilities.for_model(model_id)
    assert CAP_KEYS <= caps.keys(), f"{model_id}: missing keys"
    assert TOOL_NAME_SLOTS <= caps["tool_names"].keys()
    # provider must be one of the four we actually support
    assert caps["provider"] in {"claude_cli", "anthropic", "openai", "nvidia"}


def test_claude_cli_uses_native_tool_names():
    caps = capabilities.for_model("claude:sonnet")
    assert caps["provider"] == "claude_cli"
    assert caps["tool_names"]["read"] == "Read"
    assert caps["tool_names"]["edit"] == "Edit"
    assert caps["supports_structured_tools"] is False


def test_orchestrator_models_use_orchestrator_tool_names():
    for model_id in (
        "openai:deepseek-ai/DeepSeek-V3",
        "openai:Qwen/Qwen3-Coder-Next-FP8",
        "openai:meta-llama/Llama-3.3-70B-Instruct-Turbo",
    ):
        caps = capabilities.for_model(model_id)
        assert caps["tool_names"]["edit"] == "safe_edit_file"
        assert caps["tool_names"]["run"] == "run_tests"


def test_gpt_oss_120b_is_non_parallel_non_structured():
    """Harmony recovery path requires single-call turns."""
    caps = capabilities.for_model("openai:openai/gpt-oss-120b")
    assert caps["supports_parallel_tools"] is False
    assert caps["supports_structured_tools"] is False


def test_resolution_is_case_insensitive():
    caps_lower = capabilities.for_model("openai:deepseek-ai/deepseek-v3")
    caps_mixed = capabilities.for_model("openai:DeepSeek-AI/DeepSeek-V3")
    assert caps_lower == caps_mixed


def test_unknown_id_emits_warning_once(capsys):
    """Ids without any known provider prefix fall to the OpenAI default and
    must emit exactly one stderr warning per distinct id (not per call)."""
    capabilities._warned.clear()
    capabilities.for_model("no-such-provider:weird-model")
    capabilities.for_model("no-such-provider:weird-model")
    err = capsys.readouterr().err
    assert err.count("no capability row") == 1


def test_known_provider_prefix_does_not_warn(capsys):
    """`openai:foo/bar` without an exact row is a valid OpenAI-compatible
    model — fall back silently to OpenAI defaults."""
    capabilities._warned.clear()
    capabilities.for_model("openai:some/uncatalogued-model")
    assert "no capability row" not in capsys.readouterr().err
