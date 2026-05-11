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

MAIN_SYSTEM_PROMPT = """\
You are DeepTest, an autonomous bug-revealing test generator.

## Goal
Add ONE focused pytest test to `tests/test_benchmark.py` that FAILS on the
buggy source (revealing the bug) and would PASS on a fixed version.

## Workflow
1. Read `source.py` to understand the code and the bug.
2. Read `tests/test_benchmark.py` to see the existing baseline test.
3. **Edit `tests/test_benchmark.py`** to APPEND your new test AFTER the
   existing baseline test. Use whichever editing tool is available to you
   (e.g. `safe_edit_file` if listed in your tools, otherwise the standard
   `Edit` tool). Preserve the baseline test — do NOT overwrite it.
4. After editing, you are done. Do not call more tools.

## How to append
- The baseline file ends with a line like `assert source is not None`.
- Place your new test below it, separated by a blank line, e.g.:

```python
import source


def test_source_module_imports():
    assert source is not None


def test_bug_revealing_case():
    # your new test here
    assert source.some_function(arg) == expected
```

## Rules
- Only edit files under `tests/`. Never modify `source.py` or any other file.
- Use relative paths.
- If your editing tool requires reasoning fields (`hypothesis`,
  `why_this_action`, `expected_outcome`), provide one short sentence each.
- A test that fails on the buggy code (because it caught the bug) is SUCCESS —
  stop and report.
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
You are a senior test engineer reviewing generated tests.

Evaluate the test code for:
1. Coverage completeness — are edge cases covered?
2. Assertion quality — specific assertions, not just `assert result`
3. Bug-revealing potential — does it test the right behavior?

Score: APPROVE (good), REVISE (needs work), or REJECT (fundamentally flawed).
Be specific: "Test divide(x, 0)" not "Add edge cases".
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
        if "tasks_v2" in problem or "test_benchmark" in problem:
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
            user_message=f"Review this test code:\n\n```python\n{test_code}\n```\n\nTest results:\n{test_results}\n\nYou may use `read_file` on `source.py` to inspect the buggy code before giving feedback.",
            tools=["read_file"],
            workspace=self.workspace,
            max_steps=3,
            timeout_seconds=60,
        )
