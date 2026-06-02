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
from bugtest.agents.deep_agent import run_deep_agent, run_scout_analysis
from bugtest.agents.test_writer import TestWriter
from bugtest.deep.prompts import PROMPT_VERSION
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
    parts = [
        f"Task: {task.task_id}",
        f"Bug Description: {task.metadata.bug_description}",
    ]
    if task.metadata.test_hint:
        parts.append(f"Test Hint: {task.metadata.test_hint}")
    parts += [
        "",
        "--- source.py ---",
        task.buggy_code,
        "--- end source.py ---",
        "",
        "Write a pytest test that FAILS on this buggy code "
        "but PASSES on the fixed version.",
    ]
    return "\n".join(parts)


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


def _prepend_scout_analysis(user_message: str, scout_text: str) -> str:
    """Prepend the scout's tool-augmented analysis for Scout-Writer mode.

    The scout drove the deep tool loop to investigate the code; the writer
    sees only this distilled analysis (no tools, fresh context).
    """
    block = (
        "=== SCOUT ANALYSIS (tool-augmented investigation of source.py) ===\n"
        f"{scout_text.strip()}\n"
        "=== END SCOUT ANALYSIS ===\n\n"
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
    model_id: Optional[str] = None,
) -> RunRecord:
    """Run one complete pipeline with four possible modes.

    Modes:
        baseline:  TestWriter only, retry on failure
        agentic:   Analyzer first, then TestWriter, retry on failure
        adaptive:  Attempt 1 without analysis (baseline-style),
                   if it fails, add analysis for remaining attempts
        deep:      Tool-augmented ReAct agent in a sandbox workspace.
                   On failure, a critic subagent's feedback feeds the next
                   outer iteration. Uses the deep/ orchestrator port.
        scout:     Scout-Writer. A scout drives the deep tool loop to produce
                   a structured analysis (no test), then a tool-free writer
                   authors the test from that analysis with the same retry
                   budget. Decouples tool-driving from test generation.
    """
    start_time = time.perf_counter()
    prompt_tokens = 0
    completion_tokens = 0
    analysis: Optional[CodeAnalysis] = None
    attempts: list[AttemptRecord] = []
    base_user_message = _build_user_message(task)
    user_message = base_user_message

    # --- DEEP: tool-augmented agent, separate code path ---
    if mode == "deep":
        if model_id is None:
            raise ValueError("deep mode requires model_id")
        deep_result = run_deep_agent(
            task=task,
            model_id=model_id,
            validator=validator,
            max_attempts=max_attempts,
        )
        final_validation = validator.validate(
            test_code=deep_result.final_test_code,
            buggy_dir=task.buggy_dir,
            fixed_dir=task.fixed_dir,
        )
        attempts.append(
            AttemptRecord(
                attempt_number=deep_result.outer_iterations or 1,
                test_code=deep_result.final_test_code,
                validation=final_validation,
                timestamp=_now_iso(),
                tool_call_count=deep_result.tool_call_count,
                tool_failure_mode_count=dict(deep_result.tool_failure_mode_count),
                reasoning_filled=deep_result.reasoning_filled,
            )
        )
        duration = time.perf_counter() - start_time
        success = final_validation.is_bug_revealing
        return RunRecord(
            task_id=task.task_id,
            mode=mode,
            run_number=run_number,
            success=success,
            attempts=attempts,
            total_attempts=deep_result.outer_iterations or 1,
            attempts_to_success=(deep_result.outer_iterations if success else None),
            analysis=None,
            prompt_tokens_total=deep_result.prompt_tokens,
            completion_tokens_total=deep_result.completion_tokens,
            duration_seconds=round(duration, 2),
            timestamp=_now_iso(),
            prompt_version=deep_result.prompt_version,
            prompt_template_hash=deep_result.prompt_template_hash,
            capabilities_used=dict(deep_result.capabilities_used),
            tool_choice_mode="auto" if deep_result.capabilities_used else "",
        )

    # --- AGENTIC: run Analyzer upfront ---
    if mode == "agentic":
        analyzer = Analyzer(llm)
        analysis, resp = analyzer.run(user_message)
        prompt_tokens += resp.prompt_tokens
        completion_tokens += resp.completion_tokens
        user_message = _prepend_analysis(user_message, analysis)

    # --- SCOUT: tool-augmented analysis upfront, then tool-free writer ---
    # Decouples exploration from generation: the scout drives the deep tool
    # loop to investigate the code; the writer below sees only the distilled
    # analysis and writes the test in a fresh, tool-free context.
    if mode == "scout":
        if model_id is None:
            raise ValueError("scout mode requires model_id")
        scout = run_scout_analysis(task=task, model_id=model_id)
        prompt_tokens += scout.prompt_tokens
        completion_tokens += scout.completion_tokens
        user_message = _prepend_scout_analysis(base_user_message, scout.analysis_text)

    # --- Both modes: TestWriter with retry loop ---
    writer = TestWriter(llm)

    for attempt_num in range(1, max_attempts + 1):

        # --- ADAPTIVE: inject analysis after first failure ---
        if mode == "adaptive" and attempt_num == 2 and analysis is None:
            try:
                analyzer = Analyzer(llm)
                analysis, resp = analyzer.run(base_user_message)
                prompt_tokens += resp.prompt_tokens
                completion_tokens += resp.completion_tokens
                user_message = _prepend_analysis(base_user_message, analysis)
            except Exception:
                pass  # analysis failed, continue without it

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
        # Non-deep modes share the v2.0 failure-mode taxonomy via the
        # TestWriter prompt re-exported from bugtest.deep.prompts; tagging
        # the version makes pre/post refactor BRTRs comparable across modes.
        prompt_version=PROMPT_VERSION,
    )
