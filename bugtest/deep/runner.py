"""
DeepTest Runner — Subprocess-based test execution.

Replaces DockerSandbox with direct subprocess calls.
No Docker daemon needed. Tests run in the workspace directory.

Coverage parsing reuses the existing CoverageParser from analysis.py
since it's one of the few well-written pieces of the old codebase.
"""

import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from bugtest.deep.types import TestResult


class CoverageParser:
    """
    Parse coverage.py output to extract missing lines.

    Carried over from analysis.py — this part actually works well.
    """

    # Pattern: src/module.py    50     10    80%   10-15, 45
    COVERAGE_LINE_PATTERN = re.compile(
        r'^(\S+\.py)\s+\d+\s+\d+\s+\d+%\s+(.+)$'
    )

    # Patterns for test counts — pytest can output in any order
    PASSED_PATTERN = re.compile(r'(\d+)\s+passed')
    FAILED_PATTERN = re.compile(r'(\d+)\s+failed')

    # Pattern for FAILED lines: "FAILED test_file.py::test_name - reason"
    FAILURE_LINE_PATTERN = re.compile(
        r'FAILED\s+\S+::\S+\s*-\s*(.+)$', re.MULTILINE
    )

    @classmethod
    def parse_coverage(cls, output: str) -> dict[str, list[int]]:
        """Parse coverage report into {file: [missing_lines]}."""
        gaps = {}
        for line in output.split('\n'):
            match = cls.COVERAGE_LINE_PATTERN.match(line.strip())
            if match:
                filename = match.group(1)
                missing_str = match.group(2).strip()
                if missing_str:
                    missing = cls._parse_line_ranges(missing_str)
                    if missing:
                        gaps[filename] = missing
        return gaps

    @classmethod
    def parse_test_counts(cls, output: str) -> tuple[int, int]:
        """Parse passed/failed counts from pytest output."""
        passed_match = cls.PASSED_PATTERN.search(output)
        failed_match = cls.FAILED_PATTERN.search(output)
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        return passed, failed

    @classmethod
    def parse_failures(cls, output: str) -> list[str]:
        """Extract failure messages from pytest output."""
        return cls.FAILURE_LINE_PATTERN.findall(output)

    @classmethod
    def _parse_line_ranges(cls, ranges_str: str) -> list[int]:
        """Parse '10-15, 45' into [10, 11, 12, 13, 14, 15, 45]."""
        lines = []
        for part in ranges_str.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    lines.extend(range(int(start), int(end) + 1))
                except ValueError:
                    continue
            else:
                try:
                    lines.append(int(part))
                except ValueError:
                    continue
        return sorted(lines)


class TestRunner:
    """
    Runs pytest + coverage in a subprocess.

    No Docker. No containers. Just subprocess.run().
    If you need isolation, run the whole agent in Docker.
    """

    def __init__(self, workspace: str, timeout: int = 30):
        self.workspace = workspace
        self.timeout = timeout

    def run(self, test_path: str = ".", pytest_args: Optional[list[str]] = None) -> TestResult:
        """
        Run pytest with coverage and return structured result.

        Args:
            test_path: Path to test file/dir (relative to workspace)
            pytest_args: Extra pytest arguments

        Returns:
            TestResult with pass/fail status, coverage gaps, and failure messages
        """
        args = pytest_args or []

        import sys
        # Run pytest with coverage
        cmd = [
            sys.executable, "-m", "coverage", "run",
            "--source=.", "-m", "pytest",
            test_path, "-v", "--tb=short", *args
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False,
                exit_code=-1,
                stdout="",
                stderr="Test execution timed out",
                num_failed=1,
                failure_messages=["Timeout"]
            )

        test_stdout = proc.stdout
        test_exit = proc.returncode

        # Get coverage report
        cov_cmd = [sys.executable, "-m", "coverage", "report", "--show-missing"]
        try:
            cov_proc = subprocess.run(
                cov_cmd,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10
            )
            coverage_output = cov_proc.stdout
        except (subprocess.TimeoutExpired, Exception):
            coverage_output = ""

        # Parse everything
        coverage_gaps = CoverageParser.parse_coverage(coverage_output)
        num_passed, num_failed = CoverageParser.parse_test_counts(test_stdout)
        failure_messages = CoverageParser.parse_failures(test_stdout)

        combined_output = test_stdout
        if coverage_output:
            combined_output += "\n\n--- Coverage Report ---\n" + coverage_output

        return TestResult(
            passed=(test_exit == 0),
            exit_code=test_exit,
            stdout=combined_output,
            stderr=proc.stderr,
            coverage_gaps=coverage_gaps,
            num_passed=num_passed,
            num_failed=num_failed,
            failure_messages=failure_messages
        )

    def run_quick(self, test_path: str = ".") -> TestResult:
        """Run pytest without coverage — faster, for edit validation."""
        import sys
        cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False, exit_code=-1, stdout="", stderr="Timeout"
            )

        num_passed, num_failed = CoverageParser.parse_test_counts(proc.stdout)
        failure_messages = CoverageParser.parse_failures(proc.stdout)

        return TestResult(
            passed=(proc.returncode == 0),
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            num_passed=num_passed,
            num_failed=num_failed,
            failure_messages=failure_messages
        )
