"""Deep agent mode wrapper around the ported deep-test orchestrator.

Outer loop (max_attempts iterations):
    1. Build a fresh temp workspace with:
         source.py                  (copy from task.buggy_dir)
         tests/test_benchmark.py    (baseline import-only test)
    2. Run DeepTestOrchestrator. The agent reads source.py, appends a
       bug-revealing test to tests/test_benchmark.py, and validates by
       calling the run_tests tool.
    3. Read tests/test_benchmark.py and validate it deterministically
       against task.buggy_dir AND task.fixed_dir using `Validator`.
    4. If validation says "bug-revealing" → done. Otherwise:
         - run the orchestrator's CRITIC subagent on the failing test
           plus the buggy/fixed pytest output;
         - feed the critic's recommendation into the next outer iteration's
           problem prompt and try again.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bugtest.models import Task
from bugtest.validator import Validator


CLAUDE_MODELS = {"sonnet", "opus", "haiku"}

# Keep deep-agent workspaces inside the project tree (no /var/folders, no /tmp)
_LOCAL_TMP = Path(__file__).resolve().parent.parent.parent / ".tmp"
_LOCAL_TMP.mkdir(exist_ok=True)

_BASELINE_TEST = (
    "import source\n"
    "\n"
    "\n"
    "def test_source_module_imports():\n"
    "    assert source is not None\n"
)


@dataclass
class DeepRunResult:
    final_test_code: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    steps_used: int = 0
    outer_iterations: int = 0
    status: str = ""
    critic_feedback: list[str] = field(default_factory=list)


def _resolve_deep_model_name(model_id: str) -> str:
    """Map this project's model_id into the deep/llm.py provider-prefixed form.

    Routing rules:
      - Bare Claude tier name ("sonnet", "opus", "haiku") -> claude:<id>
        (uses the Claude Code CLI provider; no API key needed).
      - "/" in id AND TOGETHER_API_KEY set -> openai:<id> with Together base URL
        (we plumb that through env so deep/llm.py picks it up).
      - "/" in id AND NVIDIA_API_KEY set -> nvidia:<id>.
      - Otherwise leave the prefix to the caller.
    """
    if model_id in CLAUDE_MODELS:
        return f"claude:{model_id}"
    if "/" in model_id:
        if os.environ.get("TOGETHER_API_KEY"):
            os.environ.setdefault("OPENAI_API_KEY", os.environ["TOGETHER_API_KEY"])
            os.environ.setdefault(
                "DEEPTEST_OPENAI_BASE_URL", "https://api.together.xyz/v1"
            )
            return f"openai:{model_id}"
        if os.environ.get("NVIDIA_API_KEY"):
            return f"nvidia:{model_id}"
    return model_id


def _build_workspace(task: Task) -> Path:
    workspace = Path(tempfile.mkdtemp(prefix=f"deep_{task.task_id}_", dir=str(_LOCAL_TMP)))
    for src in task.buggy_dir.glob("*.py"):
        shutil.copy(src, workspace / src.name)
    tests_dir = workspace / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_benchmark.py").write_text(_BASELINE_TEST, encoding="utf-8")
    return workspace


def _build_problem(task: Task, critic_feedback: Optional[str] = None,
                   use_cli_tools: bool = False) -> str:
    """Compose the user message handed to the orchestrator.

    When `use_cli_tools=True` (Claude Code CLI provider), the prompt refers to
    Claude's native Read/Edit/Bash tools. Otherwise it refers to the
    orchestrator-side tool registry (`safe_edit_file`, `run_tests`).
    """
    bug_desc = task.metadata.bug_description or "(no description)"
    hint = task.metadata.test_hint or ""
    parts = [
        f"Task: Add a focused bug-revealing pytest test for tasks_v2 task '{task.task_id}'.",
        f"Target test file: `tests/test_benchmark.py`.",
        f"Known bug description: {bug_desc}",
        f"Hint: {hint}",
        "",
    ]
    if use_cli_tools:
        parts += [
            "Steps:",
            "1. Use Read on `source.py` to understand the code and the bug.",
            "2. Use Read on `tests/test_benchmark.py` to see the baseline test.",
            "3. Use Edit on `tests/test_benchmark.py` to APPEND a new test after",
            "   the existing baseline test. Set old_string to the last line of",
            "   the file and new_string to that same line followed by your new",
            "   test function. NEVER overwrite the existing import / baseline test.",
            "4. Use Bash to run: `python -m pytest tests/test_benchmark.py -v`",
            "   and confirm your new test FAILS (because the code is buggy).",
            "Keep the test focused. A failing test on the buggy code is the goal.",
        ]
    else:
        parts += [
            "Steps:",
            "1. Read source.py to understand the code and the bug.",
            "2. Read tests/test_benchmark.py to see the existing baseline test.",
            "3. Use safe_edit_file with old_string/new_string to APPEND your new test",
            "   AFTER the existing tests. Use old_string to match the last line of the",
            "   existing file, new_string to add your test after it. Set",
            "   allow_bug_revealing=true.",
            "4. The new test must FAIL on the buggy code (revealing the bug).",
            "Keep the test focused. Do NOT overwrite existing tests.",
        ]
    if critic_feedback:
        parts.extend([
            "",
            "=== PREVIOUS ATTEMPT FAILED — CRITIC FEEDBACK ===",
            critic_feedback.strip(),
            "=== END FEEDBACK ===",
            "",
            "Address the critic's feedback in your new attempt. The existing",
            "tests/test_benchmark.py has been reset to the baseline; rewrite",
            "your bug-revealing test from scratch.",
        ])
    return "\n".join(parts)


def _validation_summary(validation, test_code: str) -> str:
    """Build the critic-readable summary; lead with a named failure-mode label.

    The diagnosis taxonomy mirrors `bugtest/pipeline.py:_build_retry_context`
    so deep mode and the non-deep retry path use the same vocabulary.
    """
    if validation.buggy_passed:
        diagnosis = (
            "DIAGNOSIS: TEST_PASSES_ON_BUG — Test PASSED on buggy code "
            "(should FAIL to reveal the bug)."
        )
    elif not validation.fixed_passed:
        diagnosis = (
            "DIAGNOSIS: OVERFIT_TO_BUG — Test FAILED on fixed code too "
            "(overfitting — not targeting the actual bug)."
        )
    else:
        diagnosis = (
            "DIAGNOSIS: UNKNOWN — buggy/fixed validation produced an "
            "unexpected combination."
        )
    return (
        f"{diagnosis}\n\n"
        f"Test code:\n```python\n{test_code}\n```\n\n"
        f"buggy_passed={validation.buggy_passed}  "
        f"fixed_passed={validation.fixed_passed}\n"
        f"--- buggy pytest output (last 800 chars) ---\n"
        f"{validation.buggy_output[-800:]}\n"
        f"--- fixed pytest output (last 800 chars) ---\n"
        f"{validation.fixed_output[-800:]}"
    )


def run_deep_agent(task: Task, model_id: str, validator: Validator,
                   max_attempts: int = 3) -> DeepRunResult:
    """Run the deep agent on a task.

    max_attempts is the OUTER-loop budget (orchestrator runs); a critic
    subagent feeds into the next iteration if validation fails.
    """
    from bugtest.deep.orchestrator import DeepTestOrchestrator

    model_name = _resolve_deep_model_name(model_id)
    use_cli_tools = model_name.startswith("claude:")

    if model_name.startswith("nvidia:") and not os.environ.get("NVIDIA_API_KEY"):
        raise EnvironmentError("Set NVIDIA_API_KEY for NVIDIA-routed deep mode.")
    if model_name.startswith("openai:") and not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError(
            "Set TOGETHER_API_KEY (or OPENAI_API_KEY) for Together-routed deep mode."
        )

    inner_max_steps = 8
    inner_timeout = 240

    total_p = 0
    total_c = 0
    total_steps = 0
    final_test_code = "# no test produced\n"
    last_status = ""
    critic_feedback: Optional[str] = None
    critic_history: list[str] = []
    outer = 0

    for outer in range(1, max_attempts + 1):
        workspace = _build_workspace(task)
        try:
            orch = DeepTestOrchestrator(
                workspace=str(workspace),
                model_name=model_name,
                max_steps=inner_max_steps,
                timeout_seconds=inner_timeout,
            )
            problem = _build_problem(task, critic_feedback, use_cli_tools=use_cli_tools)
            result = orch.run(problem)
            total_p += result.total_prompt_tokens
            total_c += result.total_completion_tokens
            total_steps += result.steps_used
            last_status = result.status

            try:
                final_test_code = (
                    workspace / "tests" / "test_benchmark.py"
                ).read_text(encoding="utf-8")
            except Exception:
                final_test_code = "# agent left no test file\n"

            v = validator.validate(
                test_code=final_test_code,
                buggy_dir=task.buggy_dir,
                fixed_dir=task.fixed_dir,
            )
            if v.is_bug_revealing:
                break

            if outer < max_attempts:
                critic_text = orch.run_critic(
                    test_code=final_test_code,
                    test_results=_validation_summary(v, final_test_code),
                )
                critic_feedback = critic_text
                critic_history.append(critic_text)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    return DeepRunResult(
        final_test_code=final_test_code,
        prompt_tokens=total_p,
        completion_tokens=total_c,
        steps_used=total_steps,
        outer_iterations=outer,
        status=last_status,
        critic_feedback=critic_history,
    )
