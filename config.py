from pathlib import Path

import yaml
from pydantic import BaseModel


class Config(BaseModel):
    model_id: str
    max_turns: int
    timeout_seconds: int


def load_config(path: Path) -> Config:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    return Config.model_validate(data)
