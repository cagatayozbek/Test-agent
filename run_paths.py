from pathlib import Path
from dataclasses import dataclass


@dataclass
class RunPaths:
    root: Path
    raw_logs: Path
    summary: Path
    tool_outputs: Path


def build_run_paths(base: Path, task: str, run_id: str) -> RunPaths:
    root = base / "runs" / task / run_id
    return RunPaths(
        root=root,
        raw_logs=root / "raw_logs.jsonl",
        summary=root / "summary.json",
        tool_outputs=root / "tool_outputs",
    )
