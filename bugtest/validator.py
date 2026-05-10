"""Deterministic test validator using pytest. No LLM involved."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from bugtest.models import ValidationResult


# Keep all temp workspaces inside the project tree (no /tmp, no /var/folders)
_LOCAL_TMP = Path(__file__).resolve().parent.parent / ".tmp"
_LOCAL_TMP.mkdir(exist_ok=True)


class Validator:
    """Runs a test file against buggy and fixed code to determine
    whether the test is bug-revealing.

    A test is bug-revealing iff:
      - It FAILS on the buggy code  (returncode != 0)
      - It PASSES on the fixed code (returncode == 0)
    """

    def __init__(self, timeout_seconds: int = 30):
        self._timeout = timeout_seconds

    def validate(
        self,
        test_code: str,
        buggy_dir: Path,
        fixed_dir: Path,
    ) -> ValidationResult:
        buggy_passed, buggy_output = self._run_pytest(test_code, buggy_dir)
        fixed_passed, fixed_output = self._run_pytest(test_code, fixed_dir)

        return ValidationResult(
            buggy_passed=buggy_passed,
            buggy_output=buggy_output,
            fixed_passed=fixed_passed,
            fixed_output=fixed_output,
            is_bug_revealing=(not buggy_passed) and fixed_passed,
        )

    def _run_pytest(self, test_code: str, source_dir: Path) -> tuple[bool, str]:
        """Copy test + source to temp dir, run pytest, return (passed, output)."""
        with tempfile.TemporaryDirectory(dir=str(_LOCAL_TMP)) as tmpdir:
            tmp = Path(tmpdir)

            for py_file in source_dir.glob("*.py"):
                shutil.copy(py_file, tmp / py_file.name)

            test_path = tmp / "test_generated.py"
            test_path.write_text(test_code, encoding="utf-8")

            try:
                result = subprocess.run(
                    ["python3", "-m", "pytest", "-x", "-v", "test_generated.py"],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout,
                )
                output = result.stdout + "\n" + result.stderr
                return result.returncode == 0, output.strip()
            except subprocess.TimeoutExpired:
                return False, f"TIMEOUT after {self._timeout}s"
            except Exception as e:
                return False, f"ERROR: {e}"
