from pathlib import Path
import subprocess
from typing import Any


def run_tests(command: list[str] | None = None, cwd: Path | None = None) -> dict[str, Any]:
    """Run a test command and return raw stdout/stderr/returncode.
    
    If command is None, defaults to pytest.
    """
    if command is None:
        command = ["python3", "-m", "pytest", "-v"]
    
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        return {
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "ERROR: test command timed out (60s)",
            "returncode": -1,
        }
    except FileNotFoundError as exc:
        return {
            "stdout": "",
            "stderr": f"ERROR: command not found: {exc}",
            "returncode": -1,
        }


def read_file(path: Path) -> str:
    """Read entire file content as text."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"ERROR: file not found: {path}"
    except OSError as exc:
        return f"ERROR: unable to read {path}: {exc}"


def read_file_window(path: Path, start: int, end: int) -> str:
    """Read file lines in the inclusive window [start, end] and join with newlines."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return f"ERROR: file not found: {path}"
    except OSError as exc:
        return f"ERROR: unable to read {path}: {exc}"

    return "\n".join(lines[start - 1 : end])


def list_files(root: Path | None = None) -> list[str]:
    """List all files recursively starting at root (or current directory)."""
    base = root or Path(".")
    return sorted(str(p) for p in base.rglob("*"))


def log_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the payload unchanged for logging purposes."""
    return payload
