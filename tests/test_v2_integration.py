"""Integration-level checks that do NOT call any LLM provider.

Verifies the v2.0 wiring is consistent end-to-end: the orchestrator can
be constructed for every YAML model_id, each model receives a system
prompt rendered with its own tool-name dict, and the rendered prompt's
fairness invariants hold across providers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from bugtest.deep import builtin_tools  # noqa: F401 — registers tools
from bugtest.deep import capabilities
from bugtest.deep.orchestrator import (
    BENCHMARK_TOOLS,
    DeepTestOrchestrator,
    FULL_TOOLS,
)
from bugtest.deep.prompts import PROMPT_VERSION, render_system_prompt


REPO_ROOT = Path(__file__).resolve().parent.parent


def _yaml_model_ids() -> list[str]:
    """Return every (provider-prefixed) model_id referenced by YAML configs."""
    pattern = re.compile(r"^\s*model_id:\s*(\S+)\s*$")
    raw: set[str] = set()
    for path in REPO_ROOT.glob("*.yaml"):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = pattern.match(line)
            if m:
                raw.add(m.group(1))
    out: list[str] = []
    for r in sorted(raw):
        if r in {"sonnet", "opus", "haiku"}:
            out.append(f"claude:{r}")
        elif "/" in r:
            out.append(f"openai:{r}")
        else:
            out.append(r)
    return out


# ── Per-model rendering ──


@pytest.mark.parametrize("model_id", _yaml_model_ids())
def test_render_works_for_every_yaml_model(model_id):
    caps = capabilities.for_model(model_id)
    text, digest = render_system_prompt(caps["tool_names"], max_steps=8)
    assert len(digest) == 12
    # Every provider's prompt mentions its own edit-tool name in the workflow.
    assert caps["tool_names"]["edit"] in text
    assert "Success Criterion" in text
    assert "TEST_PASSES_ON_BUG" in text


def test_renders_are_either_identical_or_match_provider_class():
    """v2.0 fairness contract: two models with the same tool_names dict
    must produce byte-identical system prompts. Different tool_names →
    different prompts (we already verified that elsewhere)."""
    ids = _yaml_model_ids()
    by_tool_names: dict[tuple, str] = {}
    for mid in ids:
        caps = capabilities.for_model(mid)
        key = tuple(sorted(caps["tool_names"].items()))
        text, _ = render_system_prompt(caps["tool_names"], max_steps=8)
        if key in by_tool_names:
            assert by_tool_names[key] == text, (
                f"Same tool_names but different rendered prompt for {mid}"
            )
        else:
            by_tool_names[key] = text


# ── Orchestrator construction ──


@pytest.mark.parametrize("model_id", _yaml_model_ids())
def test_orchestrator_can_be_built_for_every_model(tmp_path: Path, model_id):
    """The orchestrator construction path must not raise for any YAML model.
    We don't call .run() — that would touch the real provider — but
    construction exercises capability resolution and LLMClient wiring."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    orch = DeepTestOrchestrator(
        workspace=str(workspace),
        model_name=model_id,
        max_steps=4,
        timeout_seconds=10,
    )
    assert orch.llm.capabilities is not None
    # Provider tag derived by LLMClient must match capability provider tag.
    assert orch.llm.capabilities["provider"] == orch.llm.provider


def test_tool_registry_choice_by_problem_string(tmp_path: Path):
    """`tasks_v2` / `test_benchmark` in the problem → BENCHMARK_TOOLS;
    otherwise FULL_TOOLS. CLI provider → None (uses native tools)."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    orch = DeepTestOrchestrator(
        workspace=str(workspace),
        model_name="openai:deepseek-ai/DeepSeek-V3",
        max_steps=4,
        timeout_seconds=10,
    )
    assert orch._select_tool_registry("Add tests for tasks_v2 task X") == BENCHMARK_TOOLS
    assert orch._select_tool_registry("Refactor module Y") == FULL_TOOLS

    orch_cli = DeepTestOrchestrator(
        workspace=str(workspace),
        model_name="claude:sonnet",
        max_steps=4,
        timeout_seconds=10,
    )
    assert orch_cli._select_tool_registry("Add tests for tasks_v2") is None


# ── Failure-mode taxonomy parity ──


def test_failure_mode_names_match_across_modules():
    """The v2.0 design depends on the agent prompt, the critic prompt, and
    `_validation_summary` using IDENTICAL failure-mode names so feedback
    loops back into the next attempt unambiguously."""
    from bugtest.agents.deep_agent import _validation_summary
    from bugtest.pipeline import _build_retry_context
    from bugtest.deep.prompts import CRITIC_PROMPT, FAILURE_MODES

    # Both modules must reference the SAME names in their text.
    assert "TEST_PASSES_ON_BUG" in CRITIC_PROMPT
    assert "OVERFIT_TO_BUG" in CRITIC_PROMPT
    assert "TEST_PASSES_ON_BUG" in FAILURE_MODES
    assert "OVERFIT_TO_BUG" in FAILURE_MODES

    # _validation_summary emits these tags too — synthesize a minimal
    # ValidationResult-shaped object to confirm.
    class _V:
        def __init__(self, bp, fp):
            self.buggy_passed = bp
            self.fixed_passed = fp
            self.buggy_output = ""
            self.fixed_output = ""

    assert "TEST_PASSES_ON_BUG" in _validation_summary(_V(True, True), "")
    assert "OVERFIT_TO_BUG" in _validation_summary(_V(False, False), "")


def test_pipeline_stamps_prompt_version_on_non_deep_runs():
    """The non-deep run path must tag prompt_version='v2.0' even though it
    doesn't go through the deep renderer (it uses the TestWriter prompt
    re-exported from prompts.py)."""
    from bugtest.pipeline import PROMPT_VERSION as PV_PIPELINE
    assert PV_PIPELINE == PROMPT_VERSION == "v2.0"
