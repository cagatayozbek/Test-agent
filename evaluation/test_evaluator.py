"""LLM-Based Test Evaluator for test generation assessment.

This module provides LLM-based evaluation of generated tests, replacing
rule-based classification with semantic understanding. The evaluator
analyzes pytest outputs and determines if tests are bug-revealing.

Key Features:
    - LLM judges if test is bug-revealing (not boolean logic)
    - LLM classifies failure reasons semantically
    - LLM provides actionable feedback for retry attempts
    - Full context passing for iterative improvement

Classes:
    TestEvaluator: Main LLM-based evaluator
    TestEvaluationResult: Structured evaluation output
    RetryGuidance: Feedback for test improvement

Example:
    >>> evaluator = TestEvaluator(llm_client)
    >>> result = evaluator.evaluate_test(
    ...     test_code="def test_boundary(): ...",
    ...     buggy_output="FAILED - AssertionError",
    ...     fixed_output="PASSED",
    ...     bug_description="Off-by-one in threshold check"
    ... )
    >>> if result.is_bug_revealing:
    ...     print("Success!")
    >>> else:
    ...     print(f"Retry guidance: {result.retry_guidance.suggestion}")
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal

from pydantic import BaseModel


class TestEvaluationResponse(BaseModel):
    """Pydantic model for LLM evaluation response."""
    
    # Core verdict
    is_bug_revealing: bool
    confidence: Literal["high", "medium", "low"]
    
    # Failure classification (if not bug-revealing)
    failure_category: Literal[
        "success",      # Bug-revealing test
        "no_fail",      # Test passes on buggy code
        "overfit",      # Test fails on both versions
        "flaky",        # Non-deterministic behavior
        "wrong_assert", # Assertion targets wrong behavior
        "wrong_input",  # Input doesn't trigger bug
        "wrong_state",  # Setup doesn't create bug state
        "syntax_error", # Test has syntax/import errors
        "unknown"       # Unclassifiable
    ]
    
    # Analysis
    buggy_analysis: str      # What happened on buggy code
    fixed_analysis: str      # What happened on fixed code
    why_not_revealing: str   # Why test isn't bug-revealing (if applicable)
    
    # Retry guidance
    should_retry: bool
    retry_suggestion: str    # Specific improvement suggestion
    
    # Overall assessment
    test_quality_score: int  # 1-10
    commentary: str


@dataclass
class RetryGuidance:
    """Structured guidance for improving a failed test."""
    should_retry: bool
    suggestion: str
    focus_areas: list[str] = field(default_factory=list)
    avoid_patterns: list[str] = field(default_factory=list)


@dataclass
class TestEvaluationResult:
    """Complete evaluation result for a generated test."""
    
    # Identity
    task_id: str
    attempt: int
    test_file: str
    
    # Core verdict (from LLM)
    is_bug_revealing: bool
    confidence: str
    failure_category: str
    
    # Raw outputs (for reference)
    buggy_output: str
    fixed_output: str
    
    # LLM analysis
    buggy_analysis: str
    fixed_analysis: str
    why_not_revealing: str
    
    # Retry info
    retry_guidance: RetryGuidance
    
    # Quality metrics
    test_quality_score: int
    commentary: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "attempt": self.attempt,
            "test_file": self.test_file,
            "is_bug_revealing": self.is_bug_revealing,
            "confidence": self.confidence,
            "failure_category": self.failure_category,
            "buggy_analysis": self.buggy_analysis,
            "fixed_analysis": self.fixed_analysis,
            "why_not_revealing": self.why_not_revealing,
            "should_retry": self.retry_guidance.should_retry,
            "retry_suggestion": self.retry_guidance.suggestion,
            "test_quality_score": self.test_quality_score,
            "commentary": self.commentary,
        }


TEST_EVALUATOR_PROMPT = """You are a Test Evaluation Agent. Your job is to determine if a generated test successfully reveals a bug.

## Bug-Revealing Test Definition
A test is "bug-revealing" if and only if:
1. It FAILS on the buggy code (exposes the bug)
2. It PASSES on the fixed code (confirms the fix works)

## Context You'll Receive
1. **Bug Description**: What bug the test should reveal
2. **Test Code**: The generated pytest test
3. **Buggy Run Output**: pytest output when run against buggy code
4. **Fixed Run Output**: pytest output when run against fixed code

## Your Task
Analyze the outputs and determine:
1. Did the test fail on buggy code? (Look for FAILED, AssertionError, etc.)
2. Did the test pass on fixed code? (Look for PASSED, "1 passed", etc.)
3. Is this a true bug-revealing test?

## Failure Categories (if not bug-revealing)
- `success`: Bug-revealing test ✓
- `no_fail`: Test passes on buggy code (doesn't expose bug)
- `overfit`: Test fails on BOTH versions (not specific to bug)
- `flaky`: Results seem non-deterministic
- `wrong_assert`: Assertion checks wrong thing
- `wrong_input`: Input values don't trigger the bug condition
- `wrong_state`: Test setup doesn't create the bug-triggering state
- `syntax_error`: Test has Python syntax or import errors
- `unknown`: Can't determine the issue

## Response Format (JSON)
{
    "is_bug_revealing": true/false,
    "confidence": "high|medium|low",
    "failure_category": "success|no_fail|overfit|...",
    "buggy_analysis": "What happened when running on buggy code",
    "fixed_analysis": "What happened when running on fixed code", 
    "why_not_revealing": "Explanation if not bug-revealing (empty if success)",
    "should_retry": true/false,
    "retry_suggestion": "Specific advice for improving the test",
    "test_quality_score": 1-10,
    "commentary": "Overall assessment"
}

Be precise. Base your judgment on the actual pytest output, not assumptions."""


class TestEvaluator:
    """LLM-based evaluator for generated tests.
    
    Uses LLM to semantically analyze test outputs and determine
    if tests are bug-revealing, replacing rule-based classification.
    
    Attributes:
        llm: GeminiClient instance for LLM calls
        history: List of previous evaluations for context
    
    Example:
        >>> from llm_client import GeminiClient
        >>> llm = GeminiClient(model_id="gemini-2.0-flash", api_key="...")
        >>> evaluator = TestEvaluator(llm)
        >>> result = evaluator.evaluate_test(
        ...     task_id="boundary_threshold",
        ...     attempt=1,
        ...     test_file="test_generated.py",
        ...     test_code="def test_x(): assert calculate(100) == 80",
        ...     buggy_output="FAILED - assert 95 == 80",
        ...     fixed_output="PASSED",
        ...     bug_description="Uses > instead of >= for threshold"
        ... )
    """
    
    def __init__(self, llm):
        """Initialize with LLM client.
        
        Args:
            llm: GeminiClient or compatible LLM client with generate_json()
        """
        self.llm = llm
        self.evaluation_history: list[TestEvaluationResult] = []
    
    def evaluate_test(
        self,
        task_id: str,
        attempt: int,
        test_file: str,
        test_code: str,
        buggy_output: str,
        fixed_output: str,
        bug_description: str,
        previous_attempts: list[dict] | None = None,
    ) -> TestEvaluationResult:
        """Evaluate a generated test using LLM.
        
        Args:
            task_id: Task identifier
            attempt: Current attempt number
            test_file: Path to test file
            test_code: The generated test code
            buggy_output: pytest output from running on buggy code
            fixed_output: pytest output from running on fixed code
            bug_description: Description of the bug to reveal
            previous_attempts: Optional list of previous attempt results for context
        
        Returns:
            TestEvaluationResult: Complete evaluation with verdict and guidance
        """
        # Build evaluation context
        context = self._build_context(
            test_code=test_code,
            buggy_output=buggy_output,
            fixed_output=fixed_output,
            bug_description=bug_description,
            previous_attempts=previous_attempts,
        )
        
        # Call LLM for evaluation
        try:
            response = self.llm.generate_json(
                system=TEST_EVALUATOR_PROMPT,
                user=context,
                response_schema=TestEvaluationResponse,
            )
            
            # Parse response - response.text is JSON string
            import json
            response_data = json.loads(response.text)
            eval_response = TestEvaluationResponse.model_validate(response_data)
            
        except Exception as e:
            # Fallback on LLM error
            print(f"⚠️ LLM evaluation error: {e}")
            eval_response = self._create_fallback_response(buggy_output, fixed_output)
        
        # Build result
        result = TestEvaluationResult(
            task_id=task_id,
            attempt=attempt,
            test_file=test_file,
            is_bug_revealing=eval_response.is_bug_revealing,
            confidence=eval_response.confidence,
            failure_category=eval_response.failure_category,
            buggy_output=buggy_output[:1000],  # Truncate for storage
            fixed_output=fixed_output[:1000],
            buggy_analysis=eval_response.buggy_analysis,
            fixed_analysis=eval_response.fixed_analysis,
            why_not_revealing=eval_response.why_not_revealing,
            retry_guidance=RetryGuidance(
                should_retry=eval_response.should_retry,
                suggestion=eval_response.retry_suggestion,
            ),
            test_quality_score=eval_response.test_quality_score,
            commentary=eval_response.commentary,
        )
        
        # Store in history
        self.evaluation_history.append(result)
        
        return result
    
    def _build_context(
        self,
        test_code: str,
        buggy_output: str,
        fixed_output: str,
        bug_description: str,
        previous_attempts: list[dict] | None = None,
    ) -> str:
        """Build evaluation context for LLM."""
        
        parts = [
            "## Bug Description",
            bug_description,
            "",
            "## Generated Test Code",
            "```python",
            test_code,
            "```",
            "",
            "## Buggy Code Run Output",
            "```",
            buggy_output[:2000] if len(buggy_output) > 2000 else buggy_output,
            "```",
            "",
            "## Fixed Code Run Output", 
            "```",
            fixed_output[:2000] if len(fixed_output) > 2000 else fixed_output,
            "```",
        ]
        
        # Add previous attempts context if available
        if previous_attempts:
            parts.extend([
                "",
                "## Previous Attempts (for context)",
            ])
            for prev in previous_attempts[-3:]:  # Last 3 attempts
                parts.append(f"- Attempt {prev.get('attempt', '?')}: "
                           f"{prev.get('failure_category', 'unknown')} - "
                           f"{prev.get('retry_suggestion', 'no suggestion')}")
        
        return "\n".join(parts)
    
    def _create_fallback_response(
        self,
        buggy_output: str,
        fixed_output: str
    ) -> TestEvaluationResponse:
        """Create fallback response when LLM fails.
        
        Uses simple heuristics as backup - not ideal but prevents crashes.
        """
        buggy_failed = "FAILED" in buggy_output or "Error" in buggy_output
        fixed_passed = "passed" in fixed_output.lower() and "failed" not in fixed_output.lower()
        
        is_bug_revealing = buggy_failed and fixed_passed
        
        if is_bug_revealing:
            category = "success"
        elif not buggy_failed:
            category = "no_fail"
        elif not fixed_passed:
            category = "overfit"
        else:
            category = "unknown"
        
        return TestEvaluationResponse(
            is_bug_revealing=is_bug_revealing,
            confidence="low",
            failure_category=category,
            buggy_analysis="[Fallback] Could not analyze - LLM error",
            fixed_analysis="[Fallback] Could not analyze - LLM error",
            why_not_revealing="" if is_bug_revealing else "LLM analysis unavailable",
            should_retry=not is_bug_revealing,
            retry_suggestion="Review test manually and retry",
            test_quality_score=5,
            commentary="Evaluation performed with fallback heuristics due to LLM error",
        )
    
    def get_retry_context(self, task_id: str) -> str:
        """Build context from previous attempts for retry.
        
        Collects all previous evaluation results for a task and formats
        them as context for the next test generation attempt.
        
        Args:
            task_id: Task identifier to filter history
        
        Returns:
            str: Formatted context string for injection into TestWriter prompt
        """
        task_history = [
            r for r in self.evaluation_history 
            if r.task_id == task_id
        ]
        
        if not task_history:
            return ""
        
        parts = [
            "=== PREVIOUS TEST GENERATION ATTEMPTS ===",
            f"Total attempts so far: {len(task_history)}",
            ""
        ]
        
        for result in task_history:
            parts.extend([
                f"### Attempt {result.attempt}",
                f"- Result: {result.failure_category}",
                f"- Bug-Revealing: {'✓' if result.is_bug_revealing else '✗'}",
                f"- Analysis: {result.why_not_revealing or 'N/A'}",
                f"- Suggestion: {result.retry_guidance.suggestion}",
                ""
            ])
        
        parts.append("=== USE THIS FEEDBACK TO IMPROVE YOUR TEST ===")
        
        return "\n".join(parts)
    
    def get_summary(self) -> dict:
        """Get summary statistics of all evaluations."""
        if not self.evaluation_history:
            return {"total": 0, "success_rate": 0.0}
        
        total = len(self.evaluation_history)
        successes = sum(1 for r in self.evaluation_history if r.is_bug_revealing)
        
        category_counts = {}
        for r in self.evaluation_history:
            cat = r.failure_category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "total": total,
            "successes": successes,
            "success_rate": successes / total,
            "categories": category_counts,
            "avg_quality_score": sum(r.test_quality_score for r in self.evaluation_history) / total,
        }
