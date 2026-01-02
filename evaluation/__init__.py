# evaluation/__init__.py
"""Adversarial evaluation framework for LLM agent benchmarking.

Modules:
    evaluator: LLM-based evaluation for bug detection runs
    test_evaluator: LLM-based evaluation for test generation
    failure_analyzer: Failure categories and storage utilities
    run_all: CLI runner for batch evaluation

Key Classes:
    Evaluator: Evaluates bug detection performance
    TestEvaluator: Evaluates test generation with BRTR
    FailureCategory: Enum for test failure classification
    FailureRecord: Storage for failure records
    FailureDatabase: Persistent failure storage
"""

from .evaluator import Evaluator, EvaluationReport
from .test_evaluator import TestEvaluator, TestEvaluationResult, RetryGuidance
from .failure_analyzer import (
    FailureCategory,
    FailureRecord,
    FailureDatabase,
    extract_pytest_summary,
    check_syntax,
)

__all__ = [
    # Bug detection evaluation
    "Evaluator",
    "EvaluationReport",
    # Test generation evaluation
    "TestEvaluator",
    "TestEvaluationResult",
    "RetryGuidance",
    # Failure analysis
    "FailureCategory",
    "FailureRecord",
    "FailureDatabase",
    "extract_pytest_summary",
    "check_syntax",
]
