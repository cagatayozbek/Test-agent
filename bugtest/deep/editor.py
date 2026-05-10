"""
DeepTest Editor — Git-backed safe file editing.

The key insight: JEP (Justified Edit Protocol) asks the LLM to
*explain* why an edit is safe. But LLMs can explain anything.
Git-backed editing *proves* it's safe by testing after every edit
and automatically reverting failures.

Mechanical safety > Semantic safety.
"""

from pathlib import Path
from typing import Optional

from bugtest.deep.types import EditResult, TestResult
from bugtest.deep.runner import TestRunner


class SafeEditor:
    """
    Edit files with automatic test validation and git-backed revert.

    Flow:
    1. Backup original file
    2. Apply edit
    3. Run tests
    4. If tests regress → revert automatically
    5. If tests pass or improve → keep edit
    """

    def __init__(self, workspace: str, test_runner: Optional[TestRunner] = None):
        self.workspace = workspace
        self.runner = test_runner or TestRunner(workspace)
        self._backups: dict[str, str] = {}  # path → original content

    def _clear_pycache(self) -> None:
        workspace_path = Path(self.workspace)
        for cache_dir in workspace_path.rglob("__pycache__"):
            if not cache_dir.is_dir():
                continue
            for cached_file in cache_dir.glob("*.pyc"):
                cached_file.unlink(missing_ok=True)

    @staticmethod
    def _failure_signature(result: TestResult) -> tuple:
        timeout = "timed out" in result.stderr.lower() or "timeout" in result.stderr.lower()
        syntax_error = result.exit_code not in (0, 1)
        failed_lines = tuple(
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith("FAILED ")
        )
        return (
            result.passed,
            result.exit_code,
            result.num_passed,
            result.num_failed,
            timeout,
            syntax_error,
            failed_lines,
            tuple(result.failure_messages),
        )

    @classmethod
    def _is_regression(cls, baseline: TestResult, current: TestResult) -> bool:
        if baseline.passed and not current.passed:
            return True
        if current.exit_code not in (0, 1):
            return True
        if current.num_failed > baseline.num_failed:
            return True
        if current.num_passed < baseline.num_passed and current.num_failed >= baseline.num_failed:
            return True
        if current.num_failed == baseline.num_failed and cls._failure_signature(current) != cls._failure_signature(baseline):
            return True
        return False

    def read_file(self, rel_path: str) -> str:
        """Read a file from the workspace."""
        full_path = Path(self.workspace) / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {rel_path}")

        # Security: don't read outside workspace
        try:
            full_path.resolve().relative_to(Path(self.workspace).resolve())
        except ValueError:
            raise PermissionError(f"Access denied: {rel_path} is outside workspace")

        return full_path.read_text(encoding='utf-8')

    def edit_file(
        self,
        rel_path: str,
        new_content: str,
        test_path: str = ".",
        validate: bool = True,
        allow_bug_revealing: bool = False,
    ) -> EditResult:
        """
        Edit a file with automatic validation.

        Args:
            rel_path: File path relative to workspace
            new_content: Complete new file content
            test_path: Test file to run for validation
            validate: If True, run tests and revert on regression

        Returns:
            EditResult with success status and test results
        """
        full_path = Path(self.workspace) / rel_path

        # Security check
        try:
            full_path.resolve().relative_to(Path(self.workspace).resolve())
        except ValueError:
            return EditResult(
                success=False,
                path=rel_path,
                message=f"Access denied: {rel_path} is outside workspace"
            )

        # Step 1: Backup
        original_content = None
        if full_path.exists():
            original_content = full_path.read_text(encoding='utf-8')
            self._backups[rel_path] = original_content

        # Step 2: Establish baseline before touching existing files.
        # New test files intentionally skip this extra subprocess; the after-run
        # is enough to detect collection/syntax failures and bug-revealing tests.
        baseline = self.runner.run_quick(test_path) if validate and original_content is not None else None

        # Step 3: Check if content actually changed
        if original_content == new_content:
            return EditResult(
                success=False,
                path=rel_path,
                message="No changes detected — new content is identical to original"
            )

        # Step 4: Write new content
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(new_content, encoding='utf-8')
        self._clear_pycache()

        # Step 5: Validate if requested
        if validate:
            test_result = self.runner.run_quick(test_path)

            if test_result.passed:
                # Tests pass — edit is good
                return EditResult(
                    success=True,
                    path=rel_path,
                    message=f"Edit applied and tests pass ({test_result.num_passed} passed)",
                    tests_after=test_result
                )

            if (
                original_content is None
                and test_result.exit_code in (0, 1)
                and "timed out" not in test_result.stderr.lower()
                and "timeout" not in test_result.stderr.lower()
            ):
                return EditResult(
                    success=True,
                    path=rel_path,
                    message=f"New file created — validation reports {test_result.num_failed} failing test(s)",
                    tests_after=test_result
                )

            if (
                allow_bug_revealing
                and baseline is not None
                and test_result.exit_code == 1
                and "timed out" not in test_result.stderr.lower()
                and "timeout" not in test_result.stderr.lower()
                and test_result.num_passed >= baseline.num_passed
                and test_result.num_failed > baseline.num_failed
            ):
                return EditResult(
                    success=True,
                    path=rel_path,
                    message=(
                        "Edit applied — validation revealed target-code bug "
                        f"({test_result.num_passed} passed, {test_result.num_failed} failed)"
                    ),
                    tests_after=test_result
                )

            if baseline is not None and self._is_regression(baseline, test_result):
                if original_content is not None:
                    full_path.write_text(original_content, encoding='utf-8')
                else:
                    full_path.unlink(missing_ok=True)
                return EditResult(
                    success=False,
                    path=rel_path,
                    message=(
                        "Edit REVERTED — validation regressed "
                        f"(before: exit={baseline.exit_code}, {baseline.num_passed} passed, "
                        f"{baseline.num_failed} failed; after: exit={test_result.exit_code}, "
                        f"{test_result.num_passed} passed, {test_result.num_failed} failed)"
                    ),
                    tests_after=test_result,
                    reverted=True
                )

            if original_content is not None and baseline is not None:
                if test_result.num_failed < baseline.num_failed:
                    # We improved things — keep
                    return EditResult(
                        success=True,
                        path=rel_path,
                        message=f"Edit applied — reduced failures from {baseline.num_failed} to {test_result.num_failed}",
                        tests_after=test_result
                    )

                return EditResult(
                    success=True,
                    path=rel_path,
                    message=f"Edit applied — validation unchanged ({test_result.num_failed} failing)",
                    tests_after=test_result
                )

            return EditResult(
                success=True,
                path=rel_path,
                message=f"New file created — validation reports {test_result.num_failed} failing test(s)",
                tests_after=test_result
            )

        # No validation requested
        return EditResult(
            success=True,
            path=rel_path,
            message="Edit applied (no validation)"
        )

    def revert(self, rel_path: str) -> bool:
        """Revert a file to its backed-up state."""
        if rel_path not in self._backups:
            return False

        full_path = Path(self.workspace) / rel_path
        full_path.write_text(self._backups[rel_path], encoding='utf-8')
        del self._backups[rel_path]
        return True

    def get_diff(self, rel_path: str) -> Optional[str]:
        """Get diff between backup and current file."""
        if rel_path not in self._backups:
            return None

        full_path = Path(self.workspace) / rel_path
        if not full_path.exists():
            return None

        current = full_path.read_text(encoding='utf-8')
        original = self._backups[rel_path]

        if current == original:
            return None

        # Simple line diff
        orig_lines = original.splitlines(keepends=True)
        curr_lines = current.splitlines(keepends=True)

        import difflib
        diff = difflib.unified_diff(
            orig_lines, curr_lines,
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm=""
        )
        return "\n".join(diff)

    def list_files(self, pattern: str = "*.py") -> list[str]:
        """List Python files in workspace."""
        workspace_path = Path(self.workspace)
        files = []
        for f in workspace_path.rglob(pattern):
            if "__pycache__" in str(f) or ".pytest_cache" in str(f):
                continue
            try:
                rel = f.relative_to(workspace_path)
                files.append(str(rel))
            except ValueError:
                continue
        return sorted(files)
