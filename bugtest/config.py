"""Experiment configuration with Pydantic validation."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    model_id: str = "gemini-2.5-flash"
    api_key_env: str = "GOOGLE_API_KEY"
    temperature: float = 1.0
    max_output_tokens: int = 8192
    base_url: Optional[str] = None


class RetryConfig(BaseModel):
    max_attempts: int = 3
    test_timeout_seconds: int = 30


class TasksConfig(BaseModel):
    dir: str = "evaluation/tasks_v2"
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class ResultsConfig(BaseModel):
    dir: str = "results"


class ExperimentMeta(BaseModel):
    name: str = "analysis_vs_direct"
    runs_per_task: int = 10
    modes: list[str] = ["baseline", "agentic", "adaptive"]
    concurrency: int = 1


class Config(BaseModel):
    experiment: ExperimentMeta = Field(default_factory=ExperimentMeta)
    model: ModelConfig = Field(default_factory=ModelConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    tasks: TasksConfig = Field(default_factory=TasksConfig)
    results: ResultsConfig = Field(default_factory=ResultsConfig)

    def get_api_key(self) -> str:
        key = os.environ.get(self.model.api_key_env, "")
        if not key:
            raise EnvironmentError(f"Set {self.model.api_key_env} environment variable")
        return key


def load_config(path: Path) -> Config:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config.model_validate(data)
