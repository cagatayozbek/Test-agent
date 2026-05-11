"""
DeepTest Types — Shared data structures used by the active agent and reporting flow.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field


@dataclass
class TestResult:
    """Result of running pytest."""

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    coverage_gaps: dict = field(default_factory=dict)  # {file: [missing_lines]}
    num_passed: int = 0
    num_failed: int = 0
    failure_messages: list = field(default_factory=list)

    @property
    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        parts = [f"Tests {status} (exit_code={self.exit_code})"]
        if self.num_passed or self.num_failed:
            parts.append(f"{self.num_passed} passed, {self.num_failed} failed")
        if self.failure_messages:
            parts.append(f"Failures: {'; '.join(self.failure_messages[:3])}")
        if self.coverage_gaps:
            for file_path, lines in self.coverage_gaps.items():
                parts.append(f"Coverage gap: {file_path} lines {lines}")
        return "\n".join(parts)


@dataclass
class EditResult:
    """Result of a file edit attempt."""

    success: bool
    path: str
    message: str
    tests_after: Optional[TestResult] = None
    reverted: bool = False


# ── Deep Agents SDK Models ──────────────────────────────────
# Used for subagent structured output (response_format parameter)


class CritiqueResult(BaseModel):
    """Structured output from the Critic subagent.

    The Critic evaluates generated tests and returns this structured
    assessment. The main agent uses `approved` and `recommendation`
    to decide whether to revise or finalize.
    """

    approved: bool = Field(description="Whether the test meets quality standards and is approved")
    overall_score: float = Field(description="Quality score from 0.0 to 1.0 (0.8+ = approve threshold)")
    feedback: str = Field(description="Detailed feedback about test quality, what works and what doesn't")
    missing_scenarios: list[str] = Field(default_factory=list, description="Specific test scenarios that are missing or incomplete")
    quality_issues: list[str] = Field(default_factory=list, description="Code quality issues found in the test (naming, assertions, etc.)")
    recommendation: str = Field(description="Action recommendation: APPROVE, REVISE, or REJECT")


class AnalysisReport(BaseModel):
    """Structured output from the Analyzer subagent.

    Provides a structured view of the project analysis including
    identified test gaps and recommended targets for test generation.
    """

    project_summary: str = Field(description="Brief overview of the project structure (modules, classes, functions)")
    high_risk_functions: list[str] = Field(description="Functions with high complexity and low test coverage")
    test_gaps: list[str] = Field(description="Specific areas where test coverage is missing")
    recommended_targets: list[str] = Field(description="Priority-ordered list of functions/methods to write tests for")
    dependency_insights: str = Field(default="", description="Notable dependency relationships that affect testing strategy")


AgentRunStatus = Literal["completed", "failed", "timeout", "recursion_limit", "error"]


class AgentRunResult(BaseModel):
    """Result of an agent run."""

    status: AgentRunStatus = Field(description="'completed', 'failed', 'timeout', 'recursion_limit', or 'error'")
    messages: list[Any] = Field(default_factory=list, description="Raw message history")
    summary: dict = Field(default_factory=dict, description="Summary extracted from messages")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    steps_used: int = Field(default=0, description="Number of steps used")
    model_name: str = Field(description="The model used for the run")


class TestRunResult(BaseModel):
    """Structured output of running tests."""

    ok: bool
    passed: int
    failed: int
    errors: int
    skipped: int
    syntax_error: bool
    timeout: bool
    return_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    raw_output: dict = Field(default_factory=dict, description="Contains raw stdout and stderr")


class AgentRunReportInput(BaseModel):
    """Normalized input for ExecutionReporter."""

    task_id: str
    model_name: str
    status: AgentRunStatus
    messages: list[Any]
    summary: dict
