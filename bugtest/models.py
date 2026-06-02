"""All data models for the experiment system."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# --- Task ---


class TaskMetadata(BaseModel):
    """Parsed metadata.json from a task directory."""

    task_id: str = ""
    task_name: str = ""
    bug_description: str = ""
    bug_type: str = ""
    difficulty: str = ""
    test_hint: str = ""
    expected_failure_signal: str = ""
    source: str = ""
    model_config = {"extra": "allow"}

    def get_id(self) -> str:
        return self.task_id or self.task_name


class Task(BaseModel):
    """A single evaluation task with buggy/fixed code paths."""

    task_id: str
    buggy_code: str
    fixed_code: str
    buggy_dir: Path
    fixed_dir: Path
    metadata: TaskMetadata
    model_config = {"arbitrary_types_allowed": True}


# --- Agent Outputs ---


class CodeAnalysis(BaseModel):
    """Structured output from the Analyzer agent."""

    bug_hypothesis: str
    bug_location: str
    trigger_condition: str
    expected_vs_actual: str
    suggested_test_strategy: str
    confidence: Literal["low", "medium", "high"] = "medium"


# --- Validation ---


class ValidationResult(BaseModel):
    """Result of running a test against buggy + fixed code."""

    buggy_passed: bool
    buggy_output: str
    fixed_passed: bool
    fixed_output: str
    is_bug_revealing: bool
    error: Optional[str] = None


# --- Single Run ---


class AttemptRecord(BaseModel):
    """Record of one test generation attempt."""

    attempt_number: int
    test_code: str
    validation: ValidationResult
    timestamp: str
    # v2.0 instrumentation (default values preserve v1.x deserializability).
    tool_call_count: int = 0
    tool_failure_mode_count: Dict[str, int] = Field(default_factory=dict)
    reasoning_filled: bool = False


class RunRecord(BaseModel):
    """Complete record of one pipeline run (all retries for one task+mode)."""

    task_id: str
    mode: Literal["baseline", "agentic", "adaptive", "deep", "scout"]
    run_number: int
    success: bool
    attempts: list[AttemptRecord]
    total_attempts: int
    attempts_to_success: Optional[int] = None
    analysis: Optional[CodeAnalysis] = None
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0
    duration_seconds: float = 0.0
    timestamp: str = ""
    error: Optional[str] = None  # populated when pipeline raised before completion
    # v2.0 prompt-strategy provenance. Defaults keep older summary.json files
    # deserializable as v1.x; the migration script tags them retroactively.
    prompt_version: str = ""
    prompt_template_hash: str = ""
    # Mixed-type values (provider str, parallel/structured bools, tool_names dict).
    capabilities_used: Dict[str, Any] = Field(default_factory=dict)
    tool_choice_mode: Literal["auto", "required", "none", ""] = ""


# --- Experiment Summary ---


class ModeStats(BaseModel):
    """Aggregated statistics for one mode across all tasks."""

    mode: Literal["baseline", "agentic", "adaptive", "deep", "scout"]
    total_runs: int
    successful_runs: int
    brtr: float
    brtr_ci_lower: float = 0.0
    brtr_ci_upper: float = 0.0
    avg_attempts_to_success: Optional[float] = None
    avg_prompt_tokens: float = 0.0
    avg_completion_tokens: float = 0.0
    avg_duration_seconds: float = 0.0


class TaskStats(BaseModel):
    """Per-task comparison between modes."""

    task_id: str
    baseline_brtr: float
    agentic_brtr: float
    baseline_avg_attempts: Optional[float] = None
    agentic_avg_attempts: Optional[float] = None


class ExperimentSummary(BaseModel):
    """Final experiment output with statistical analysis."""

    experiment_name: str
    model_id: str
    timestamp: str
    total_tasks: int
    runs_per_task: int
    max_attempts: int
    mode_stats: list[ModeStats]
    task_stats: list[TaskStats]
    raw_brtr_baseline: list[float] = Field(default_factory=list)
    raw_brtr_agentic: list[float] = Field(default_factory=list)
