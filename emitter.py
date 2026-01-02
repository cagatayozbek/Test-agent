"""Stateless JSONL log emitter for agent session logging.

This module provides a simple, stateless function for appending log entries
to JSONL (JSON Lines) files. Each entry is serialized and written as a
single line, enabling efficient streaming and line-by-line parsing.

Design Principles:
    - Stateless: No global state or file handles kept open
    - Atomic: Each emit is a complete append operation
    - Clean: Excludes unset and None fields from output

Functions:
    emit_log_entry: Append a LogEntry to a JSONL file

Example:
    >>> from emitter import emit_log_entry
    >>> from schemas import LogEntry
    >>> entry = LogEntry(
    ...     timestamp="2026-01-01T12:00:00Z",
    ...     agent="analysis",
    ...     role="assistant",
    ...     content="Found bug on line 23"
    ... )
    >>> emit_log_entry(Path("./logs/session.jsonl"), entry)
"""

import json
from pathlib import Path

from schemas import LogEntry


def emit_log_entry(path: Path, entry: LogEntry) -> None:
    """Append a log entry to a JSONL file.
    
    Serializes the LogEntry to JSON and appends it as a single line to
    the specified file. Creates parent directories if needed.
    
    Args:
        path: Path to the JSONL log file (created if doesn't exist)
        entry: LogEntry object to serialize and append
    
    Side Effects:
        - Creates parent directories if they don't exist
        - Appends one line to the file
    
    Example:
        >>> emit_log_entry(
        ...     Path("./logs/raw_logs.jsonl"),
        ...     LogEntry(timestamp="...", agent="planner", role="assistant", content="...")
        ... )
    
    Note:
        - Uses exclude_unset=True and exclude_none=True for clean output
        - Uses ensure_ascii=True for portable JSON
        - Each call opens and closes the file (stateless)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = entry.model_dump(exclude_unset=True, exclude_none=True)
    line = json.dumps(serialized, ensure_ascii=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
