"""Lock the model-agnostic prompt renderer's structure and hash determinism."""

from __future__ import annotations

from bugtest.deep.prompts import (
    ANALYZER_PROMPT,
    CRITIC_PROMPT,
    FAILURE_MODES,
    PROMPT_VERSION,
    TEST_WRITER_SYSTEM_PROMPT,
    render_system_prompt,
)


ORCHESTRATOR_TOOLS = {"read": "read_file", "edit": "safe_edit_file", "run": "run_tests"}
CLI_TOOLS = {"read": "Read", "edit": "Edit", "run": "Bash (`python -m pytest`)"}


def test_prompt_version_is_v2():
    assert PROMPT_VERSION == "v2.0"


def test_hash_is_deterministic():
    a_text, a_hash = render_system_prompt(ORCHESTRATOR_TOOLS, max_steps=8)
    b_text, b_hash = render_system_prompt(ORCHESTRATOR_TOOLS, max_steps=8)
    assert a_hash == b_hash
    assert a_text == b_text
    assert len(a_hash) == 12


def test_hash_changes_with_max_steps():
    _, h8 = render_system_prompt(ORCHESTRATOR_TOOLS, max_steps=8)
    _, h12 = render_system_prompt(ORCHESTRATOR_TOOLS, max_steps=12)
    assert h8 != h12


def test_hash_changes_with_tool_names():
    _, h_orch = render_system_prompt(ORCHESTRATOR_TOOLS, max_steps=8)
    _, h_cli = render_system_prompt(CLI_TOOLS, max_steps=8)
    assert h_orch != h_cli


def test_two_renders_differ_only_by_tool_name_substitution():
    """Fairness invariant: switching `tool_names` must change the rendered
    prompt only at the placeholder sites. We use synthetic markers so the
    test isn't fooled by natural-English collisions (e.g. "Edit" appearing
    in section text)."""
    markers_a = {"read": "<<R_A>>", "edit": "<<E_A>>", "run": "<<X_A>>"}
    markers_b = {"read": "<<R_B>>", "edit": "<<E_B>>", "run": "<<X_B>>"}
    text_a, _ = render_system_prompt(markers_a, max_steps=8)
    text_b, _ = render_system_prompt(markers_b, max_steps=8)

    def normalize(text, markers):
        return (
            text.replace(markers["read"], "<<READ>>")
                .replace(markers["edit"], "<<EDIT>>")
                .replace(markers["run"], "<<RUN>>")
        )

    assert normalize(text_a, markers_a) == normalize(text_b, markers_b)


def test_prompt_contains_required_sections():
    text, _ = render_system_prompt(ORCHESTRATOR_TOOLS, max_steps=8)
    for marker in (
        "Success Criterion",
        "Failure Modes",
        "Workflow",
        "Test-File Modification",
        "Stop Conditions",
        "Step Budget",
        "Reasoning Fields",
        "Rules",
    ):
        assert marker in text, f"Missing section: {marker}"


def test_prompt_announces_step_budget():
    text, _ = render_system_prompt(ORCHESTRATOR_TOOLS, max_steps=11)
    assert "at most 11 steps" in text


def test_prompt_mentions_failure_modes_by_name():
    text, _ = render_system_prompt(ORCHESTRATOR_TOOLS, max_steps=8)
    assert "TEST_PASSES_ON_BUG" in text
    assert "OVERFIT_TO_BUG" in text


def test_critic_prompt_uses_same_failure_mode_names():
    """Critic and agent must speak the same taxonomy or feedback won't land."""
    for name in ("TEST_PASSES_ON_BUG", "OVERFIT_TO_BUG"):
        assert name in CRITIC_PROMPT
        assert name in FAILURE_MODES


def test_test_writer_prompt_mentions_failure_modes():
    assert "TEST_PASSES_ON_BUG" in TEST_WRITER_SYSTEM_PROMPT
    assert "OVERFIT_TO_BUG" in TEST_WRITER_SYSTEM_PROMPT


def test_analyzer_prompt_requires_json_only():
    assert "ONLY valid JSON" in ANALYZER_PROMPT
    assert "bug_hypothesis" in ANALYZER_PROMPT
    assert "confidence" in ANALYZER_PROMPT
