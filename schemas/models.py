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
