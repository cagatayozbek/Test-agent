"""Custom orchestrator session - main experimental pipeline.

This module provides the core multi-agent orchestration logic for bug investigation.
It replaces DeepAgents with a deterministic custom loop after DeepAgents exhibited
non-terminating internal loops (see docs/deepagents_failure.md).

Architecture:
    The CustomSession runs agents in a fixed sequence defined by AgentGraph:
    - Baseline mode: Single LLM call
    - Agentic mode: planner → analysis → critic → reflection → executor
    
    Each agent receives context from previous agents via ConversationHistory,
    enabling collaborative reasoning.

Key Classes:
    AgentMessage: Single message from an agent
    ConversationHistory: Tracks all agent outputs for context passing
    RunResult: Final output from a session run
    CustomSession: Main orchestrator class
    SummaryBuilder: Constructs Summary objects from run results

Example:
    >>> from custom_session import CustomSession
    >>> session = CustomSession(
    ...     graph=agent_graph,
    ...     mode="agentic",
    ...     prompts=prompts,
    ...     tools=instrumented_tools,
    ...     log_path=Path("./logs/raw_logs.jsonl"),
    ...     llm=gemini_client,
    ...     task_context=task_context,
    ... )
    >>> result = session.run(max_iterations=5)
    >>> print(result.analysis_text)
"""

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from emitter import emit_log_entry
from instrumented_tools import InstrumentedTools
from runner import build_log_entry
from schemas import CriticResponse, EvaluationResult, Summary, SemanticHypothesis, TokenUsage
from graph_loader import AgentGraph
from llm_client import GeminiClient, LLMResponse

if TYPE_CHECKING:
    from task_loader import TaskContext, TaskContextV2
    from evaluation.test_evaluator import TestEvaluator, TestEvaluationResult


@dataclass
class AgentMessage:
    """A single message from an agent in the conversation history.
    
    Stores the output from one agent to be included as context for subsequent
    agents in the pipeline.
    
    Attributes:
        agent: Name of the agent (e.g., "planner", "analysis", "critic")
        content: Raw text output from the agent's LLM call
    
    Example:
        >>> msg = AgentMessage(agent="analysis", content="The bug is on line 23...")
        >>> print(msg.to_context_string())
        [ANALYSIS]:
        The bug is on line 23...
    """
    agent: str
    content: str
    
    def to_context_string(self) -> str:
        """Format this message for inclusion in LLM context.
        
        Returns:
            str: Formatted string with agent name header and content.
        """
        return f"[{self.agent.upper()}]:\n{self.content}"


@dataclass
class ConversationHistory:
    """Tracks agent outputs and tool results for context passing.
    
    Maintains a sequential record of all agent outputs and tool executions
    during a session. This history is used to provide context to each
    subsequent agent, enabling collaborative reasoning.
    
    Attributes:
        messages: List of AgentMessage objects from previous agents
        tool_results: List of tool execution records with name, args, result
        retry_context: Optional context from previous test generation attempts
    
    Example:
        >>> history = ConversationHistory()
        >>> history.add_agent_message("planner", "Suggest running tests first")
        >>> history.add_tool_result("run_tests", {}, "2 tests passed, 1 failed")
        >>> context = history.get_context_for_agent("analysis")
    """
    messages: list[AgentMessage] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    retry_context: str = ""  # Context from previous test generation attempts
    
    def add_agent_message(self, agent: str, content: str) -> None:
        """Add an agent's output to the conversation history.
        
        Args:
            agent: Name of the agent producing the output
            content: Raw text output from the agent
        """
        self.messages.append(AgentMessage(agent=agent, content=content))
    
    def add_tool_result(self, tool_name: str, args: dict, result: str) -> None:
        """Record a tool execution result in the history.
        
        Args:
            tool_name: Name of the executed tool
            args: Arguments passed to the tool
            result: String representation of tool output
        """
        self.tool_results.append({
            "tool": tool_name,
            "args": args,
            "result": result
        })
    
    def get_context_for_agent(self, current_agent: str) -> str:
        """Build a context string containing all previous agent outputs.
        
        Constructs a formatted string with all previous agent messages and
        tool results, suitable for injection into an LLM prompt.
        
        For the testwriter agent, also includes retry_context from previous
        test generation attempts if available.
        
        Args:
            current_agent: Name of the agent requesting context (for logging)
        
        Returns:
            str: Formatted context string, or empty string if no history.
        """
        context_parts = []
        
        # Include retry context for testwriter agent
        if current_agent == "testwriter" and self.retry_context:
            context_parts.append(self.retry_context)
            context_parts.append("")
        
        if self.messages:
            context_parts.append("=== PREVIOUS AGENT OUTPUTS ===")
            for msg in self.messages:
                context_parts.append(msg.to_context_string())
                context_parts.append("")  # blank line separator
        
        # Include tool results if any
        if self.tool_results:
            context_parts.append("=== TOOL EXECUTION RESULTS ===")
            for tr in self.tool_results:
                result_preview = tr["result"][:500] if len(tr["result"]) > 500 else tr["result"]
                context_parts.append(f"Tool: {tr['tool']}")
                context_parts.append(f"Args: {tr['args']}")
                context_parts.append(f"Result: {result_preview}")
                context_parts.append("")
        
        if context_parts:
            context_parts.append("=== END PREVIOUS CONTEXT ===\n")
            return "\n".join(context_parts)
        
        return ""
    
    def set_retry_context(self, context: str) -> None:
        """Set retry context from previous test generation attempts.
        
        This context will be included in the prompt for the testwriter agent.
        
        Args:
            context: Formatted context string from TestEvaluator
        """
        self.retry_context = context


@dataclass
class RunResult:
    """Result container for a completed session run.
    
    Holds all outputs from a session including agent texts, tool results,
    and any successfully parsed structured data.
    
    Attributes:
        analysis_text: Raw text output from analysis agent
        critic_text: Raw text output from critic agent
        executor_tool_name: Name of final tool executed
        executor_result: String result from final tool execution
        parsed_hypothesis: Structured SemanticHypothesis if JSON parsing succeeded
        parsed_evaluation: Structured EvaluationResult if JSON parsing succeeded
    """
    analysis_text: str
    critic_text: str
    executor_tool_name: str
    executor_result: str
    parsed_hypothesis: SemanticHypothesis | None = None
    parsed_evaluation: EvaluationResult | None = None


def parse_hypothesis_from_json(json_text: str) -> SemanticHypothesis | None:
    """Parse SemanticHypothesis from JSON output using Pydantic validation.
    
    Handles JSON wrapped in code fences (```json ... ```) and validates
    against the SemanticHypothesis schema.
    
    Args:
        json_text: JSON string from analysis agent, may include code fences
        
    Returns:
        SemanticHypothesis if parsing and validation succeed, None otherwise
    
    Example:
        >>> json_str = '{"hypothesis": "Bug on line 23", "confidence_level": "HIGH", ...}'
        >>> result = parse_hypothesis_from_json(json_str)
        >>> if result:
        ...     print(result.confidence_level)
    """
    # Strip code fences and whitespace
    sanitized = re.sub(r"```(?:json)?", "", json_text).strip()
    
    try:
        # Use Pydantic model for validation
        return SemanticHypothesis.model_validate_json(sanitized)
    except Exception as e:
        print(f"⚠️ Failed to parse hypothesis JSON: {e}")
        return None


def parse_evaluation_from_json(json_text: str) -> EvaluationResult | None:
    """Parse EvaluationResult from critic agent JSON using CriticResponse schema.
    
    Handles JSON wrapped in code fences and uses the CriticResponse schema
    for validation, then converts to simplified EvaluationResult.
    
    Args:
        json_text: JSON string from critic agent, may include code fences
        
    Returns:
        EvaluationResult if parsing and validation succeed, None otherwise
    
    Example:
        >>> json_str = '{"behavior": "reasonable", "verdict": "ACCEPT", ...}'
        >>> result = parse_evaluation_from_json(json_str)
        >>> if result:
        ...     print(result.behavior)
    """
    # Strip code fences and whitespace
    sanitized = re.sub(r"```(?:json)?", "", json_text).strip()
    
    try:
        # Use Pydantic model for validation
        critic_response = CriticResponse.model_validate_json(sanitized)
        return critic_response.to_evaluation_result()
    except Exception as e:
        print(f"⚠️ Failed to parse evaluation JSON: {e}")
        return None


class CustomSession:
    """Deterministic multi-agent orchestrator using direct LLM calls.
    
    Manages the execution of a multi-agent pipeline for bug investigation.
    Agents run in sequence, with each agent receiving context from previous
    agents via ConversationHistory. The executor agent can perform multiple
    tool calls in a loop until investigation is complete.
    
    Features:
        - Deterministic agent ordering from AgentGraph
        - Context passing between agents
        - JSON mode for structured output (analysis, critic)
        - Multi-turn tool execution with loop control
        - Task directory awareness for file operations
        - Comprehensive logging with token usage tracking
    
    Attributes:
        graph: AgentGraph defining agent sequences for each mode
        mode: Current mode ("baseline" or "agentic")
        prompts: Dict mapping agent names to their system prompts
        tools: InstrumentedTools instance for tool execution
        log_path: Path to JSONL log file
        llm: GeminiClient for LLM calls
        task_context: Optional TaskContext with source/test code
        task_dir: Resolved path to task directory for file operations
        tool_map: Mapping of tool names to wrapped methods
    
    Example:
        >>> session = CustomSession(
        ...     graph=agent_graph,
        ...     mode="agentic",
        ...     prompts={"planner": "...", "analysis": "...", ...},
        ...     tools=instrumented_tools,
        ...     log_path=Path("./logs/raw_logs.jsonl"),
        ...     llm=gemini_client,
        ...     task_context=task_context,
        ... )
        >>> result = session.run(max_iterations=5)
    """

    def __init__(
        self,
        graph: AgentGraph,
        mode: str,
        prompts: dict[str, str],
        tools: InstrumentedTools,
        log_path: Path,
        llm: GeminiClient,
        task_context: "TaskContext | None" = None,
        retry_context: str = "",
    ) -> None:
        """Initialize the session with all required components.
        
        Args:
            graph: AgentGraph defining agent sequences for each mode
            mode: Execution mode ("baseline" or "agentic")
            prompts: Dict mapping agent names to system prompt strings
            tools: InstrumentedTools instance for executing tool calls
            log_path: Path to JSONL file for logging agent interactions
            llm: GeminiClient instance for making LLM calls
            task_context: Optional TaskContext with source and test code
            retry_context: Optional context from previous test generation attempts
        """
        self.graph = graph
        self.mode = mode
        self.prompts = prompts
        self.tools = tools
        self.log_path = log_path
        self.llm = llm
        self.task_context = task_context
        self.retry_context = retry_context
        
        # Determine task directory from TaskContextV2 paths
        # TaskContextV2 has buggy_path like: evaluation/tasks_v2/boundary_threshold/buggy
        # Task dir is parent of buggy_path: evaluation/tasks_v2/boundary_threshold
        self.task_dir: Path | None = None
        if task_context and hasattr(task_context, 'buggy_path'):
            # Use buggy_path.parent for TaskContextV2 (tasks_v2 structure)
            self.task_dir = task_context.buggy_path.parent
            if not self.task_dir.exists():
                print(f"⚠️ Task directory not found: {self.task_dir}")
                self.task_dir = None
            else:
                print(f"📁 Task directory: {self.task_dir}")
        
        # Create tool map with task-aware tools
        self.tool_map = {
            "run_tests": self._run_tests_in_task_dir,
            "read_file": self._read_file_in_task_dir,
            "read_file_window": self._read_file_window_in_task_dir,
            "list_files": self._list_files_in_task_dir,
            "log_event": self.tools.log_event_wrapped,
            "write_test_file": self._write_test_file_in_run_dir,
        }
    
    def _write_test_file_in_run_dir(
        self,
        output_dir: str | Path,
        filename: str,
        content: str,
        attempt: int = 1
    ) -> dict:
        """Write generated test file to BOTH run directory AND buggy directory.
        
        The test file is written to:
        1. runs/<task>/<run_id>/generated_tests/ - for archival
        2. task_dir/buggy/ - for immediate pytest execution (same dir as source.py)
        
        Args:
            output_dir: Relative directory (typically "generated_tests")
            filename: Test file name
            content: Python test code
            attempt: Attempt number for isolation
        
        Returns:
            dict: Result with success, path, error keys
        """
        # Use run directory's generated_tests folder for archival
        # log_path is: /project/runs/<task>/<run_id>/raw_logs.jsonl
        run_dir = self.log_path.parent
        target_dir = run_dir / output_dir
        result = self.tools.write_test_file(target_dir, filename, content, attempt)
        
        # ALSO write to task_dir/buggy for pytest discovery
        # Tests need to be in same dir as source.py for imports to work
        if self.task_dir and result.get("success"):
            try:
                buggy_dir = self.task_dir / "buggy"
                if buggy_dir.exists():
                    task_test_path = buggy_dir / filename
                    task_test_path.write_text(content, encoding="utf-8")
                    result["task_dir_path"] = str(task_test_path)
            except Exception as e:
                # Don't fail if task_dir write fails - we still have the runs/ copy
                result["task_dir_error"] = str(e)
        
        return result
    
    def _get_task_path(self, path: str | Path) -> Path:
        """Convert a relative path to absolute path within task directory.
        
        Args:
            path: Relative or absolute file path
        
        Returns:
            Path: Absolute path, resolved within task_dir if relative
        """
        path = Path(path) if isinstance(path, str) else path
        if self.task_dir and not path.is_absolute():
            return self.task_dir / path
        return path
    
    def _run_tests_in_task_dir(self, command: list[str] | None = None, cwd: Path | str | None = None) -> dict:
        """Run tests in the task's buggy directory.
        
        Tests are run in buggy/ subdirectory where source.py lives,
        so imports work correctly.
        
        Args:
            command: Test command (defaults to pytest)
            cwd: Working directory (defaults to task_dir/buggy)
        
        Returns:
            dict: Test output with stdout, stderr, returncode
        """
        if cwd is None and self.task_dir:
            # Run in buggy/ directory where source.py and tests live
            buggy_dir = self.task_dir / "buggy"
            cwd = buggy_dir if buggy_dir.exists() else self.task_dir
        elif isinstance(cwd, str):
            cwd = self._get_task_path(cwd)
        return self.tools.run_tests(command=command, cwd=cwd)
    
    def _read_file_in_task_dir(self, path: str | Path) -> str:
        """Read file from task directory.
        
        Args:
            path: File path (relative paths resolved to task_dir)
        
        Returns:
            str: File content or error string
        """
        return self.tools.read_file(self._get_task_path(path))
    
    def _read_file_window_in_task_dir(self, path: str | Path, start: int, end: int) -> str:
        """Read file line range from task directory.
        
        Args:
            path: File path (relative paths resolved to task_dir)
            start: Starting line number (1-indexed)
            end: Ending line number (1-indexed)
        
        Returns:
            str: Lines from file or error string
        """
        return self.tools.read_file_window(self._get_task_path(path), start, end)
    
    def _list_files_in_task_dir(self, root: str | Path | None = None, path: str | Path | None = None) -> list[str]:
        """List files in task directory.
        
        Args:
            root: Directory path (legacy arg name)
            path: Directory path (LLM-friendly arg name)
        
        Returns:
            list[str]: Sorted list of file paths
        """
        dir_path = path or root or "."
        return self.tools.list_files(root=self._get_task_path(dir_path))

    def run(self, max_iterations: int = 5) -> RunResult:
        """Run the agent pipeline with optional multi-turn execution.
        
        Executes agents in sequence as defined by the AgentGraph mode.
        Each agent receives context from previous agents. The executor
        agent can perform multiple tool calls until investigation completes.
        
        Args:
            max_iterations: Maximum tool execution iterations for executor (default: 5)
        
        Returns:
            RunResult: Container with all agent outputs and parsed structures
        
        Flow:
            1. For each agent in mode sequence:
               - Build context from previous agents
               - Call LLM with agent prompt + context
               - Log response and add to history
               - Parse structured output for analysis/critic
            2. Execute tool loop:
               - Parse executor JSON for tool call
               - Execute tool and log result
               - If continue=true, get next executor action
               - Repeat until continue=false or max iterations
        """
        mode_def = self.graph.modes[self.mode]
        analysis_text = ""
        critic_text = ""
        executor_reply = ""
        parsed_hypothesis: SemanticHypothesis | None = None
        parsed_evaluation: EvaluationResult | None = None
        all_tool_results: list[str] = []
        
        # Initialize conversation history for context passing
        history = ConversationHistory()
        
        # Set retry context from previous attempts if available
        if self.retry_context:
            history.set_retry_context(self.retry_context)
            print(f"📋 Retry context loaded from previous attempts")
        
        # Build initial user message with task context
        if self.task_context:
            base_user_message = self.task_context.to_prompt_context()
        else:
            base_user_message = "Proceed."

        for agent_name in mode_def.agents:
            prompt = self.prompts[agent_name]
            emit_log_entry(self.log_path, build_log_entry(agent=agent_name, role="system", content=prompt))

            # Build user message with previous agent context
            previous_context = history.get_context_for_agent(agent_name)
            if previous_context:
                user_message = f"{previous_context}\n{base_user_message}"
            else:
                user_message = base_user_message

            # Live console output
            print(f"\n{'='*50}")
            print(f"🤖 [{agent_name.upper()}] calling LLM...")
            if previous_context:
                print(f"📋 Context from {len(history.messages)} previous agent(s)")
            
            # Use JSON mode for analysis and critic agents, regular mode for others
            start_time = time.perf_counter()
            if agent_name == "analysis":
                print("📊 Using JSON mode with SemanticHypothesis schema...")
                try:
                    llm_response = self.llm.generate_json(
                        system=prompt, user=user_message, response_schema=SemanticHypothesis
                    )
                except Exception as e:
                    print(f"⚠️ JSON mode failed, falling back to regular: {e}")
                    llm_response = self.llm.generate(system=prompt, user=user_message)
            elif agent_name == "critic":
                print("📊 Using JSON mode with CriticResponse schema...")
                try:
                    llm_response = self.llm.generate_json(
                        system=prompt, user=user_message, response_schema=CriticResponse
                    )
                except Exception as e:
                    print(f"⚠️ JSON mode failed, falling back to regular: {e}")
                    llm_response = self.llm.generate(system=prompt, user=user_message)
            else:
                llm_response = self.llm.generate(system=prompt, user=user_message)
            duration = time.perf_counter() - start_time
            
            reply = llm_response.text
            token_usage = TokenUsage(
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
            )
            
            # Add this agent's output to history for next agents
            history.add_agent_message(agent_name, reply)
            
            # Show truncated response with token info
            preview = reply[:300] + "..." if len(reply) > 300 else reply
            print(f"📝 Response ({len(reply)} chars) in {duration:.2f}s | 🎟️ {token_usage.total_tokens} tokens")
            print(preview)
            
            emit_log_entry(self.log_path, build_log_entry(
                agent=agent_name, role="assistant", content=reply, 
                duration_seconds=round(duration, 3), token_usage=token_usage
            ))

            if agent_name == "analysis":
                analysis_text = reply
                # Try to parse structured hypothesis from JSON
                parsed_hypothesis = parse_hypothesis_from_json(reply)
                if parsed_hypothesis:
                    print(f"✅ Parsed hypothesis: {parsed_hypothesis.hypothesis[:100]}...")
                    print(f"   Confidence: {parsed_hypothesis.confidence_level}")
            if agent_name == "critic":
                critic_text = reply
                # Try to parse structured evaluation from JSON
                parsed_evaluation = parse_evaluation_from_json(reply)
                if parsed_evaluation:
                    print(f"✅ Parsed evaluation: behavior={parsed_evaluation.behavior}")
                    if parsed_evaluation.failure_type:
                        print(f"   Failure type: {parsed_evaluation.failure_type}")
            if agent_name == "executor":
                executor_reply = reply
            # Also capture testwriter output for baseline mode (testwriter can call tools)
            if agent_name == "testwriter":
                executor_reply = reply
                # Execute TestWriter's tool call immediately (write_test_file)
                # This ensures the test file is created BEFORE executor's run_tests
                tool_name, tool_args, tool_result, _ = self._execute_tool_with_continue(reply)
                if tool_name == "write_test_file" and "success" in str(tool_result):
                    history.add_tool_result(tool_name, tool_args, tool_result)
                    all_tool_results.append(tool_result)
                    print(f"✅ TestWriter tool executed: {tool_name}")
                    result_preview = str(tool_result)[:200] + "..." if len(str(tool_result)) > 200 else str(tool_result)
                    print(f"📤 Result: {result_preview}")

        # Multi-turn execution loop
        iteration = 0
        should_continue = True
        last_tool_name = ""
        last_tool_result = ""
        
        while should_continue and iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*50}")
            print(f"🔧 Executing tool (iteration {iteration}/{max_iterations})...")
            
            tool_name, tool_args, tool_result, should_continue = self._execute_tool_with_continue(executor_reply)
            last_tool_name = tool_name
            last_tool_result = tool_result
            all_tool_results.append(tool_result)
            
            # Add tool result to history
            history.add_tool_result(tool_name, tool_args, tool_result)
            
            print(f"✅ Tool: {tool_name}")
            result_preview = str(tool_result)[:200] + "..." if len(str(tool_result)) > 200 else str(tool_result)
            print(f"📤 Result: {result_preview}")
            
            if should_continue and iteration < max_iterations:
                print(f"\n🔄 Continuing investigation...")
                # Get next action from executor with updated context
                executor_reply = self._get_next_executor_action(history, base_user_message)
            elif should_continue:
                print(f"\n⚠️ Max iterations ({max_iterations}) reached")
                should_continue = False
            else:
                print(f"\n✅ Investigation complete")

        return RunResult(
            analysis_text=analysis_text,
            critic_text=critic_text,
            executor_tool_name=last_tool_name,
            executor_result=last_tool_result,
            parsed_hypothesis=parsed_hypothesis,
            parsed_evaluation=parsed_evaluation,
        )

    def _get_next_executor_action(self, history: ConversationHistory, base_user_message: str) -> str:
        """Get next executor action based on accumulated tool results.
        
        Called during multi-turn execution when executor needs to decide
        the next action after a tool has returned results.
        
        Args:
            history: ConversationHistory with all previous agent outputs and tool results
            base_user_message: Original user message with task context
        
        Returns:
            str: Raw executor response with next tool call JSON
        """
        prompt = self.prompts["executor"]
        previous_context = history.get_context_for_agent("executor")
        user_message = f"{previous_context}\n{base_user_message}\n\nBased on the tool results above, decide your next action."
        
        print(f"\n{'='*50}")
        print(f"🤖 [EXECUTOR] deciding next action...")
        
        start_time = time.perf_counter()
        llm_response = self.llm.generate(system=prompt, user=user_message)
        duration = time.perf_counter() - start_time
        
        reply = llm_response.text
        token_usage = TokenUsage(
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
        )
        
        preview = reply[:300] + "..." if len(reply) > 300 else reply
        print(f"📝 Response ({len(reply)} chars) in {duration:.2f}s | 🎟️ {token_usage.total_tokens} tokens")
        print(preview)
        
        emit_log_entry(self.log_path, build_log_entry(
            agent="executor", role="assistant", content=reply, 
            duration_seconds=round(duration, 3), token_usage=token_usage
        ))
        history.add_agent_message("executor", reply)
        
        return reply

    def _execute_tool_with_continue(self, executor_reply: str) -> tuple[str, dict, str, bool]:
        """Parse executor JSON response and invoke the requested tool.
        
        Parses the executor's JSON output to extract tool name, arguments,
        and continue flag, then executes the tool and returns results.
        
        Args:
            executor_reply: Raw JSON string from executor agent
        
        Returns:
            tuple: (tool_name, args_dict, result_string, should_continue)
                - tool_name: Name of executed tool
                - args_dict: Arguments passed to tool
                - result_string: String representation of tool output
                - should_continue: Whether executor wants another iteration
        
        Note:
            - Handles code fences in JSON
            - Falls back to log_event on parse errors
            - log_event always sets should_continue=False
        """
        # Strip code fences and whitespace
        sanitized = re.sub(r"```(?:json)?", "", executor_reply).strip()
        
        try:
            payload = json.loads(sanitized)
        except json.JSONDecodeError:
            # Fallback: log_event with raw reply
            emit_log_entry(
                self.log_path,
                build_log_entry(agent="executor", role="error", content=f"Invalid JSON: {executor_reply}"),
            )
            return "log_event", {}, str({"error": "parse_failed", "raw": executor_reply}), False

        tool_name = payload.get("tool", "log_event")
        args = payload.get("args", {})
        should_continue = payload.get("continue", False)
        
        # log_event always stops the loop
        if tool_name == "log_event":
            should_continue = False
        
        tool_fn = self.tool_map.get(tool_name)
        if not tool_fn:
            result = {"error": f"unknown tool: {tool_name}"}
        else:
            try:
                result = tool_fn(**args)
            except TypeError as exc:
                result = {"error": f"invalid args for {tool_name}: {exc}"}

        emit_log_entry(
            self.log_path,
            build_log_entry(agent="executor", role="assistant", content=str(result), tool_name=tool_name),
        )
        return tool_name, args, str(result), should_continue

    def _execute_tool(self, executor_reply: str) -> tuple[str, dict, str]:
        """Legacy method for single tool execution (backward compatibility).
        
        Simple wrapper around _execute_tool_with_continue that drops the
        continue flag for code expecting the old 3-tuple return.
        
        Args:
            executor_reply: Raw JSON string from executor agent
        
        Returns:
            tuple: (tool_name, args_dict, result_string)
        """
        tool_name, args, result, _ = self._execute_tool_with_continue(executor_reply)
        return tool_name, args, result


class SummaryBuilder:
    """Builder class for constructing Summary objects from run results.
    
    Handles both structured (JSON-parsed) and unstructured (raw text) inputs,
    providing fallback behavior when parsing fails.
    
    Attributes:
        model_id: LLM model identifier used for the run
        tool_call_count: Total number of tool invocations
        hypothesis_text: Raw analysis agent output text
        evaluation_text: Raw critic agent output text
        parsed_hypothesis: Structured SemanticHypothesis if available
        parsed_evaluation: Structured EvaluationResult if available
    
    Example:
        >>> builder = SummaryBuilder(
        ...     model_id="gemini-2.0-flash",
        ...     tool_call_count=5,
        ...     hypothesis_text="Bug found on line 23...",
        ...     evaluation_text="Analysis is reasonable...",
        ...     parsed_hypothesis=hypothesis_obj,
        ...     parsed_evaluation=eval_obj,
        ... )
        >>> summary = builder.build(timestamp="2026-01-01T12:00:00Z")
    """
    
    def __init__(
        self,
        model_id: str,
        tool_call_count: int,
        hypothesis_text: str,
        evaluation_text: str,
        parsed_hypothesis: SemanticHypothesis | None = None,
        parsed_evaluation: EvaluationResult | None = None,
    ) -> None:
        """Initialize builder with run results.
        
        Args:
            model_id: Identifier of LLM model used
            tool_call_count: Total tool invocations during run
            hypothesis_text: Raw text from analysis agent
            evaluation_text: Raw text from critic agent
            parsed_hypothesis: Structured hypothesis if JSON parsing succeeded
            parsed_evaluation: Structured evaluation if JSON parsing succeeded
        """
        self.model_id = model_id
        self.tool_call_count = tool_call_count
        self.hypothesis_text = hypothesis_text
        self.evaluation_text = evaluation_text
        self.parsed_hypothesis = parsed_hypothesis
        self.parsed_evaluation = parsed_evaluation

    def build(self, timestamp: str) -> Summary:
        """Construct a Summary object with available data.
        
        Uses parsed structured data if available, otherwise creates
        fallback objects from raw text.
        
        Args:
            timestamp: ISO 8601 timestamp for the summary
        
        Returns:
            Summary: Complete summary object ready for serialization
        """
        # Use parsed hypothesis if available, otherwise create fallback
        if self.parsed_hypothesis:
            hypothesis = self.parsed_hypothesis
        else:
            hypothesis = SemanticHypothesis(
                hypothesis=self.hypothesis_text,
                confidence_level="LOW",
                assumptions=[],
                evidence=[],
                what_might_be_missing="",
                next_question="",
            )
        
        # Use parsed evaluation if available, otherwise create fallback
        if self.parsed_evaluation:
            evaluation = self.parsed_evaluation
        else:
            evaluation = EvaluationResult(
                behavior="reasonable",
                failure_type="",
                commentary=self.evaluation_text,
            )
        return Summary(
            hypothesis=hypothesis,
            evaluation=evaluation,
            model_id=self.model_id,
            timestamp=timestamp,
            tool_call_count=self.tool_call_count,
        )


@dataclass
class TestGenerationResult:
    """Result from a single test generation attempt.
    
    Attributes:
        attempt: Attempt number (1-indexed)
        test_file: Path to generated test file
        test_code: Generated test code content
        is_bug_revealing: Whether test is bug-revealing
        buggy_failed: Did test fail on buggy code
        fixed_passed: Did test pass on fixed code
        evaluation: Full TestEvaluationResult if available
    """
    attempt: int
    test_file: Path | None
    test_code: str
    is_bug_revealing: bool
    buggy_failed: bool
    fixed_passed: bool
    evaluation: "TestEvaluationResult | None" = None


@dataclass
class TestGenerationSessionResult:
    """Final result from test generation session with retries.
    
    Attributes:
        success: Whether a bug-revealing test was generated
        attempts: Total number of attempts made
        results: List of all attempt results
        final_test_file: Path to successful test file (if any)
    """
    success: bool
    attempts: int
    results: list[TestGenerationResult]
    final_test_file: Path | None = None


class TestGenerationSession:
    """Session for test generation with retry logic.
    
    Manages the retry loop for generating bug-revealing tests:
    1. Run agent pipeline to generate test
    2. Validate test against buggy/fixed code
    3. If not bug-revealing, get feedback from TestEvaluator
    4. Inject feedback as retry_context for next attempt
    5. Run Reflection → TestWriter to improve test
    6. Repeat until success or max retries
    
    Attributes:
        graph: AgentGraph defining agent sequences
        mode: Execution mode ("baseline" or "agentic")
        prompts: Dict of agent prompts
        tools: InstrumentedTools for tool execution
        log_path: Path to JSONL log file
        llm: GeminiClient for LLM calls
        task_context: TaskContextV2 with buggy/fixed code
        test_evaluator: TestEvaluator for LLM-based evaluation
        max_retries: Maximum retry attempts
        test_timeout: Timeout for test execution (seconds)
    
    Example:
        >>> session = TestGenerationSession(
        ...     graph=graph,
        ...     mode="agentic",
        ...     prompts=prompts,
        ...     tools=tools,
        ...     log_path=log_path,
        ...     llm=llm,
        ...     task_context=task_context_v2,
        ...     test_evaluator=evaluator,
        ...     max_retries=3,
        ... )
        >>> result = session.run()
        >>> if result.success:
        ...     print(f"Bug-revealing test: {result.final_test_file}")
    """
    
    def __init__(
        self,
        graph: AgentGraph,
        mode: str,
        prompts: dict[str, str],
        tools: InstrumentedTools,
        log_path: Path,
        llm: GeminiClient,
        task_context: "TaskContextV2",
        test_evaluator: "TestEvaluator",
        max_retries: int = 3,
        test_timeout: int = 60,
    ) -> None:
        """Initialize test generation session.
        
        Args:
            graph: AgentGraph with mode definitions
            mode: "baseline" or "agentic"
            prompts: Agent prompts dict
            tools: Instrumented tools instance
            log_path: Path for logging
            llm: LLM client
            task_context: V2 task context with buggy/fixed paths
            test_evaluator: TestEvaluator for validation feedback
            max_retries: Max retry attempts (default: 3)
            test_timeout: Test execution timeout (default: 60s)
        """
        self.graph = graph
        self.mode = mode
        self.prompts = prompts
        self.tools = tools
        self.log_path = log_path
        self.llm = llm
        self.task_context = task_context
        self.test_evaluator = test_evaluator
        self.max_retries = max_retries
        self.test_timeout = test_timeout
        
        # Track all attempts
        self.attempt_results: list[TestGenerationResult] = []
    
    def run(self) -> TestGenerationSessionResult:
        """Run test generation with retry loop.
        
        Attempts to generate a bug-revealing test, retrying with
        feedback from TestEvaluator on failure.
        
        Returns:
            TestGenerationSessionResult with success status and all attempts
        """
        from task_loader import run_test_on_both_versions
        
        retry_context = ""
        
        for attempt in range(1, self.max_retries + 1):
            print(f"\n{'='*60}")
            print(f"🧪 TEST GENERATION ATTEMPT {attempt}/{self.max_retries}")
            print(f"{'='*60}")
            
            # Run agent pipeline with retry context
            session = CustomSession(
                graph=self.graph,
                mode=self.mode,
                prompts=self.prompts,
                tools=self.tools,
                log_path=self.log_path,
                llm=self.llm,
                task_context=self.task_context,
                retry_context=retry_context,
            )
            run_result = session.run()
            
            # Find generated test file
            run_dir = self.log_path.parent
            generated_tests_dir = run_dir / "generated_tests"
            test_file = self._find_latest_test_file(generated_tests_dir)
            
            if not test_file:
                print(f"⚠️ No test file generated in attempt {attempt}")
                result = TestGenerationResult(
                    attempt=attempt,
                    test_file=None,
                    test_code="",
                    is_bug_revealing=False,
                    buggy_failed=False,
                    fixed_passed=False,
                )
                self.attempt_results.append(result)
                retry_context = self._build_no_test_retry_context(attempt)
                continue
            
            test_code = test_file.read_text(encoding="utf-8")
            print(f"📄 Generated test: {test_file.name}")
            
            # Validate against buggy/fixed code
            print(f"🔬 Validating test...")
            validation = run_test_on_both_versions(
                test_file_path=test_file,
                buggy_dir=self.task_context.buggy_path,
                fixed_dir=self.task_context.fixed_path,
                timeout=self.test_timeout,
            )
            
            is_bug_revealing = validation["is_bug_revealing"]
            buggy_failed = validation["buggy_failed"]
            fixed_passed = validation["fixed_passed"]
            
            # Show validation result
            brtr_emoji = "🎯" if is_bug_revealing else "❌"
            print(f"{brtr_emoji} Validation: buggy_fail={buggy_failed}, "
                  f"fixed_pass={fixed_passed} → bug_revealing={is_bug_revealing}")
            
            # Run LLM evaluation for feedback
            buggy_output = (
                validation["buggy_result"]["stdout"] + "\n" +
                validation["buggy_result"]["stderr"]
            )
            fixed_output = (
                validation["fixed_result"]["stdout"] + "\n" +
                validation["fixed_result"]["stderr"]
            )
            
            eval_result = self.test_evaluator.evaluate_test(
                task_id=self.task_context.task_id,
                attempt=attempt,
                test_file=str(test_file),
                test_code=test_code,
                buggy_output=buggy_output,
                fixed_output=fixed_output,
                bug_description=self.task_context.get_bug_description(),
            )
            
            result = TestGenerationResult(
                attempt=attempt,
                test_file=test_file,
                test_code=test_code,
                is_bug_revealing=is_bug_revealing,
                buggy_failed=buggy_failed,
                fixed_passed=fixed_passed,
                evaluation=eval_result,
            )
            self.attempt_results.append(result)
            
            if is_bug_revealing:
                print(f"✅ SUCCESS! Bug-revealing test generated on attempt {attempt}")
                return TestGenerationSessionResult(
                    success=True,
                    attempts=attempt,
                    results=self.attempt_results,
                    final_test_file=test_file,
                )
            
            # Get retry context from evaluator
            print(f"🔄 Getting feedback for retry...")
            print(f"   Category: {eval_result.failure_category}")
            print(f"   Suggestion: {eval_result.retry_guidance.suggestion[:100]}...")
            
            retry_context = self.test_evaluator.get_retry_context(
                self.task_context.task_id
            )
            
            # Log retry
            emit_log_entry(
                self.log_path,
                build_log_entry(
                    agent="retry_controller",
                    role="system",
                    content=f"Attempt {attempt} failed: {eval_result.failure_category}. "
                            f"Suggestion: {eval_result.retry_guidance.suggestion}",
                ),
            )
        
        # All retries exhausted
        print(f"\n❌ Failed to generate bug-revealing test after {self.max_retries} attempts")
        return TestGenerationSessionResult(
            success=False,
            attempts=self.max_retries,
            results=self.attempt_results,
            final_test_file=None,
        )
    
    def _find_latest_test_file(self, generated_tests_dir: Path) -> Path | None:
        """Find the most recently generated test file."""
        if not generated_tests_dir.exists():
            return None
        
        test_files = list(generated_tests_dir.glob("test_*.py"))
        if not test_files:
            return None
        
        # Sort by modification time, return latest
        return max(test_files, key=lambda f: f.stat().st_mtime)
    
    def _build_no_test_retry_context(self, attempt: int) -> str:
        """Build retry context when no test file was generated."""
        return f"""=== PREVIOUS TEST GENERATION ATTEMPTS ===
Total attempts so far: {attempt}

### Attempt {attempt}
- Result: no_test_generated
- Bug-Revealing: ✗
- Analysis: No test file was written to generated_tests/ directory
- Suggestion: Ensure you call write_test_file tool with valid content

=== USE THIS FEEDBACK TO IMPROVE YOUR TEST ===
IMPORTANT: You MUST call the write_test_file tool to create the test file.
"""
