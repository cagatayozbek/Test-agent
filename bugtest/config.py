"""Experiment configuration with Pydantic validation."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    model_id: str = "sonnet"
    api_key_env: str = "CLAUDE_CODE_KEY"
    temperature: float = 0.7
    max_output_tokens: int = 4096


class RetryConfig(BaseModel):
    max_attempts: int = 3
    test_timeout_seconds: int = 30


class TasksConfig(BaseModel):
    dir: str = "evaluation/tasks_v2_bugsinpy"
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class ResultsConfig(BaseModel):
    dir: str = "results"


class ExperimentMeta(BaseModel):
    name: str = "bugsinpy_pilot"
    runs_per_task: int = 3
    modes: list[str] = ["baseline", "adaptive", "deep"]
    experiment_id: Optional[str] = None


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
