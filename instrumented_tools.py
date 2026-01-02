"""Instrumented tool wrappers with call counting.

This module provides wrapper classes around the blind tools from tools/__init__.py,
adding instrumentation for tracking tool usage metrics. Each tool call increments
a counter, enabling analysis of agent behavior and tool utilization patterns.

The wrappers also handle string-to-Path conversion, making them more flexible
for use with LLM outputs that typically return paths as strings.

Classes:
    ToolCounter: Simple counter for tracking total tool invocations
    InstrumentedTools: Wrapper class providing instrumented tool methods

Example:
    >>> counter = ToolCounter()
    >>> tools = InstrumentedTools(counter)
    >>> content = tools.read_file("./source.py")  # Counter increments
    >>> print(counter.count)  # 1
    >>> tools.list_files(".")  # Counter increments again
    >>> print(counter.count)  # 2
"""

from pathlib import Path
from typing import Any

from tools import list_files as _list_files
from tools import log_event as _log_event
from tools import read_file as _read_file
from tools import read_file_window as _read_file_window
from tools import run_tests as _run_tests
from tools import write_test_file as _write_test_file


class ToolCounter:
    """Thread-safe counter for tracking tool invocations.
    
    A simple counter class that tracks the total number of tool calls made
    during an agent session. Used for metrics collection and analysis.
    
    Attributes:
        count (int): Current count of tool invocations.
    
    Example:
        >>> counter = ToolCounter()
        >>> counter.count
        0
        >>> counter.increment()
        >>> counter.count
        1
    """
    
    def __init__(self) -> None:
        """Initialize counter to zero."""
        self.count = 0

    def increment(self) -> None:
        """Increment the counter by one.
        
        Called automatically by InstrumentedTools wrapper methods
        before each tool invocation.
        """
        self.count += 1


class InstrumentedTools:
    """Wrapper class providing instrumented tool methods with usage tracking.
    
    Wraps the blind tools from tools/__init__.py, adding:
    - Automatic call counting via ToolCounter
    - String-to-Path conversion for path arguments
    - Flexible argument handling (supports both 'root' and 'path' for list_files)
    
    This class is designed to be passed to CustomSession for agent use.
    
    Attributes:
        counter (ToolCounter): Shared counter instance for tracking calls.
    
    Example:
        >>> counter = ToolCounter()
        >>> tools = InstrumentedTools(counter)
        >>> 
        >>> # Read a file (counter increments)
        >>> content = tools.read_file("source_code.py")
        >>> 
        >>> # Run tests (counter increments)
        >>> result = tools.run_tests(cwd="./tests")
        >>> 
        >>> # Check total tool calls
        >>> print(f"Total calls: {counter.count}")
    """
    
    def __init__(self, counter: ToolCounter) -> None:
        """Initialize with a shared counter instance.
        
        Args:
            counter: ToolCounter instance for tracking invocations.
                Multiple InstrumentedTools instances can share a counter.
        """
        self.counter = counter

    def log_event_wrapped(self, **kwargs: Any) -> dict[str, Any]:
        """Log an event payload with flexible keyword arguments.
        
        Accepts any keyword arguments and passes them as a dict to log_event.
        Useful when LLM generates varied argument structures.
        
        Args:
            **kwargs: Arbitrary keyword arguments to include in log payload.
        
        Returns:
            dict: The kwargs as a dictionary.
        
        Example:
            >>> tools.log_event_wrapped(message="Found bug", severity="high")
            {'message': 'Found bug', 'severity': 'high'}
        """
        self.counter.increment()
        return _log_event(kwargs)

    def run_tests(self, command: list[str] | None = None, cwd: Path | str | None = None) -> dict[str, Any]:
        """Execute tests with automatic path conversion.
        
        Wraps tools.run_tests with counter instrumentation and
        automatic string-to-Path conversion for cwd argument.
        
        Args:
            command: Test command as list of strings. Defaults to pytest.
            cwd: Working directory as Path or string. Auto-converted to Path.
        
        Returns:
            dict: Raw test output with stdout, stderr, returncode.
        
        Example:
            >>> result = tools.run_tests()  # Default pytest
            >>> result = tools.run_tests(cwd="./my_project")  # String path OK
        """
        self.counter.increment()
        if isinstance(cwd, str):
            cwd = Path(cwd)
        return _run_tests(command=command, cwd=cwd)

    def read_file(self, path: Path | str) -> str:
        """Read file content with automatic path conversion.
        
        Wraps tools.read_file with counter instrumentation and
        automatic string-to-Path conversion.
        
        Args:
            path: File path as Path object or string.
        
        Returns:
            str: File content or error string.
        
        Example:
            >>> content = tools.read_file("source_code.py")  # String OK
            >>> content = tools.read_file(Path("source_code.py"))  # Path OK
        """
        self.counter.increment()
        if isinstance(path, str):
            path = Path(path)
        return _read_file(path)

    def read_file_window(self, path: Path | str, start: int, end: int) -> str:
        """Read file line range with automatic path conversion.
        
        Wraps tools.read_file_window with counter instrumentation and
        automatic string-to-Path conversion.
        
        Args:
            path: File path as Path object or string.
            start: Starting line number (1-indexed, inclusive).
            end: Ending line number (1-indexed, inclusive).
        
        Returns:
            str: Joined lines from range or error string.
        
        Example:
            >>> snippet = tools.read_file_window("code.py", 10, 25)
        """
        self.counter.increment()
        if isinstance(path, str):
            path = Path(path)
        return _read_file_window(path, start, end)

    def list_files(self, root: Path | str | None = None, path: Path | str | None = None) -> list[str]:
        """List files recursively with flexible argument names.
        
        Wraps tools.list_files with counter instrumentation, path conversion,
        and support for both 'root' and 'path' argument names (LLMs sometimes
        use either).
        
        Args:
            root: Directory path (legacy parameter name).
            path: Directory path (LLM-friendly parameter name).
                If both provided, 'path' takes precedence.
        
        Returns:
            list[str]: Sorted list of file paths.
        
        Example:
            >>> files = tools.list_files(root="./src")  # Using 'root'
            >>> files = tools.list_files(path="./src")  # Using 'path'
        """
        self.counter.increment()
        # Support both 'root' and 'path' argument names
        dir_path = path or root
        if isinstance(dir_path, str):
            dir_path = Path(dir_path)
        return _list_files(dir_path)

    def log_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Log an event with explicit payload dict.
        
        Wraps tools.log_event with counter instrumentation.
        
        Args:
            payload: Dictionary containing event data.
        
        Returns:
            dict: The payload unchanged.
        
        Example:
            >>> tools.log_event({"message": "ROOT CAUSE: Bug on line 23"})
        """
        self.counter.increment()
        return _log_event(payload)

    def write_test_file(
        self,
        output_dir: Path | str,
        filename: str,
        content: str,
        attempt: int = 1
    ) -> dict[str, Any]:
        """Write a generated test file with automatic path conversion.
        
        Wraps tools.write_test_file with counter instrumentation and
        automatic string-to-Path conversion for output_dir.
        
        Args:
            output_dir: Directory path as Path or string.
            filename: Name of the test file.
            content: Complete Python test code.
            attempt: Attempt number for isolation (default=1).
        
        Returns:
            dict: Result with success, path, and error keys.
        
        Example:
            >>> result = tools.write_test_file(
            ...     "./generated_tests",
            ...     "test_generated.py",
            ...     "def test_bug(): assert False"
            ... )
        """
        self.counter.increment()
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)
        return _write_test_file(output_dir, filename, content, attempt)
