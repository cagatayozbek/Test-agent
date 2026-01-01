from typing import Literal

from pydantic import BaseModel


class SemanticHypothesis(BaseModel):
    hypothesis: str
    confidence_level: Literal["LOW", "MEDIUM", "HIGH"]
    assumptions: list[str]
    evidence: list[str]
    what_might_be_missing: str
    next_question: str


class EvaluationResult(BaseModel):
    behavior: Literal["reasonable", "confused", "overconfident"]
    failure_type: str
    commentary: str


class CriticResponse(BaseModel):
    """Extended evaluation response from Critic agent with detailed analysis."""
    behavior: Literal["reasonable", "confused", "overconfident"]
    failure_type: str
    commentary: str
    challenges: list[str]
    alternatives: list[str]
    missing_evidence: list[str]
    verdict: Literal["ACCEPT", "REVISE", "REJECT"]
    
    def to_evaluation_result(self) -> "EvaluationResult":
        """Convert to simplified EvaluationResult for summary."""
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
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LogEntry(BaseModel):
    timestamp: str
    agent: str
    role: str
    content: str
    tool_name: str | None = None
    duration_seconds: float | None = None
    token_usage: TokenUsage | None = None


class Summary(BaseModel):
    hypothesis: SemanticHypothesis
    evaluation: EvaluationResult
    model_id: str
    timestamp: str
    tool_call_count: int
