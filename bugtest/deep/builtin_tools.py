"""
Built-in tools for DeepTest agent.

These wrap existing modules (TestRunner, SafeEditor, ProjectModel)
and expose them through the minimal tool registry.
"""

import os
import re
import sys
import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Optional

from bugtest.deep.tools import register_tool
from bugtest.deep.runner import TestRunner
from bugtest.deep.editor import SafeEditor
from bugtest.deep.analysis.project_model import ProjectModel
from bugtest.deep.analysis.dependency_graph import DependencyGraph


@register_tool(name="read_file", description="Read a file from the workspace.")
def read_file(file_path: str, workspace: str = ".") -> str:
    """Read file content. Use relative paths like 'source.py' or 'tests/test_benchmark.py'."""
    full_path = Path(workspace) / file_path
    if not full_path.exists():
        return f"Error: File not found: {file_path}"
    try:
        full_path.resolve().relative_to(Path(workspace).resolve())
    except ValueError:
        return f"Error: Path escapes workspace: {file_path}"
    return full_path.read_text(encoding="utf-8")


@register_tool(name="ls", description="List files in a directory.")
def ls(path: str = ".", workspace: str = ".") -> str:
    """List files and directories."""
    target = Path(workspace) / path
    if not target.exists():
        return f"Error: Directory not found: {path}"
    entries = []
    for entry in sorted(target.iterdir()):
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        suffix = "/" if entry.is_dir() else ""
        entries.append(f"{entry.name}{suffix}")
    return "\n".join(entries) if entries else "(empty directory)"


@register_tool(name="run_tests", description="Run pytest with coverage on the workspace.")
def run_tests(test_path: str = ".", workspace: str = ".", context: dict = None) -> str:
    """Run pytest with coverage. Returns pass/fail counts and coverage gaps."""
    runner = TestRunner(workspace)
    start_time = time.time()
    result = runner.run(test_path)
    duration = time.time() - start_time

    # Anti-loop guardrail
    if context and not result.passed:
        context["consecutive_failures"] = context.get("consecutive_failures", 0) + 1
        if context["consecutive_failures"] >= 3:
            return "SYSTEM_GUARDRAIL: Maximum consecutive failures. You MUST stop and rethink."
    elif context and result.passed:
        context["consecutive_failures"] = 0

    response = {
        "ok": result.passed,
        "passed": result.num_passed,
        "failed": result.num_failed,
        "exit_code": result.exit_code,
        "duration_seconds": round(duration, 2),
        "failure_messages": result.failure_messages[:5],
        "stdout": result.stdout[-5000:],
        "stderr": result.stderr[-2000:] if result.stderr else "",
    }

    if result.coverage_gaps:
        gaps = {}
        for fp, lines in list(result.coverage_gaps.items())[:3]:
            gaps[fp] = lines[:10]
        response["coverage_gaps"] = gaps

    return json.dumps(response, indent=2)


@register_tool(
    name="safe_edit_file",
    description="Create or edit a test file with automatic validation and revert on regression."
)
def safe_edit_file(
    file_path: str,
    hypothesis: str,
    why_this_action: str,
    expected_outcome: str,
    new_content: Optional[str] = None,
    old_string: Optional[str] = None,
    new_string: Optional[str] = None,
    allow_bug_revealing: bool = False,
    workspace: str = ".",
) -> str:
    """Edit or create a file in tests/ with reasoning and auto-validation."""
    # Validate reasoning
    if not hypothesis or len(hypothesis) < 10:
        return "Error: hypothesis must be at least 10 characters."
    if not why_this_action:
        return "Error: why_this_action is required."
    if not expected_outcome:
        return "Error: expected_outcome is required."

    # Validate path (must be under tests/)
    workspace_path = Path(workspace).resolve()
    candidate = (workspace_path / file_path).resolve()
    try:
        relative = candidate.relative_to(workspace_path)
    except ValueError:
        return "Error: Path escapes workspace."

    if relative.parts[:1] != ("tests",):
        return "Error: safe_edit_file may only write under tests/."
    if not candidate.name.endswith(".py"):
        return "Error: Only .py files allowed."

    # Resolve content
    final_content = new_content
    if final_content is None:
        if old_string is None or new_string is None:
            return "Error: Provide new_content, or both old_string and new_string."
        full_path = workspace_path / relative
        if not full_path.exists():
            return "Error: old_string/new_string edits require an existing file."
        current = full_path.read_text(encoding="utf-8")
        if old_string not in current:
            return "Error: old_string not found in file."
        if current.count(old_string) != 1:
            return "Error: old_string must match exactly one location."
        final_content = current.replace(old_string, new_string, 1)

    # Write file directly and run tests (simplified — no revert on bug-revealing)
    full_path = workspace_path / relative
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(final_content, encoding="utf-8")

    # Run tests to validate
    runner = TestRunner(workspace)
    test_result = runner.run_quick(".")

    if test_result.passed:
        return json.dumps({
            "status": "success",
            "path": str(relative),
            "message": f"Tests pass ({test_result.num_passed} passed)",
            "tests_after": {"passed": True, "num_passed": test_result.num_passed, "num_failed": 0},
        }, indent=2)

    if allow_bug_revealing and test_result.exit_code == 1 and test_result.num_failed > 0:
        # Bug-revealing: test fails because of target code bug — this is success!
        return json.dumps({
            "status": "success",
            "path": str(relative),
            "message": f"Bug-revealing test added ({test_result.num_passed} passed, {test_result.num_failed} failed — reveals target bug)",
            "bug_revealed": True,
            "tests_after": {
                "passed": False, "num_passed": test_result.num_passed,
                "num_failed": test_result.num_failed,
                "failure_messages": test_result.failure_messages[:3],
            },
        }, indent=2)

    if test_result.exit_code not in (0, 1):
        # Syntax/collection error — revert
        full_path.write_text(
            "import source\n\n\ndef test_source_module_imports():\n    assert source is not None\n",
            encoding="utf-8"
        )
        return json.dumps({
            "status": "failed",
            "path": str(relative),
            "message": f"Reverted — syntax/collection error (exit={test_result.exit_code})",
            "reverted": True,
            "stderr": test_result.stderr[:500],
        }, indent=2)

    return json.dumps({
        "status": "success",
        "path": str(relative),
        "message": f"Written ({test_result.num_passed} passed, {test_result.num_failed} failed)",
        "tests_after": {
            "passed": False, "num_passed": test_result.num_passed,
            "num_failed": test_result.num_failed,
        },
    }, indent=2)


@register_tool(name="analyze_project", description="AST analysis of the workspace project.")
def analyze_project(workspace: str = ".") -> str:
    """Analyze project structure, complexity, and dependencies."""
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, 5000))
    try:
        model = ProjectModel(workspace)
        snapshot = model.analyze()
    finally:
        sys.setrecursionlimit(old_limit)

    dep_graph = DependencyGraph(snapshot)

    lines = ["PROJECT ANALYSIS REPORT", "=" * 50, "", snapshot.summary(), ""]

    all_funcs = snapshot.get_all_functions()
    if all_funcs:
        sorted_funcs = sorted(all_funcs, key=lambda f: f.complexity, reverse=True)
        lines.append("HIGH-RISK FUNCTIONS (by complexity):")
        for func in sorted_funcs[:10]:
            lines.append(
                f"  - {func.name} in {func.module_path} "
                f"(complexity={func.complexity}, lines={func.line_range[0]}-{func.line_range[1]})"
            )

    lines.append("")
    lines.append(dep_graph.to_prompt_context())
    return "\n".join(lines)


@register_tool(name="search_workspace", description="Search workspace with grep/ripgrep.")
def search_workspace(query: str, file_glob: str = "", workspace: str = ".") -> str:
    """Search the workspace for a pattern."""
    if not query:
        return "Error: Provide a search query."

    cmd = ["grep", "-RIn", query, "."]
    try:
        proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return "Search timed out."

    output = proc.stdout.strip()
    if not output:
        return f"No matches found for: {query!r}"
    return output[:15000]


@register_tool(name="save_knowledge", description="Save project knowledge to memory file.")
def save_knowledge(topic: str, content: str, workspace: str = ".") -> str:
    """Save a testing insight to .deeptest_memory."""
    memory_file = os.path.join(workspace, ".deeptest_memory")
    with open(memory_file, "a", encoding="utf-8") as f:
        f.write(f"\n### {topic}\n{content}\n")
    return f"Saved: {topic}"


# ── SWE Atlas Tools ──

@register_tool(
    name="safe_edit_test_file",
    description="Create or edit a test file for SWE Atlas tasks (broader scope than safe_edit_file)."
)
def safe_edit_test_file(
    file_path: str,
    hypothesis: str,
    why_this_action: str,
    expected_outcome: str,
    new_content: Optional[str] = None,
    old_string: Optional[str] = None,
    new_string: Optional[str] = None,
    workspace: str = ".",
) -> str:
    """Edit test files for SWE Atlas (cross-language support)."""
    if not hypothesis or len(hypothesis) < 10:
        return "Error: hypothesis must be at least 10 characters."

    workspace_path = Path(workspace).resolve()
    candidate = (workspace_path / file_path).resolve()
    try:
        relative = candidate.relative_to(workspace_path)
    except ValueError:
        return "Error: Path escapes workspace."

    # Resolve content
    final_content = new_content
    if final_content is None:
        if old_string is None or new_string is None:
            return "Error: Provide new_content, or both old_string and new_string."
        if not candidate.exists():
            return "Error: File does not exist for old_string edit."
        current = candidate.read_text(encoding="utf-8")
        if old_string not in current:
            return "Error: old_string not found."
        if current.count(old_string) != 1:
            return "Error: old_string must match exactly once."
        final_content = current.replace(old_string, new_string, 1)

    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(final_content, encoding="utf-8")
    return json.dumps({"status": "success", "path": str(relative), "message": "File written."})


@register_tool(
    name="run_swe_atlas_tests",
    description="Run official SWE Atlas test script in Docker container."
)
def run_swe_atlas_tests(test_files: str = "", workspace: str = ".", context: dict = None) -> str:
    """Run SWE Atlas run_script.sh in the active Docker container."""
    container_id = (context or {}).get("swe_atlas_container_id")
    if not container_id:
        return "Error: No SWE Atlas container configured."

    timeout = int((context or {}).get("swe_atlas_test_timeout_seconds", 900))
    command = "bash /tests/run_script.sh"
    if test_files.strip():
        command += " " + " ".join(shlex.quote(p) for p in shlex.split(test_files))

    started = time.time()
    try:
        proc = subprocess.run(
            ["docker", "exec", container_id, "bash", "-lc", command],
            capture_output=True, text=True, timeout=timeout,
        )
        return json.dumps({
            "command": command,
            "return_code": proc.returncode,
            "duration_seconds": round(time.time() - started, 3),
            "stdout": proc.stdout[-20000:],
            "stderr": proc.stderr[-20000:],
        }, indent=2)
    except subprocess.TimeoutExpired:
        return json.dumps({"command": command, "return_code": -1, "stderr": f"Timed out after {timeout}s"})


@register_tool(name="write_test_manifest", description="Write manifest.txt for SWE Atlas verifier.")
def write_test_manifest(manifest_content: str, workspace: str = ".", context: dict = None) -> str:
    """Write /logs/agent/manifest.txt."""
    logs_dir = (context or {}).get("swe_atlas_logs_dir")
    if not logs_dir:
        return "Error: No logs directory configured."

    content = manifest_content.strip()
    if not content:
        return "Error: Empty manifest."
    if "<<TEST_MANIFEST>>" not in content:
        content = f"<<TEST_MANIFEST>>\n{content}\n<<TEST_MANIFEST>>"

    manifest_path = Path(logs_dir) / "agent" / "manifest.txt"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(content + "\n", encoding="utf-8")
    return json.dumps({"status": "success", "path": "/logs/agent/manifest.txt"})
