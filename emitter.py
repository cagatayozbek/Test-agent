import json
from pathlib import Path

from schemas import LogEntry


def emit_log_entry(path: Path, entry: LogEntry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = entry.model_dump(exclude_unset=True, exclude_none=True)
    line = json.dumps(serialized, ensure_ascii=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
