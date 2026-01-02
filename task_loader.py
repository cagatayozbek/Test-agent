"""Task context loader for evaluation tasks.

This module provides utilities for loading source code, test code, and
metadata for evaluation tasks. It constructs TaskContext objects that
can be injected into agent prompts.

Supports two task formats:
    - V1 (legacy): source_code.py + test_code.py
    - V2 (test generation): buggy/source.py + fixed/source.py

Classes:
    TaskContext: Container for task source code, tests, and metadata

Functions:
    load_task_context: Load TaskContext from evaluation/tasks/<task_id>/
    load_task_context_v2: Load TaskContextV2 for test generation tasks

Expected Directory Structures:

    V1 (bug detection):
        evaluation/tasks/<task_id>/
        ├── source_code.py    # Code under test
        ├── test_code.py      # Test file to run
        └── metadata.json     # Task metadata (optional)

    V2 (test generation):
        evaluation/tasks_v2/<task_id>/
        ├── buggy/
        │   └── source.py     # Buggy version
        ├── fixed/
        │   └── source.py     # Fixed version
        └── metadata.json     # Task metadata with bug_description

Example:
    >>> from task_loader import load_task_context, load_task_context_v2
    >>> context = load_task_context(Path("."), "misleading_coverage")
    >>> context_v2 = load_task_context_v2(Path("."), "boundary_bug")
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TaskContext:
    """Container for evaluation task context.
    
    Holds source code, test code, and metadata for a single evaluation task.
    Provides methods to format the context for LLM prompt injection.
    
    Attributes:
        task_id: Unique identifier for the task (e.g., "misleading_coverage")
        code_content: Source code from source_code.py
        test_content: Test code from test_code.py
        metadata: Parsed metadata.json contents (may be empty dict)
    
    Example:
        >>> context = TaskContext(
        ...     task_id="my_task",
        ...     code_content="def foo(): return 42",
        ...     test_content="def test_foo(): assert foo() == 42",
        ...     metadata={"expected_bug": "off-by-one"}
        ... )
        >>> prompt = context.to_prompt_context()
    """
    task_id: str
    code_content: str
    test_content: str
    metadata: dict
    
    def to_prompt_context(self) -> str:
        """Format task context for LLM prompt injection.
        
        Creates a structured string containing the task ID, source code,
        and test code, suitable for including in an agent's user message.
        
        Returns:
            str: Formatted context string with section markers
        
        Example:
            >>> context = load_task_context(Path("."), "my_task")
            >>> prompt = context.to_prompt_context()
            >>> # prompt contains:
            >>> # === TASK CONTEXT ===
            >>> # Task: my_task
            >>> # --- source_code.py ---
            >>> # ...
        """
        lines = [
            "=== TASK CONTEXT ===",
            f"Task: {self.task_id}",
            "",
            "--- source_code.py ---",
            self.code_content,
            "",
            "--- test_code.py ---",
            self.test_content,
            "",
            "=== END CONTEXT ===",
            "",
            "Analyze the code and tests above. Identify any bugs, missing test coverage, or potential issues.",
        ]
        return "\n".join(lines)


def load_task_context(base_dir: Path, task_id: str) -> Optional[TaskContext]:
    """Load task context from evaluation/tasks/<task_id>/.
    
    Reads source_code.py, test_code.py, and metadata.json from the task
    directory and constructs a TaskContext object.
    
    Args:
        base_dir: Project root directory containing evaluation/tasks/
        task_id: Name of the task directory to load
    
    Returns:
        TaskContext if task exists with required files, None otherwise.
        Returns None for dummy/legacy tasks without proper structure.
    
    Example:
        >>> context = load_task_context(Path("."), "misleading_coverage")
        >>> if context:
        ...     print(f"Loaded task: {context.task_id}")
        ...     print(f"Code: {len(context.code_content)} chars")
    """
    task_dir = base_dir / "evaluation" / "tasks" / task_id
    
    if not task_dir.exists():
        # Dummy task or legacy task - no context
        return None
    
    code_path = task_dir / "source_code.py"
    test_path = task_dir / "test_code.py"
    metadata_path = task_dir / "metadata.json"
    
    if not code_path.exists() or not test_path.exists():
        return None
    
    code_content = code_path.read_text(encoding="utf-8")
    test_content = test_path.read_text(encoding="utf-8")
    
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    
    return TaskContext(
        task_id=task_id,
        code_content=code_content,
        test_content=test_content,
        metadata=metadata,
    )


@dataclass
class TaskContextV2:
    """Container for test generation task context (V2 format).
    
    Holds buggy and fixed versions of source code for bug-revealing test
    generation tasks. The agent sees only the buggy code; fixed code is
    used for validation.
    
    Attributes:
        task_id: Unique identifier for the task
        buggy_code: Source code with bug (shown to agent)
        fixed_code: Source code without bug (for validation only)
        metadata: Parsed metadata.json with bug_description
        buggy_path: Path to buggy/source.py for test execution
        fixed_path: Path to fixed/source.py for test execution
    
    Example:
        >>> context = TaskContextV2(
        ...     task_id="boundary_bug",
        ...     buggy_code="def foo(x): return x > 100",  # Bug: should be >=
        ...     fixed_code="def foo(x): return x >= 100",
        ...     metadata={"bug_description": "Off-by-one in threshold check"},
        ...     buggy_path=Path("evaluation/tasks_v2/boundary_bug/buggy"),
        ...     fixed_path=Path("evaluation/tasks_v2/boundary_bug/fixed"),
        ... )
    """
    task_id: str
    buggy_code: str
    fixed_code: str
    metadata: dict
    buggy_path: Path
    fixed_path: Path
    
    def to_prompt_context(self) -> str:
        """Format task context for LLM prompt (shows only buggy code).
        
        Creates a structured string containing only the buggy code.
        The fixed code is NOT shown to the agent - it's for validation only.
        
        Returns:
            str: Formatted context string with buggy code
        """
        bug_desc = self.metadata.get("bug_description", "Unknown bug")
        lines = [
            "=== TASK CONTEXT (Test Generation) ===",
            f"Task: {self.task_id}",
            f"Bug Description: {bug_desc}",
            "",
            "--- source.py (buggy version) ---",
            self.buggy_code,
            "",
            "=== END CONTEXT ===",
            "",
            "Write a pytest test that FAILS on this buggy code but PASSES on the fixed version.",
            "The test should specifically target the bug described above.",
        ]
        return "\n".join(lines)
    
    def get_bug_description(self) -> str:
        """Get human-readable bug description from metadata."""
        return self.metadata.get("bug_description", "No description available")


def load_task_context_v2(base_dir: Path, task_id: str) -> Optional[TaskContextV2]:
    """Load V2 task context from evaluation/tasks_v2/<task_id>/.
    
    Reads buggy/source.py, fixed/source.py, and metadata.json from the
    task directory for test generation tasks.
    
    Args:
        base_dir: Project root directory containing evaluation/tasks_v2/
        task_id: Name of the task directory to load
    
    Returns:
        TaskContextV2 if task exists with required files, None otherwise.
    
    Example:
        >>> context = load_task_context_v2(Path("."), "boundary_bug")
        >>> if context:
        ...     print(f"Bug: {context.get_bug_description()}")
    """
    task_dir = base_dir / "evaluation" / "tasks_v2" / task_id
    
    if not task_dir.exists():
        return None
    
    buggy_path = task_dir / "buggy" / "source.py"
    fixed_path = task_dir / "fixed" / "source.py"
    metadata_path = task_dir / "metadata.json"
    
    if not buggy_path.exists() or not fixed_path.exists():
        return None
    
    buggy_code = buggy_path.read_text(encoding="utf-8")
    fixed_code = fixed_path.read_text(encoding="utf-8")
    
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    
    return TaskContextV2(
        task_id=task_id,
        buggy_code=buggy_code,
        fixed_code=fixed_code,
        metadata=metadata,
        buggy_path=task_dir / "buggy",
        fixed_path=task_dir / "fixed",
    )


def run_test_on_both_versions(
    test_file_path: Path,
    buggy_dir: Path,
    fixed_dir: Path,
    timeout: int = 60
) -> dict:
    """Run a test file against both buggy and fixed code versions.
    
    Executes the same test file in two directories (buggy and fixed)
    and returns the results for bug-revealing test validation.
    
    Args:
        test_file_path: Path to the generated test file
        buggy_dir: Directory containing buggy/source.py
        fixed_dir: Directory containing fixed/source.py
        timeout: Test execution timeout in seconds
    
    Returns:
        dict with keys:
            - buggy_result: pytest output for buggy code
            - fixed_result: pytest output for fixed code
            - buggy_failed: bool - True if test failed on buggy
            - fixed_passed: bool - True if test passed on fixed
            - is_bug_revealing: bool - True if buggy_failed AND fixed_passed
    
    Example:
        >>> result = run_test_on_both_versions(
        ...     Path("generated_tests/test_generated.py"),
        ...     Path("evaluation/tasks_v2/bug1/buggy"),
        ...     Path("evaluation/tasks_v2/bug1/fixed"),
        ... )
        >>> if result["is_bug_revealing"]:
        ...     print("Success! Test reveals the bug.")
    """
    import shutil
    import subprocess
    import tempfile
    
    def run_pytest(test_file: Path, source_dir: Path) -> dict:
        """Copy test to source dir and run pytest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Copy source files
            for f in source_dir.glob("*.py"):
                shutil.copy(f, tmpdir)
            
            # Copy test file
            shutil.copy(test_file, tmpdir / test_file.name)
            
            # Run pytest
            try:
                result = subprocess.run(
                    ["python3", "-m", "pytest", "-v", test_file.name],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "passed": result.returncode == 0,
                }
            except subprocess.TimeoutExpired:
                return {
                    "stdout": "",
                    "stderr": "Timeout",
                    "returncode": -1,
                    "passed": False,
                }
    
    # Run on buggy code
    buggy_result = run_pytest(test_file_path, buggy_dir)
    
    # Run on fixed code
    fixed_result = run_pytest(test_file_path, fixed_dir)
    
    # Determine if test is bug-revealing
    buggy_failed = not buggy_result["passed"]
    fixed_passed = fixed_result["passed"]
    is_bug_revealing = buggy_failed and fixed_passed
    
    return {
        "buggy_result": buggy_result,
        "fixed_result": fixed_result,
        "buggy_failed": buggy_failed,
        "fixed_passed": fixed_passed,
        "is_bug_revealing": is_bug_revealing,
    }
