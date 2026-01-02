"""Utility functions for logging and summary generation.

This module provides helper functions used throughout the agent session
for timestamp generation, log entry construction, and summary writing.

Functions:
    iso8601_utc_timestamp: Generate current UTC timestamp in ISO 8601 format
    build_log_entry: Construct a LogEntry with current timestamp
    write_summary: Write a Summary object to a JSON file

Example:
    >>> from runner import iso8601_utc_timestamp, build_log_entry, write_summary
    >>> timestamp = iso8601_utc_timestamp()  # "2026-01-01T12:00:00Z"
    >>> entry = build_log_entry(agent="analysis", role="assistant", content="...")
    >>> write_summary(Path("./output/summary.json"), summary)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from schemas import LogEntry, Summary, TokenUsage


def iso8601_utc_timestamp() -> str:
    """Generate current UTC timestamp in ISO 8601 format.
    
    Returns:
        str: Timestamp string like "2026-01-01T12:00:00Z"
    
    Example:
        >>> ts = iso8601_utc_timestamp()
        >>> print(ts)  # "2026-01-01T15:30:45Z"
    
    Note:
        - Microseconds are truncated for cleaner output
        - Uses "Z" suffix instead of "+00:00" for brevity
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_log_entry(
    agent: str,
    role: str,
    content: str,
    tool_name: str | None = None,
    duration_seconds: float | None = None,
    token_usage: TokenUsage | None = None,
) -> LogEntry:
    """Construct a LogEntry with auto-generated timestamp.
    
    Factory function for creating LogEntry objects with the current
    UTC timestamp automatically populated.
    
    Args:
        agent: Name of the agent (e.g., "planner", "analysis")
        role: Role in conversation ("system", "assistant", "error")
        content: Text content of the log entry
        tool_name: Optional name of tool if this logs a tool call
        duration_seconds: Optional duration of the operation
        token_usage: Optional TokenUsage with prompt/completion counts
    
    Returns:
        LogEntry: Populated entry ready for emission
    
    Example:
        >>> entry = build_log_entry(
        ...     agent="executor",
        ...     role="assistant",
        ...     content='{"tool": "read_file", ...}',
        ...     tool_name="read_file",
        ...     duration_seconds=0.5
        ... )
    """
    return LogEntry(
        timestamp=iso8601_utc_timestamp(),
        agent=agent,
        role=role,
        content=content,
        tool_name=tool_name,
        duration_seconds=duration_seconds,
        token_usage=token_usage,
    )


def write_summary(path: Path, summary: Summary) -> None:
    """Write a Summary object to a JSON file.
    
    Serializes the Summary to pretty-printed JSON and writes to the
    specified path. Creates parent directories if needed.
    
    Args:
        path: Destination path for the summary JSON file
        summary: Summary object to serialize
    
    Side Effects:
        - Creates parent directories if they don't exist
        - Overwrites existing file at path
    
    Example:
        >>> write_summary(Path("./runs/task1/run1/summary.json"), summary)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = summary.model_dump()
    text = json.dumps(payload, ensure_ascii=True, indent=2)
    path.write_text(text, encoding="utf-8")
