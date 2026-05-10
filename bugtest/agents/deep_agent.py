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

This makes deep mode "iterate-and-self-critique", comparable to baseline +
adaptive's retry budgets but with a tool-augmented agent inside.
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


def _build_workspace(task: Task) -> Path:
    workspace = Path(tempfile.mkdtemp(prefix=f"deep_{task.task_id}_", dir=str(_LOCAL_TMP)))
    for src in task.buggy_dir.glob("*.py"):
        shutil.copy(src, workspace / src.name)
    tests_dir = workspace / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_benchmark.py").write_text(_BASELINE_TEST, encoding="utf-8")
    return workspace


def _build_problem(task: Task, critic_feedback: Optional[str] = None) -> str:
    bug_desc = task.metadata.bug_description or "(no description)"
    hint = task.metadata.test_hint or ""
    parts = [
        f"Task: Add a focused bug-revealing pytest test for tasks_v2 task '{task.task_id}'.",
        f"Target test file: `tests/test_benchmark.py`.",
        f"Known bug description: {bug_desc}",
        f"Hint: {hint}",
        "",
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
    return (
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

    if model_id in CLAUDE_MODELS:
        model_name = f"claude:{model_id}"
    elif "/" in model_id:
        model_name = f"nvidia:{model_id}"
    else:
        model_name = model_id

    if model_name.startswith("nvidia:") and not os.environ.get("NVIDIA_API_KEY"):
        raise EnvironmentError("Set NVIDIA_API_KEY for non-Claude deep mode.")

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
            problem = _build_problem(task, critic_feedback)
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

            # Deterministic check
            v = validator.validate(
                test_code=final_test_code,
                buggy_dir=task.buggy_dir,
                fixed_dir=task.fixed_dir,
            )
            if v.is_bug_revealing:
                break

            # On failure (and if we still have budget) ask the critic.
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
