from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class TestGenerationConfig(BaseModel):
    """Configuration for test generation mode."""
    max_retry_attempts: int = 3
    test_timeout_seconds: int = 60


class Config(BaseModel):
    model_id: str
    max_turns: int
    timeout_seconds: int
    test_generation: Optional[TestGenerationConfig] = None


def load_config(path: Path) -> Config:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    return Config.model_validate(data)
