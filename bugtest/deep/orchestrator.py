"""
DeepTest Orchestrator — main agent + analyzer/critic subagents.

System prompts come from `bugtest.deep.prompts` — a single model-agnostic
template that swaps tool names per provider via `bugtest.deep.capabilities`.
This is the v2.0 fairness contract: every model sees the same prompt
structure, only the tool-name tokens differ.
"""

import os
from typing import Optional

from bugtest.deep import builtin_tools  # noqa: F401 — registers tools
from bugtest.deep import capabilities
from bugtest.deep.agent import Agent, AgentResult, run_subagent
from bugtest.deep.config import settings
from bugtest.deep.llm import LLMClient
from bugtest.deep.prompts import (
    ANALYZER_PROMPT,
    CRITIC_PROMPT,
    PROMPT_VERSION,
    render_system_prompt,
)


# Tool registries advertised to the agent loop. The Claude Code CLI provider
# uses its own native Read/Edit/Bash tools end-to-end in one subprocess, so it
# gets `tools=None` (the rendered prompt names those tools by their CLI
# spellings via the capability dict).
BENCHMARK_TOOLS = ["read_file", "ls", "run_tests", "safe_edit_file"]
FULL_TOOLS = [
    "read_file", "ls", "run_tests", "safe_edit_file",
    "analyze_project", "search_workspace", "save_knowledge",
]


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

    def _select_tool_registry(self, problem: str) -> Optional[list[str]]:
        """Pick the orchestrator-side tool list. CLI provider gets None."""
        if self.llm.capabilities.get("provider") == "claude_cli":
            return None
        if "tasks_v2" in problem or "test_benchmark" in problem:
            return BENCHMARK_TOOLS
        return FULL_TOOLS

    def run(self, problem: str) -> AgentResult:
        """Run the main agent on the given problem."""
        tools = self._select_tool_registry(problem)

        tool_names = self.llm.capabilities["tool_names"]
        system_prompt, prompt_hash = render_system_prompt(
            tool_names=tool_names,
            max_steps=self.max_steps,
        )

        # Optional workspace memory append. The hash already pins the
        # rendered prompt — appended memory is logged separately under
        # capabilities_used for now (the hash intentionally excludes it
        # because memory is per-workspace, not per-prompt-version).
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
            prompt_version=PROMPT_VERSION,
            prompt_template_hash=prompt_hash,
        )
        agent.context.update(self.context)

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
            user_message=(
                f"Review this test code:\n\n```python\n{test_code}\n```\n\n"
                f"Test results:\n{test_results}"
            ),
            tools=None,  # Critic is pure reasoning, no tools
            workspace=self.workspace,
            max_steps=1,
            timeout_seconds=30,
        )
