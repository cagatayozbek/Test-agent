"""Pipeline orchestrator for baseline and agentic modes.

Fair comparison design:
- SAME TestWriter system prompt for both modes
- SAME retry budget (max_attempts) for both modes
- SAME validator for both modes
- ONLY VARIABLE: agentic mode prepends CodeAnalysis to user message
"""

import time
from datetime import datetime, timezone
from typing import Optional

from bugtest.agents.analyzer import Analyzer
from bugtest.agents.test_writer import TestWriter
from bugtest.llm import GeminiClient
from bugtest.models import (
    AttemptRecord,
    CodeAnalysis,
    RunRecord,
    Task,
)
from bugtest.validator import Validator


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _build_user_message(task: Task) -> str:
    """Build user message from task (shared between both modes)."""
    return (
        f"Task: {task.task_id}\n"
        f"Bug Description: {task.metadata.bug_description}\n\n"
        f"--- source.py ---\n"
        f"{task.buggy_code}\n"
        f"--- end source.py ---\n\n"
        f"Write a pytest test that FAILS on this buggy code "
        f"but PASSES on the fixed version."
    )


def _prepend_analysis(user_message: str, analysis: CodeAnalysis) -> str:
    """Prepend analysis context to user message for agentic mode."""
    block = (
        "=== CODE ANALYSIS (from Analyzer agent) ===\n"
        f"Bug Hypothesis: {analysis.bug_hypothesis}\n"
        f"Bug Location: {analysis.bug_location}\n"
        f"Trigger Condition: {analysis.trigger_condition}\n"
        f"Expected vs Actual: {analysis.expected_vs_actual}\n"
        f"Suggested Test Strategy: {analysis.suggested_test_strategy}\n"
        f"Confidence: {analysis.confidence}\n"
        "=== END ANALYSIS ===\n\n"
    )
    return block + user_message


def _build_retry_context(attempts: list[AttemptRecord]) -> str:
    """Build retry feedback from previous attempts."""
    parts = []
    for a in attempts:
        v = a.validation
        if v.buggy_passed:
            reason = "Test PASSED on buggy code (should FAIL to reveal the bug)"
        elif not v.fixed_passed:
            reason = "Test FAILED on fixed code too (overfitting — not targeting the actual bug)"
        else:
            reason = "Unknown failure"

        parts.append(
            f"Attempt {a.attempt_number}:\n"
            f"  Problem: {reason}\n"
            f"  Buggy output (last 500 chars): ...{v.buggy_output[-500:]}\n"
            f"  Fixed output (last 500 chars): ...{v.fixed_output[-500:]}\n"
        )
    return "\n".join(parts)


def run_pipeline(
    task: Task,
    mode: str,
    run_number: int,
    llm: GeminiClient,
    validator: Validator,
    max_attempts: int = 3,
) -> RunRecord:
    """Run one complete pipeline: analysis (if agentic) + test_writer with retries.

    The ONLY difference between modes: agentic calls Analyzer first and
    prepends its CodeAnalysis output to the TestWriter's user message.
    Everything else is identical.
    """
    start_time = time.perf_counter()
    prompt_tokens = 0
    completion_tokens = 0
    analysis: Optional[CodeAnalysis] = None
    attempts: list[AttemptRecord] = []
    user_message = _build_user_message(task)

    # --- AGENTIC: run Analyzer first (one call, NOT retried) ---
    if mode == "agentic":
        analyzer = Analyzer(llm)
        analysis, resp = analyzer.run(user_message)
        prompt_tokens += resp.prompt_tokens
        completion_tokens += resp.completion_tokens
        user_message = _prepend_analysis(user_message, analysis)

    # --- Both modes: TestWriter with retry loop ---
    writer = TestWriter(llm)

    for attempt_num in range(1, max_attempts + 1):
        if attempt_num == 1:
            test_code, resp = writer.run(user_message)
        else:
            retry_ctx = _build_retry_context(attempts)
            test_code, resp = writer.run_with_retry_context(user_message, retry_ctx)

        prompt_tokens += resp.prompt_tokens
        completion_tokens += resp.completion_tokens

        validation = validator.validate(
            test_code=test_code,
            buggy_dir=task.buggy_dir,
            fixed_dir=task.fixed_dir,
        )

        attempts.append(
            AttemptRecord(
                attempt_number=attempt_num,
                test_code=test_code,
                validation=validation,
                timestamp=_now_iso(),
            )
        )

        if validation.is_bug_revealing:
            break

    duration = time.perf_counter() - start_time
    success = any(a.validation.is_bug_revealing for a in attempts)
    attempts_to_success = None
    if success:
        attempts_to_success = next(
            a.attempt_number for a in attempts if a.validation.is_bug_revealing
        )

    return RunRecord(
        task_id=task.task_id,
        mode=mode,
        run_number=run_number,
        success=success,
        attempts=attempts,
        total_attempts=len(attempts),
        attempts_to_success=attempts_to_success,
        analysis=analysis,
        prompt_tokens_total=prompt_tokens,
        completion_tokens_total=completion_tokens,
        duration_seconds=round(duration, 2),
        timestamp=_now_iso(),
    )
