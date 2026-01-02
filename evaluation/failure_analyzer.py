"""Failure analysis utilities for test generation evaluation.

This module provides helper utilities for working with test failure data.
The actual classification and analysis is done by TestEvaluator (LLM-based).

This module only provides:
    - FailureCategory enum for type safety
    - FailureRecord dataclass for storage
    - Helper functions for pytest output parsing (non-classification)
    - FailureDatabase for persistence

For classification and analysis, use evaluation/test_evaluator.py which
provides LLM-based semantic understanding instead of rule-based heuristics.

Example:
    >>> from failure_analyzer import FailureCategory, FailureRecord
    >>> from test_evaluator import TestEvaluator
    >>> 
    >>> # Use TestEvaluator for classification
    >>> evaluator = TestEvaluator(llm)
    >>> result = evaluator.evaluate_test(...)
    >>> 
    >>> # Store result using FailureRecord
    >>> record = FailureRecord.from_evaluation_result(result)
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import re


class FailureCategory(Enum):
    """Classification categories for test generation attempts.
    
    These categories are determined by the LLM-based TestEvaluator.
    This enum provides type safety for storing and comparing results.
    """
    
    # Success case
    SUCCESS = "success"          # Bug-revealing test ✓
    
    # Primary failure categories
    NO_FAIL = "no_fail"          # Test passes on buggy code
    OVERFIT = "overfit"          # Test fails on both versions
    FLAKY = "flaky"              # Non-deterministic results
    
    # Root cause categories (from LLM analysis)
    WRONG_ASSERT = "wrong_assert"      # Assertion doesn't target bug
    WRONG_INPUT = "wrong_input"        # Input doesn't trigger bug
    WRONG_STATE = "wrong_state"        # Setup doesn't create bug state
    SYNTAX_ERROR = "syntax_error"      # Test has syntax errors
    
    # Fallback
    UNKNOWN = "unknown"                # Unclassifiable


@dataclass
class FailureRecord:
    """Record of a single test generation attempt.
    
    Stores the result of running and evaluating a generated test.
    The category field is populated by TestEvaluator (LLM-based).
    
    Attributes:
        task_id: Task identifier
        attempt: Attempt number
        test_file: Path to generated test file
        category: Classification from LLM evaluator
        buggy_output: Pytest output from buggy run (truncated)
        fixed_output: Pytest output from fixed run (truncated)
        llm_analysis: LLM's analysis and reasoning
        retry_suggestion: LLM's suggestion for improvement
    """
    task_id: str
    attempt: int
    test_file: str
    category: FailureCategory
    buggy_output: str = ""
    fixed_output: str = ""
    llm_analysis: str = ""
    retry_suggestion: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "attempt": self.attempt,
            "test_file": self.test_file,
            "category": self.category.value,
            "buggy_output": self.buggy_output[:500],  # Truncate for storage
            "fixed_output": self.fixed_output[:500],
            "llm_analysis": self.llm_analysis,
            "retry_suggestion": self.retry_suggestion,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FailureRecord":
        """Create FailureRecord from dictionary."""
        return cls(
            task_id=data["task_id"],
            attempt=data["attempt"],
            test_file=data["test_file"],
            category=FailureCategory(data["category"]),
            buggy_output=data.get("buggy_output", ""),
            fixed_output=data.get("fixed_output", ""),
            llm_analysis=data.get("llm_analysis", ""),
            retry_suggestion=data.get("retry_suggestion", ""),
        )
    
    @classmethod
    def from_evaluation_result(cls, eval_result) -> "FailureRecord":
        """Create FailureRecord from TestEvaluationResult.
        
        Args:
            eval_result: TestEvaluationResult from TestEvaluator
        
        Returns:
            FailureRecord with data from LLM evaluation
        """
        return cls(
            task_id=eval_result.task_id,
            attempt=eval_result.attempt,
            test_file=eval_result.test_file,
            category=FailureCategory(eval_result.failure_category),
            buggy_output=eval_result.buggy_output,
            fixed_output=eval_result.fixed_output,
            llm_analysis=eval_result.why_not_revealing,
            retry_suggestion=eval_result.retry_guidance.suggestion,
        )


def extract_pytest_summary(output: str) -> dict:
    """Extract basic counts from pytest output.
    
    This is a helper function for quick parsing, not for classification.
    Classification should be done by TestEvaluator.
    
    Args:
        output: Raw pytest stdout/stderr
    
    Returns:
        dict with keys: passed, failed, errors
    """
    result = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
    }
    
    # Parse summary line: "1 passed, 2 failed"
    summary_match = re.search(r"(\d+) passed", output)
    if summary_match:
        result["passed"] = int(summary_match.group(1))
    
    failed_match = re.search(r"(\d+) failed", output)
    if failed_match:
        result["failed"] = int(failed_match.group(1))
    
    error_match = re.search(r"(\d+) error", output)
    if error_match:
        result["errors"] = int(error_match.group(1))
    
    return result


def check_syntax(test_content: str) -> tuple[bool, str]:
    """Check if test code has syntax errors.
    
    Quick validation before running tests. For detailed analysis
    of what's wrong, use TestEvaluator.
    
    Args:
        test_content: Python test code as string
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        compile(test_content, "<test>", "exec")
        return True, ""
    except SyntaxError as e:
        return False, str(e)


@dataclass
class FailureDatabase:
    """Persistent storage for failure records.
    
    Stores failure records to JSON for later analysis and pattern
    identification across multiple evaluation runs.
    
    Attributes:
        storage_path: Path to JSON storage file
        records: List of FailureRecord objects
    """
    storage_path: Path
    records: list[FailureRecord] = field(default_factory=list)
    
    def add_record(self, record: FailureRecord) -> None:
        """Add a failure record to the database."""
        self.records.append(record)
    
    def add_from_evaluation(self, eval_result) -> FailureRecord:
        """Add record from TestEvaluationResult.
        
        Args:
            eval_result: TestEvaluationResult from TestEvaluator
        
        Returns:
            Created FailureRecord
        """
        record = FailureRecord.from_evaluation_result(eval_result)
        self.add_record(record)
        return record
    
    def save(self) -> None:
        """Save all records to JSON file."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "records": [r.to_dict() for r in self.records],
            "summary": self.get_summary(),
        }
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def load(self) -> None:
        """Load records from JSON file."""
        if not self.storage_path.exists():
            return
        with open(self.storage_path, "r") as f:
            data = json.load(f)
        self.records = [FailureRecord.from_dict(r) for r in data.get("records", [])]
    
    def get_summary(self) -> dict:
        """Get summary statistics."""
        if not self.records:
            return {"total": 0, "categories": {}}
        
        category_counts = {}
        for record in self.records:
            cat = record.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "total": len(self.records),
            "categories": category_counts,
            "success_rate": category_counts.get("success", 0) / len(self.records),
        }
    
    def get_records_by_task(self, task_id: str) -> list[FailureRecord]:
        """Get all records for a specific task."""
        return [r for r in self.records if r.task_id == task_id]
    
    def get_retry_context(self, task_id: str) -> str:
        """Build context string for retry attempts.
        
        Formats previous failure records as context for the next
        test generation attempt.
        
        Args:
            task_id: Task to get context for
        
        Returns:
            Formatted context string
        """
        task_records = self.get_records_by_task(task_id)
        
        if not task_records:
            return ""
        
        parts = [
            "=== PREVIOUS ATTEMPTS SUMMARY ===",
            f"Total previous attempts: {len(task_records)}",
            ""
        ]
        
        for record in task_records[-3:]:  # Last 3 attempts
            parts.extend([
                f"### Attempt {record.attempt}",
                f"- Category: {record.category.value}",
                f"- Analysis: {record.llm_analysis[:200]}..." if record.llm_analysis else "- No analysis",
                f"- Suggestion: {record.retry_suggestion}",
                ""
            ])
        
        parts.append("Use this information to avoid repeating mistakes.")
        
        return "\n".join(parts)


def print_evaluation_summary(records: list[FailureRecord]) -> None:
    """Print human-readable summary to console.
    
    Args:
        records: List of FailureRecord objects
    """
    if not records:
        print("No records to summarize.")
        return
    
    total = len(records)
    category_counts = {}
    for record in records:
        cat = record.category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    success_count = category_counts.get("success", 0)
    success_rate = success_count / total
    
    print("\n📊 Test Generation Evaluation Summary")
    print("-" * 40)
    print(f"Total attempts: {total}")
    print(f"Success rate: {success_rate:.1%}")
    print("\nCategories (from LLM evaluation):")
    for cat, count in sorted(category_counts.items()):
        pct = count / total
        emoji = "✅" if cat == "success" else "❌"
        print(f"  {emoji} {cat}: {count} ({pct:.1%})")
