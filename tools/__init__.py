"""Blind tool functions for agent investigation.

This module provides "blind" tools that return raw data without any interpretation,
heuristics, or analysis. The tools are designed to be used by LLM agents for
code investigation tasks.

Design Principles:
    - No interpretation: Tools return raw output without commentary
    - No heuristics: No built-in logic to guide analysis
    - Soft errors: Return error strings instead of raising exceptions
    - Path flexibility: Accept both Path objects and strings

Available Tools:
    - run_tests: Execute pytest and return stdout/stderr/returncode
    - read_file: Read entire file content as text
    - read_file_window: Read specific line range from file
    - list_files: List all files recursively in directory
    - log_event: Passthrough for logging events

Example:
    >>> from tools import run_tests, read_file
    >>> result = run_tests(cwd=Path("./my_project"))
    >>> content = read_file(Path("./source.py"))
"""

from pathlib import Path
import subprocess
from typing import Any


def run_tests(command: list[str] | None = None, cwd: Path | None = None) -> dict[str, Any]:
    """Execute a test command and capture raw output.
    
    Runs the specified command (or pytest by default) in a subprocess and
    returns the raw stdout, stderr, and return code without any interpretation.
    
    Args:
        command: Shell command as list of strings. If None, defaults to
            ["python3", "-m", "pytest", "-v"] for pytest execution.
        cwd: Working directory for command execution. If None, uses current
            directory.
    
    Returns:
        dict: Raw output with keys:
            - stdout (str): Standard output from command
            - stderr (str): Standard error from command  
            - returncode (int): Exit code (0 = success, non-zero = failure)
    
    Examples:
        >>> # Run default pytest
        >>> result = run_tests()
        >>> result["returncode"]  # 0 if tests pass
        0
        
        >>> # Run custom command
        >>> result = run_tests(command=["python", "-m", "unittest"])
        
        >>> # Run in specific directory
        >>> result = run_tests(cwd=Path("./tests"))
    
    Note:
        - Timeout is 60 seconds
        - Returns error dict on timeout or command not found
        - No analysis of test results - agents must interpret output
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
    """Read entire file content as UTF-8 text.
    
    Reads and returns the complete content of a file. Returns an error
    string (not exception) if the file cannot be read.
    
    Args:
        path: Path object pointing to the file to read.
    
    Returns:
        str: File content as text, or error string starting with "ERROR:"
            if file not found or cannot be read.
    
    Examples:
        >>> content = read_file(Path("./source_code.py"))
        >>> if not content.startswith("ERROR:"):
        ...     print(f"File has {len(content)} characters")
        
        >>> # Non-existent file returns error string
        >>> read_file(Path("./nonexistent.py"))
        'ERROR: file not found: nonexistent.py'
    
    Note:
        - Uses UTF-8 encoding
        - Returns soft error strings for missing files (no exceptions)
        - No caching - reads file fresh each call
    """
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"ERROR: file not found: {path}"
    except OSError as exc:
        return f"ERROR: unable to read {path}: {exc}"


def read_file_window(path: Path, start: int, end: int) -> str:
    """Read specific line range from a file.
    
    Reads lines from start to end (inclusive, 1-indexed) and joins them
    with newlines. Useful for examining specific code sections without
    loading entire large files.
    
    Args:
        path: Path object pointing to the file to read.
        start: Starting line number (1-indexed, inclusive).
        end: Ending line number (1-indexed, inclusive).
    
    Returns:
        str: Joined lines from the specified range, or error string
            starting with "ERROR:" if file cannot be read.
    
    Examples:
        >>> # Read lines 10-20 from a file
        >>> snippet = read_file_window(Path("./code.py"), 10, 20)
        
        >>> # Read single line
        >>> line_5 = read_file_window(Path("./code.py"), 5, 5)
        
        >>> # Out of range returns empty or partial content
        >>> read_file_window(Path("./code.py"), 1000, 1010)
        ''
    
    Note:
        - Line numbers are 1-indexed (first line is 1)
        - Both start and end are inclusive
        - Returns empty string for out-of-range requests
        - Returns soft error strings for missing files
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return f"ERROR: file not found: {path}"
    except OSError as exc:
        return f"ERROR: unable to read {path}: {exc}"

    return "\n".join(lines[start - 1 : end])


def list_files(root: Path | None = None) -> list[str]:
    """List all files recursively in a directory.
    
    Walks the directory tree starting from root and returns a sorted
    list of all file paths (relative to root). Useful for discovering
    project structure.
    
    Args:
        root: Starting directory for recursive listing. If None,
            defaults to current directory (".").
    
    Returns:
        list[str]: Sorted list of relative file paths as strings.
            Includes all files including hidden files and subdirectories.
    
    Examples:
        >>> # List all files in current directory
        >>> files = list_files()
        >>> print(files[:3])
        ['config.py', 'main.py', 'tests/test_main.py']
        
        >>> # List files in specific directory
        >>> files = list_files(Path("./src"))
        >>> 'src/utils.py' in files
        True
    
    Note:
        - Returns paths relative to root
        - Includes hidden files (starting with .)
        - Results are sorted alphabetically
        - Returns empty list for non-existent directories
    """
    base = root or Path(".")
    return sorted(str(p) for p in base.rglob("*"))


def log_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Passthrough function for logging events.
    
    Returns the input payload unchanged. Used by agents to record
    observations, findings, and conclusions during investigation.
    The actual logging is handled by the instrumented wrapper.
    
    Args:
        payload: Dictionary containing event data to log. Typically
            includes a "message" key with the observation text.
    
    Returns:
        dict: The same payload dictionary, unchanged.
    
    Examples:
        >>> log_event({"message": "Found potential bug on line 23"})
        {'message': 'Found potential bug on line 23'}
        
        >>> log_event({"message": "ROOT CAUSE: Off-by-one error"})
        {'message': 'ROOT CAUSE: Off-by-one error'}
    
    Note:
        - This is a passthrough - actual logging happens in InstrumentedTools
        - Commonly used with "message" key but accepts any dict structure
        - Used to signal investigation completion when agent finds root cause
    """
    return payload


def write_test_file(
    output_dir: Path,
    filename: str,
    content: str,
    attempt: int = 1
) -> dict[str, Any]:
    """Write a generated test file to the output directory.
    
    Creates or overwrites a test file in the specified directory. Supports
    test isolation by allowing attempt-numbered filenames for audit trail.
    
    Args:
        output_dir: Directory path where test file will be written.
            Created if it doesn't exist.
        filename: Name of the test file (e.g., "test_generated.py").
            If attempt > 1, attempt number is appended.
        content: Complete Python test code to write.
        attempt: Attempt number for isolation (default=1). If > 1,
            filename becomes "test_generated_attempt_2.py" etc.
    
    Returns:
        dict: Result with keys:
            - success (bool): Whether write succeeded
            - path (str): Absolute path to written file
            - error (str | None): Error message if failed
    
    Examples:
        >>> result = write_test_file(
        ...     output_dir=Path("./generated_tests"),
        ...     filename="test_generated.py",
        ...     content="import pytest\n\ndef test_bug(): ..."
        ... )
        >>> result["success"]
        True
        
        >>> # With attempt number for audit trail
        >>> result = write_test_file(
        ...     output_dir=Path("./generated_tests"),
        ...     filename="test_generated.py",
        ...     content="...",
        ...     attempt=2
        ... )
        >>> result["path"].endswith("test_generated_attempt_2.py")
        True
    
    Note:
        - Creates output_dir if it doesn't exist
        - Overwrites existing files with same name
        - Uses UTF-8 encoding
        - Returns soft error dict on failure (no exceptions)
    """
    try:
        # Create directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Modify filename for attempts > 1
        if attempt > 1:
            base, ext = filename.rsplit(".", 1) if "." in filename else (filename, "py")
            filename = f"{base}_attempt_{attempt}.{ext}"
        
        file_path = output_dir / filename
        file_path.write_text(content, encoding="utf-8")
        
        return {
            "success": True,
            "path": str(file_path.absolute()),
            "error": None
        }
    except OSError as exc:
        return {
            "success": False,
            "path": "",
            "error": f"Failed to write test file: {exc}"
        }
