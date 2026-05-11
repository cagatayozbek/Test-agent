"""Shared policy for identifying files that are legitimate test targets."""

from __future__ import annotations

from pathlib import PurePosixPath


TEST_FILE_SUFFIXES = (
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".java",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".uts",
)


def normalize_workspace_path(path: str) -> str:
    """Normalize a workspace-relative path without allowing absolute paths."""
    normalized = str(PurePosixPath(path.replace("\\", "/")))
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def is_allowed_test_file(path: str) -> bool:
    """Return True when a changed path looks like a test file across common stacks."""
    normalized = normalize_workspace_path(path)
    if not normalized or normalized.startswith("../"):
        return False

    parts = PurePosixPath(normalized).parts
    name = parts[-1].lower() if parts else ""
    stem = name.rsplit(".", 1)[0]

    if not name.endswith(TEST_FILE_SUFFIXES):
        return False

    if parts and parts[0] in {"tests", "test"}:
        return True
    if any(part in {"tests", "test"} or part.endswith("_tests") for part in parts[:-1]):
        return True
    if name.startswith("test_") or name.startswith("test-"):
        return True
    if name.endswith("_test.go") or name.endswith("_test.py") or name.endswith("-test.js"):
        return True
    if ".test." in name or ".spec." in name:
        return True
    if name.endswith(".uts"):
        return True
    if stem.endswith("_test") or stem.endswith("_spec"):
        return True

    return False


def split_test_and_non_test_files(paths: list[str]) -> tuple[list[str], list[str]]:
    """Split paths into allowed test files and policy violations."""
    test_files: list[str] = []
    non_test_files: list[str] = []
    for path in paths:
        normalized = normalize_workspace_path(path)
        if is_allowed_test_file(normalized):
            test_files.append(normalized)
        else:
            non_test_files.append(normalized)
    return sorted(test_files), sorted(non_test_files)
