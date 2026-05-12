"""
DeepTest Orchestrator — Main agent + subagents.

Replaces the LangChain/deepagents-based main.py with a minimal
agent loop that coordinates analysis, test generation, and critique.
"""

from typing import Optional

from bugtest.deep.llm import LLMClient
from bugtest.deep.agent import Agent, AgentResult, run_subagent
from bugtest.deep import builtin_tools  # noqa: F401 — registers tools
from bugtest.deep.config import settings


# ── System Prompts ──

# Prompt for the Claude Code CLI provider. The CLI runs end-to-end in a single
# subprocess invocation using its OWN native tools (Read / Edit / Write / Bash);
# it has no access to the orchestrator-side tool registry (`safe_edit_file`,
# `run_tests`, etc.), so the prompt must reference only CLI-native tool names.
CLAUDE_CLI_SYSTEM_PROMPT = """\
You are DeepTest, an autonomous test generation agent running inside the
Claude Code CLI. You have direct filesystem access via your built-in
Read, Edit, Write, and Bash tools.

## Success Criterion (non-negotiable)
1. The new test MUST FAIL on the buggy code (expose the bug).
2. The new test MUST PASS on the fixed version of the code.
Equivalent: buggy_passed == False AND fixed_passed == True. Encoding the
buggy output as the expected value is a FAILURE mode (the test will pass on
the bug and fail on the fix). Always reason about what the *fixed* code
should return, then assert that.

## Your Workflow (single-shot — do everything in this one turn)

You are given a workspace containing:
  - source.py                 (the buggy module under test)
  - tests/test_benchmark.py   (a baseline import-only test, MUST be preserved)

Do the following, in order:

1. Read `source.py` to understand the code and the bug.
2. Read `tests/test_benchmark.py` to see the baseline test.
3. APPEND a new pytest test function to `tests/test_benchmark.py`. Do NOT
   overwrite the existing import / baseline test — use the Edit tool with
   old_string set to the last line of the file and new_string set to that
   same line PLUS your new test below it.
4. Run `python -m pytest tests/test_benchmark.py -v` via Bash to confirm
   that your new test FAILS (because source.py is buggy). A failing test
   on the buggy code is the intended outcome — it means the test reveals
   the bug.
5. Briefly summarise what you did and stop.

## Rules
- Only edit files under `tests/`. Never modify `source.py`.
- The new test must target the SPECIFIC bug described in the user message.
- Keep the test focused: one function, a few assertions, no fixtures.
- Use the deterministic input from the hint when one is provided.
"""

MAIN_SYSTEM_PROMPT = """\
You are DeepTest, an autonomous test generation and debugging agent.
Your job is to analyze Python projects, identify test gaps, and generate
high-quality pytest test files.

## Your Workflow

### Fast Benchmark Mode
- If the task mentions `tasks_v2`, `tests/test_benchmark.py`, or asks to keep
  a benchmark short, use the minimal workflow:
  1. read `source.py` to understand the code
  2. read `tests/test_benchmark.py` to see existing tests
  3. Call `safe_edit_file` with the `append` parameter to add your new test
     AFTER the existing baseline test. The `append` text is concatenated to
     the end of the file — no need to match line-by-line.
  4. Set `allow_bug_revealing=true` so a test that fails on the buggy code
     is reported as success.
- Example call:
    safe_edit_file(
      file_path="tests/test_benchmark.py",
      append="\\n\\ndef test_bug():\\n    assert source.f(127) == 7\\n",
      allow_bug_revealing=true
    )
- The existing baseline `test_source_module_imports` is preserved automatically.
- Once a test reveals a real target-code bug, stop and report it.

### Full Workflow
1. Read the source code to understand what needs testing
2. Read existing tests (if any) to understand the baseline
3. Write focused pytest tests using `safe_edit_file` (prefer `append` for
   adding; use `old_string`/`new_string` for precise substitutions; use
   `new_content` only when fully rewriting the file).
4. Run tests with `run_tests` to verify
5. If tests fail due to YOUR test being wrong → fix and retry
6. If tests fail due to a BUG in target code → that's SUCCESS (bug revealed!)

## Rules
- Only create/edit files in the tests/ directory
- Use relative paths (e.g., `tests/test_benchmark.py`, not absolute paths)
- Always run tests after writing them
- Use `safe_edit_file` for all file modifications
- Do not edit source/application code
- `hypothesis`, `why_this_action`, and `expected_outcome` are optional — fill
  them in when you have a clear rationale, otherwise leave them blank.
- Read target source files before writing tests for them
- Preserve existing tests when adding new ones (use `append`)
"""

ANALYZER_PROMPT = """\
You are an expert Python code analyst specialized in test gap analysis.

Analyze the given project to determine what functions and code paths
need test coverage the most.

Focus on:
- Functions with complex conditional logic
- Mathematical operations with edge cases (division, boundaries)
- Error handling paths
- Public API functions

Return a clear analysis with:
- High-risk functions (with file:line references)
- Specific test gaps
- Recommended test targets in priority order
"""

CRITIC_PROMPT = """\
You are a senior test engineer reviewing a generated pytest test for a
bug-revealing benchmark task.

A passing run is defined as:  buggy_passed == False  AND  fixed_passed == True.
The test MUST fail on the buggy source and MUST pass on the fixed source.

You will receive a DIAGNOSIS line describing the failure mode. The two
inversion cases you must call out by name when you see them:

  • TEST_PASSES_ON_BUG  (buggy_passed=True) — the assertion does not
    distinguish buggy from correct behaviour. The assertion is too loose
    (e.g. checks `is not None`, length, type) or asserts the buggy output
    as expected. Recommend a stricter assertion grounded in the *fixed*
    behaviour described in the bug description.

  • OVERFIT_TO_BUG  (fixed_passed=False) — the test encodes the buggy
    output as the expected value, so it fails on the fix as well.
    Recommend rewriting the expected value to match what the *fixed*
    code should return, then re-checking against the bug description.

Also briefly evaluate assertion specificity and edge-case coverage, but the
primary objective is to flip buggy_passed/fixed_passed to the passing pair.

End your review with exactly one of:  APPROVE  /  REVISE  /  REJECT.
Be concrete ("assert bitcount(127) == 7" beats "Add edge cases").
"""

# ── Orchestrator ──

BENCHMARK_TOOLS = ["read_file", "ls", "run_tests", "safe_edit_file"]
FULL_TOOLS = ["read_file", "ls", "run_tests", "safe_edit_file", "analyze_project", "search_workspace", "save_knowledge"]


class DeepTestOrchestrator:
    """
    Main DeepTest orchestrator.

    Usage:
        orch = DeepTestOrchestrator(workspace="/path/to/project")
        result = orch.run("Write tests for source.py")
    """

    def __init__(
        self,
        workspace: str,
        model_name: Optional[str] = None,
        max_steps: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.workspace = workspace
        self.model_name = model_name or settings.default_model_name
        self.max_steps = max_steps or settings.max_steps
        self.timeout_seconds = timeout_seconds or settings.agent_timeout_seconds

        self.llm = LLMClient(
            model=self.model_name,
            timeout=settings.model_request_timeout_seconds,
            max_retries=settings.model_retries,
            workspace=self.workspace,
        )

        self.context = {"consecutive_failures": 0}

    def run(self, problem: str) -> AgentResult:
        """Run the main agent on the given problem."""
        # The Claude Code CLI provider does everything in one subprocess call
        # using its own Read/Edit/Bash/Write tools; advertising the orchestrator
        # tool registry to it just confuses the prompt. Branch here.
        if getattr(self.llm, "provider", "") == "claude_cli":
            system_prompt = CLAUDE_CLI_SYSTEM_PROMPT
            tools = None  # CLI uses native tools — no schema needed
        elif "tasks_v2" in problem or "test_benchmark" in problem:
            system_prompt = MAIN_SYSTEM_PROMPT
            tools = BENCHMARK_TOOLS
        else:
            system_prompt = MAIN_SYSTEM_PROMPT
            tools = FULL_TOOLS

        # Load workspace memory if exists
        import os
        memory_file = os.path.join(self.workspace, ".deeptest_memory")
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    memory = f.read()
                system_prompt += f"\n\n## Project Memory\n{memory}"
            except Exception:
                pass

        agent = Agent(
            llm=self.llm,
            system_prompt=system_prompt,
            tools=tools,
            workspace=self.workspace,
            max_steps=self.max_steps,
            timeout_seconds=self.timeout_seconds,
        )
        agent.context = self.context

        return agent.run(problem)

    def run_analyzer(self, problem: str) -> str:
        """Run the analyzer subagent."""
        return run_subagent(
            llm=self.llm,
            system_prompt=ANALYZER_PROMPT,
            user_message=f"Analyze this project for test gaps:\n{problem}",
            tools=["read_file", "ls", "analyze_project", "search_workspace"],
            workspace=self.workspace,
            max_steps=5,
            timeout_seconds=60,
        )

    def run_critic(self, test_code: str, test_results: str) -> str:
        """Run the critic subagent."""
        return run_subagent(
            llm=self.llm,
            system_prompt=CRITIC_PROMPT,
            user_message=f"Review this test code:\n\n```python\n{test_code}\n```\n\nTest results:\n{test_results}",
            tools=None,  # Critic is pure reasoning, no tools
            workspace=self.workspace,
            max_steps=1,
            timeout_seconds=30,
        )
