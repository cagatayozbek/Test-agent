from pathlib import Path
from typing import Any

from tools import list_files as _list_files
from tools import log_event as _log_event
from tools import read_file as _read_file
from tools import read_file_window as _read_file_window
from tools import run_tests as _run_tests


class ToolCounter:
    def __init__(self) -> None:
        self.count = 0

    def increment(self) -> None:
        self.count += 1


class InstrumentedTools:
    def __init__(self, counter: ToolCounter) -> None:
        self.counter = counter

    def log_event_wrapped(self, **kwargs: Any) -> dict[str, Any]:
        """Log a payload dictionary as-is."""
        self.counter.increment()
        return _log_event(kwargs)

    def run_tests(self, command: list[str] | None = None, cwd: Path | str | None = None) -> dict[str, Any]:
        """Run a test command and return raw stdout/stderr/returncode."""
        self.counter.increment()
        if isinstance(cwd, str):
            cwd = Path(cwd)
        return _run_tests(command=command, cwd=cwd)

    def read_file(self, path: Path | str) -> str:
        """Read entire file content as text."""
        self.counter.increment()
        if isinstance(path, str):
            path = Path(path)
        return _read_file(path)

    def read_file_window(self, path: Path | str, start: int, end: int) -> str:
        """Read file lines in inclusive window [start, end] joined by newline."""
        self.counter.increment()
        if isinstance(path, str):
            path = Path(path)
        return _read_file_window(path, start, end)

    def list_files(self, root: Path | str | None = None, path: Path | str | None = None) -> list[str]:
        """List all files recursively starting at root (or current directory).
        
        Args:
            root: Root directory to list (legacy parameter name)
            path: Root directory to list (LLM-friendly parameter name)
        """
        self.counter.increment()
        # Support both 'root' and 'path' argument names
        dir_path = path or root
        if isinstance(dir_path, str):
            dir_path = Path(dir_path)
        return _list_files(dir_path)

    def log_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the payload unchanged for logging purposes."""
        self.counter.increment()
        return _log_event(payload)
