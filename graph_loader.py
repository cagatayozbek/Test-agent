from pathlib import Path

import yaml
from pydantic import BaseModel


class Mode(BaseModel):
    entry: str
    agents: list[str]
    edges: list[tuple[str, str]]


class AgentGraph(BaseModel):
    version: int
    modes: dict[str, Mode]


def load_agent_graph(path: Path) -> AgentGraph:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    return AgentGraph.model_validate(data)
