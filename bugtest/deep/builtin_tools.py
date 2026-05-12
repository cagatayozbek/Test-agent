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


_BASELINE_TEST_REVERT = (
    "import source\n\n\ndef test_source_module_imports():\n"
    "    assert source is not None\n"
)


def _file_tail_diagnostic(text: str, max_chars: int = 150) -> str:
    """Return a short tail-window of `text` for inclusion in error messages."""
    if not text:
        return "(file is empty)"
    tail = text[-max_chars:]
    if len(text) > max_chars:
        tail = "…" + tail
    return tail


def _syntax_error_snippet(stderr: str, stdout: str = "", max_lines: int = 2) -> str:
    """Return the most informative error lines from stderr+stdout (capped).

    pytest writes collection-time errors (SyntaxError, IndentationError) to
    stdout, not stderr, so we prefer stderr but fall back to scanning stdout
    for lines that look like Python errors.
    """
    err_lines = [line for line in (stderr or "").splitlines() if line.strip()]
    if err_lines:
        return "\n".join(err_lines[:max_lines])
    # Fall back to stdout: pick the first lines that look like Python errors.
    err_kw = ("Error", "error:", "Traceback")
    out_lines = [
        line for line in (stdout or "").splitlines()
        if line.strip() and any(kw in line for kw in err_kw)
    ]
    return "\n".join(out_lines[:max_lines])


def _bump_failure_mode(context: Optional[dict], tag: str) -> None:
    """Increment a counter in `context["tool_failure_mode_count"]`.

    The agent loop reads this dict to populate AttemptRecord.
    Safe no-op when the tool is invoked outside an agent run (no context).
    """
    if context is None:
        return
    counts = context.setdefault("tool_failure_mode_count", {})
    counts[tag] = counts.get(tag, 0) + 1


def _classify_revert(stderr: str, stdout: str) -> str:
    """Distinguish a Python SyntaxError from a generic pytest collection error.

    SyntaxError/IndentationError prints to stdout during pytest collection on
    Python 3.13; older Python versions route some of it through stderr. We
    sniff both — if any of those tokens appear, tag it `revert_syntax`,
    otherwise `revert_collection`.
    """
    blob = (stderr or "") + " " + (stdout or "")
    if "SyntaxError" in blob or "IndentationError" in blob:
        return "revert_syntax"
    return "revert_collection"


@register_tool(
    name="safe_edit_file",
    description=(
        "Add or correct a pytest test under `tests/`. Pick exactly one mode: "
        "`mode='append'` (DEFAULT — concat `append` text to end of file) "
        "OR `mode='replace'` (substitute `old_string` with `new_string`, "
        "exact single match). Edits that produce a Python syntax or "
        "pytest-collection error are auto-reverted to the baseline."
    ),
    param_descriptions={
        "file_path": "Path relative to workspace; must start with `tests/` and end with `.py`.",
        "mode": "Either 'append' (default — add to end of file) or 'replace' (substitute old_string with new_string).",
        "append": "Text to append. Required when mode='append'. A newline is inserted between the existing content and your text if needed.",
        "old_string": "Exact substring to replace; must match the file exactly once including any newlines. Required when mode='replace'.",
        "new_string": "Replacement text for old_string. Required when mode='replace'.",
        "allow_bug_revealing": "Set true when you intend the new test to FAIL on the buggy code — the tool reports bug_revealed=true instead of treating the failure as an error.",
        "hypothesis": "Optional. Short rationale for the edit (any length).",
        "why_this_action": "Optional. Why this specific edit shape was chosen.",
        "expected_outcome": "Optional. What you expect to see after the edit.",
    },
)
def safe_edit_file(
    file_path: str,
    mode: str = "append",
    append: Optional[str] = None,
    old_string: Optional[str] = None,
    new_string: Optional[str] = None,
    hypothesis: str = "",
    why_this_action: str = "",
    expected_outcome: str = "",
    allow_bug_revealing: bool = False,
    workspace: str = ".",
    context: Optional[dict] = None,
) -> str:
    """Edit a file under tests/ with auto-validation and revert-on-error.

    Two modes:
      - mode='append'   -> concat `append` to end of existing file
      - mode='replace'  -> substitute exact `old_string` -> `new_string`
    """
    # Track whether the model bothered to fill any reasoning field; the agent
    # loop snapshots this into AttemptRecord.reasoning_filled.
    if context is not None:
        context["last_reasoning_filled"] = bool(
            (hypothesis or "").strip()
            or (why_this_action or "").strip()
            or (expected_outcome or "").strip()
        )

    # Synthesize placeholders so downstream string formatting never sees empty;
    # reasoning content itself is opt-in (no validation, no length floor).
    hypothesis = hypothesis or "(not provided)"
    why_this_action = why_this_action or "(not provided)"
    expected_outcome = expected_outcome or "(not provided)"

    # --- Mode validation ----------------------------------------------------
    if mode not in ("append", "replace"):
        _bump_failure_mode(context, "mode_conflict")
        return (
            f"Error: mode must be 'append' or 'replace', got {mode!r}. "
            "For adding a new test, use mode='append' with `append=\"...\"`."
        )

    if mode == "append":
        if append is None:
            _bump_failure_mode(context, "mode_conflict")
            return (
                "Error: mode='append' requires the `append` parameter "
                "containing the test code to add."
            )
        if old_string is not None or new_string is not None:
            _bump_failure_mode(context, "mode_conflict")
            return (
                "Error: mode='append' must not pass `old_string`/`new_string`. "
                "Switch to mode='replace' for substring edits."
            )
    else:  # mode == "replace"
        if old_string is None or new_string is None:
            _bump_failure_mode(context, "mode_conflict")
            return (
                "Error: mode='replace' requires both `old_string` and "
                "`new_string`."
            )
        if append is not None:
            _bump_failure_mode(context, "mode_conflict")
            return (
                "Error: mode='replace' must not pass `append`. "
                "Switch to mode='append' to add at the end of the file."
            )

    # --- Path validation ----------------------------------------------------
    workspace_path = Path(workspace).resolve()
    candidate = (workspace_path / file_path).resolve()
    try:
        relative = candidate.relative_to(workspace_path)
    except ValueError:
        _bump_failure_mode(context, "path_outside_tests")
        return "Error: Path escapes workspace."

    if relative.parts[:1] != ("tests",):
        _bump_failure_mode(context, "path_outside_tests")
        return "Error: safe_edit_file may only write under tests/."
    if not candidate.name.endswith(".py"):
        _bump_failure_mode(context, "path_outside_tests")
        return "Error: Only .py files allowed."

    full_path = workspace_path / relative

    # --- Content resolution -------------------------------------------------
    if mode == "append":
        if not full_path.exists():
            return "Error: append mode requires an existing file."
        current = full_path.read_text(encoding="utf-8")
        sep = "" if current.endswith("\n") or current == "" else "\n"
        final_content = current + sep + append  # type: ignore[operator]
    else:  # replace
        if not full_path.exists():
            return "Error: replace mode requires an existing file."
        current = full_path.read_text(encoding="utf-8")
        if old_string not in current:
            tail = _file_tail_diagnostic(current)
            return (
                "Error: old_string not found in file. File ends with:\n"
                f"---\n{tail}\n---\n"
                "Tip: extract the EXACT trailing substring (including newlines) "
                "from the file, or use mode='append' to add at the end instead."
            )
        if current.count(old_string) != 1:
            return (
                f"Error: old_string matches {current.count(old_string)} locations; "
                "it must match exactly one. Include more surrounding context to disambiguate."
            )
        final_content = current.replace(old_string, new_string, 1)  # type: ignore[arg-type]

    # --- Write + validate ---------------------------------------------------
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(final_content, encoding="utf-8")

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
        # Bug-revealing failure on buggy code — this is success.
        return json.dumps({
            "status": "success",
            "path": str(relative),
            "message": (
                f"Bug-revealing test added ({test_result.num_passed} passed, "
                f"{test_result.num_failed} failed — reveals target bug)"
            ),
            "bug_revealed": True,
            "tests_after": {
                "passed": False, "num_passed": test_result.num_passed,
                "num_failed": test_result.num_failed,
                "failure_messages": test_result.failure_messages[:3],
            },
        }, indent=2)

    if test_result.exit_code not in (0, 1):
        # Syntax/collection error — revert to baseline and tag the failure mode.
        revert_tag = _classify_revert(test_result.stderr, test_result.stdout)
        _bump_failure_mode(context, revert_tag)
        full_path.write_text(_BASELINE_TEST_REVERT, encoding="utf-8")
        return json.dumps({
            "status": "failed",
            "path": str(relative),
            "message": (
                f"Reverted — syntax/collection error (exit={test_result.exit_code}). "
                "Your edit was rejected; the baseline test was restored. Fix the syntax and retry."
            ),
            "reverted": True,
            "failure_mode": revert_tag,
            "stderr_snippet": _syntax_error_snippet(test_result.stderr, test_result.stdout),
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
    hypothesis: str = "",
    why_this_action: str = "",
    expected_outcome: str = "",
    new_content: Optional[str] = None,
    old_string: Optional[str] = None,
    new_string: Optional[str] = None,
    workspace: str = ".",
    context: Optional[dict] = None,
) -> str:
    """Edit test files for SWE Atlas (cross-language support)."""
    # Reasoning fields opt-in to match deep mode's policy; SWE Atlas tasks
    # historically required ≥10 chars of hypothesis but that biased weak
    # tool-callers' success rates, so the floor is removed.
    if context is not None:
        context["last_reasoning_filled"] = bool(
            (hypothesis or "").strip()
            or (why_this_action or "").strip()
            or (expected_outcome or "").strip()
        )

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
