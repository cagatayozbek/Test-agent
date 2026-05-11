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
You are DeepTest, an autonomous test generation and debugging agent.
Your job is to analyze Python projects, identify test gaps, and generate
high-quality pytest test files.

## Your Workflow

### Fast Benchmark Mode
- If the task mentions `tasks_v2`, `tests/test_benchmark.py`, or asks to keep
  a benchmark short, use the minimal workflow:
  1. read `source.py` to understand the code
  2. read `tests/test_benchmark.py` to see existing tests
  3. Use safe_edit_file with old_string/new_string to APPEND your new test
     AFTER the existing tests. Never overwrite existing tests!
  4. Set allow_bug_revealing=true when the test reveals a real bug.
- CRITICAL: You MUST preserve all existing tests. Use old_string to match the
  last line of the existing file, and new_string to append your new test after it.
- Example: old_string="assert source is not None\n" new_string="assert source is not None\n\n\ndef test_bug():\n    ..."
- Once a test reveals a real target-code bug, stop and report it.

### Full Workflow
1. Read the source code to understand what needs testing
2. Read existing tests (if any) to understand the baseline
3. Write focused pytest tests using `safe_edit_file`
4. Run tests with `run_tests` to verify
5. If tests fail due to YOUR test being wrong → fix and retry
6. If tests fail due to a BUG in target code → that's SUCCESS (bug revealed!)

## Rules
- Only create/edit files in the tests/ directory
- Use relative paths (e.g., `tests/test_benchmark.py`, not absolute paths)
- Always run tests after writing them
- Use `safe_edit_file` for all file modifications
- Do not edit source/application code
- Every edit needs: hypothesis, why_this_action, expected_outcome
- Read target source files before writing tests for them
- Preserve existing tests when adding new ones
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
            user_message=f"Review this test code:\n\n```python\n{test_code}\n```\n\nTest results:\n{test_results}",
            tools=None,  # Critic is pure reasoning, no tools
            workspace=self.workspace,
            max_steps=1,
            timeout_seconds=30,
        )
