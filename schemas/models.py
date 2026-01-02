"""Pydantic models for structured agent outputs and logging.

This module defines the data models used throughout the agent system for:
- Structured LLM outputs (SemanticHypothesis, CriticResponse)
- Evaluation results (EvaluationResult)
- Logging and metrics (LogEntry, TokenUsage)
- Session summaries (Summary)

All models use Pydantic for validation and serialization, enabling:
- JSON schema generation for Gemini's response_schema parameter
- Automatic validation of LLM outputs
- Clean JSON serialization for logs and summaries

Example:
    >>> from schemas import SemanticHypothesis, Summary
    >>> hypothesis = SemanticHypothesis(
    ...     hypothesis="Bug on line 23",
    ...     confidence_level="HIGH",
    ...     assumptions=["Threshold is 100"],
    ...     evidence=["Line 23 uses > instead of >="],
    ...     what_might_be_missing="Business requirements",
    ...     next_question="Check requirements doc"
    ... )
"""

from typing import Literal

from pydantic import BaseModel


class SemanticHypothesis(BaseModel):
    """Structured hypothesis output from the Analysis agent.
    
    Captures the agent's theory about a bug along with supporting evidence,
    assumptions, and uncertainty indicators.
    
    Attributes:
        hypothesis: Main theory about the bug (specific with line numbers)
        confidence_level: LOW, MEDIUM, or HIGH based on evidence strength
        assumptions: List of assumptions underlying the hypothesis
        evidence: List of concrete evidence from code/tests
        what_might_be_missing: Gaps in analysis, uncertainties
        next_question: What investigation would confirm/refute hypothesis
    
    Example:
        >>> hyp = SemanticHypothesis(
        ...     hypothesis="Off-by-one error in calculate_discount() line 23",
        ...     confidence_level="HIGH",
        ...     assumptions=["VIP threshold is 100 points"],
        ...     evidence=["Line 23: points > 100 should be points >= 100"],
        ...     what_might_be_missing="Business requirements",
        ...     next_question="Is >= the intended behavior?"
        ... )
    """
    hypothesis: str
    confidence_level: Literal["LOW", "MEDIUM", "HIGH"]
    assumptions: list[str]
    evidence: list[str]
    what_might_be_missing: str
    next_question: str


class EvaluationResult(BaseModel):
    """Simplified evaluation result for summaries.
    
    Core evaluation fields extracted from CriticResponse for inclusion
    in session summaries.
    
    Attributes:
        behavior: "reasonable" (solid), "confused" (unclear), or "overconfident"
        failure_type: Specific failure type (e.g., "missing_edge_case") or empty
        commentary: Detailed evaluation prose
    """
    behavior: Literal["reasonable", "confused", "overconfident"]
    failure_type: str
    commentary: str


class CriticResponse(BaseModel):
    """Extended evaluation response from Critic agent.
    
    Full structured output from the Critic agent including challenges,
    alternatives, and verdict. Can be converted to simplified EvaluationResult.
    
    Attributes:
        behavior: "reasonable", "confused", or "overconfident"
        failure_type: Specific failure type if any, empty string if none
        commentary: Detailed prose explaining the evaluation
        challenges: List of problems with the analysis
        alternatives: List of other possible explanations
        missing_evidence: List of additional checks that would help
        verdict: ACCEPT (solid), REVISE (needs work), or REJECT (flawed)
    """
    behavior: Literal["reasonable", "confused", "overconfident"]
    failure_type: str
    commentary: str
    challenges: list[str]
    alternatives: list[str]
    missing_evidence: list[str]
    verdict: Literal["ACCEPT", "REVISE", "REJECT"]
    
    def to_evaluation_result(self) -> "EvaluationResult":
        """Convert to simplified EvaluationResult for summary.
        
        Combines all evaluation fields into a comprehensive commentary string
        while preserving the core behavior and failure_type fields.
        
        Returns:
            EvaluationResult: Simplified version with combined commentary
        """
        # Build comprehensive commentary from all fields
        commentary_parts = [self.commentary]
        if self.challenges:
            commentary_parts.append(f"\nChallenges: {', '.join(self.challenges)}")
        if self.alternatives:
            commentary_parts.append(f"\nAlternatives: {', '.join(self.alternatives)}")
        if self.missing_evidence:
            commentary_parts.append(f"\nMissing Evidence: {', '.join(self.missing_evidence)}")
        commentary_parts.append(f"\nVerdict: {self.verdict}")
        
        return EvaluationResult(
            behavior=self.behavior,
            failure_type=self.failure_type,
            commentary="".join(commentary_parts),
        )


class TokenUsage(BaseModel):
    """Token usage metrics from an LLM call.
    
    Attributes:
        prompt_tokens: Tokens in the input prompt
        completion_tokens: Tokens in the generated response
        total_tokens: Sum of prompt and completion tokens
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LogEntry(BaseModel):
    """Single log entry for agent session logging.
    
    Captures one interaction in the agent pipeline, including agent output,
    tool calls, timing, and token usage.
    
    Attributes:
        timestamp: ISO 8601 UTC timestamp
        agent: Name of the agent (e.g., "planner", "executor")
        role: Role in conversation ("system", "assistant", "error")
        content: Text content of the entry
        tool_name: Name of tool if this logs a tool call (optional)
        duration_seconds: Duration of the operation (optional)
        token_usage: Token metrics if from LLM call (optional)
    """
    timestamp: str
    agent: str
    role: str
    content: str
    tool_name: str | None = None
    duration_seconds: float | None = None
    token_usage: TokenUsage | None = None


class Summary(BaseModel):
    """Session summary with hypothesis, evaluation, and metrics.
    
    Final output from a session run containing the structured hypothesis,
    evaluation results, and session metadata.
    
    Attributes:
        hypothesis: Structured analysis hypothesis
        evaluation: Critic's evaluation of the hypothesis
        model_id: LLM model identifier used
        timestamp: ISO 8601 timestamp of summary generation
        tool_call_count: Total number of tool invocations
    """
    hypothesis: SemanticHypothesis
    evaluation: EvaluationResult
    model_id: str
    timestamp: str
    tool_call_count: int


class TestGenerationResult(BaseModel):
    """Result of a single test generation attempt.
    
    Captures the outcome of running a generated test against
    both buggy and fixed code versions.
    
    Attributes:
        attempt: Attempt number (1-based)
        test_file: Path to generated test file
        buggy_failed: True if test failed on buggy code
        fixed_passed: True if test passed on fixed code
        is_bug_revealing: True if buggy_failed AND fixed_passed
        buggy_output: Pytest output from buggy run
        fixed_output: Pytest output from fixed run
    """
    attempt: int
    test_file: str
    buggy_failed: bool
    fixed_passed: bool
    is_bug_revealing: bool
    buggy_output: str = ""
    fixed_output: str = ""


class TestGenerationSummary(BaseModel):
    """Summary for test generation sessions.
    
    Extended summary including test generation specific metrics
    for bug-revealing test evaluation.
    
    Attributes:
        # Base fields (shared with Summary)
        hypothesis: Structured analysis hypothesis
        evaluation: Critic's evaluation
        model_id: LLM model identifier
        timestamp: ISO 8601 timestamp
        tool_call_count: Total tool invocations
        
        # Test generation specific fields
        task_id: Task identifier
        mode: "baseline" or "agentic"
        tests_generated: Number of test files written
        attempts_until_success: Attempts to get bug-revealing test (null if failed)
        buggy_failed: Final test failed on buggy code
        fixed_passed: Final test passed on fixed code
        is_bug_revealing: True if test reveals the bug
        overfitting_detected: True if test fails on both versions
        test_results: List of all attempt results
    """
    # Base fields
    hypothesis: SemanticHypothesis | None = None
    evaluation: EvaluationResult | None = None
    model_id: str
    timestamp: str
    tool_call_count: int
    
    # Test generation fields
    task_id: str
    mode: Literal["baseline", "agentic"]
    tests_generated: int = 0
    attempts_until_success: int | None = None
    buggy_failed: bool = False
    fixed_passed: bool = False
    is_bug_revealing: bool = False
    overfitting_detected: bool = False
    test_results: list[TestGenerationResult] = []
    
    def calculate_brtr(self) -> float:
        """Calculate Bug-Revealing Test Rate.
        
        Returns:
            float: 1.0 if bug-revealing, 0.0 otherwise
        """
        return 1.0 if self.is_bug_revealing else 0.0
