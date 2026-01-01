import json
from datetime import datetime, timezone
from pathlib import Path

from schemas import LogEntry, Summary, TokenUsage


def iso8601_utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_log_entry(
    agent: str,
    role: str,
    content: str,
    tool_name: str | None = None,
    duration_seconds: float | None = None,
    token_usage: TokenUsage | None = None,
) -> LogEntry:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = summary.model_dump()
    text = json.dumps(payload, ensure_ascii=True, indent=2)
    path.write_text(text, encoding="utf-8")
