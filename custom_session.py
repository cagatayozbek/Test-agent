"""Custom orchestrator session - main experimental pipeline.

This module replaces DeepAgents with a deterministic custom loop.
DeepAgents exhibited non-terminating internal loops (see docs/deepagents_failure.md).
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
from schemas import EvaluationResult, Summary, SemanticHypothesis, TokenUsage
from graph_loader import AgentGraph
from llm_client import GeminiClient, LLMResponse

if TYPE_CHECKING:
    from task_loader import TaskContext


@dataclass
class AgentMessage:
    """A message from an agent in the conversation history."""
    agent: str
    content: str
    
    def to_context_string(self) -> str:
        """Format this message for inclusion in context."""
        return f"[{self.agent.upper()}]:\n{self.content}"


@dataclass
class ConversationHistory:
    """Tracks agent outputs for context passing."""
    messages: list[AgentMessage] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    
    def add_agent_message(self, agent: str, content: str) -> None:
        """Add an agent's output to history."""
        self.messages.append(AgentMessage(agent=agent, content=content))
    
    def add_tool_result(self, tool_name: str, args: dict, result: str) -> None:
        """Add a tool execution result to history."""
        self.tool_results.append({
            "tool": tool_name,
            "args": args,
            "result": result
        })
    
    def get_context_for_agent(self, current_agent: str) -> str:
        """Build context string with all previous agent outputs."""
        if not self.messages:
            return ""
        
        context_parts = ["=== PREVIOUS AGENT OUTPUTS ==="]
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
        
        context_parts.append("=== END PREVIOUS CONTEXT ===\n")
        return "\n".join(context_parts)


@dataclass
class RunResult:
    analysis_text: str
    critic_text: str
    executor_tool_name: str
    executor_result: str
    parsed_hypothesis: SemanticHypothesis | None = None  # Structured hypothesis if parsing succeeded


def parse_hypothesis_from_json(json_text: str) -> SemanticHypothesis | None:
    """Parse SemanticHypothesis from JSON output.
    
    Args:
        json_text: JSON string from analysis agent (may include code fences)
        
    Returns:
        SemanticHypothesis if parsing succeeds, None otherwise
    """
    # Strip code fences and whitespace
    sanitized = re.sub(r"```(?:json)?", "", json_text).strip()
    
    try:
        data = json.loads(sanitized)
        
        # Validate and normalize confidence_level
        confidence = data.get("confidence_level", "LOW").upper()
        if confidence not in ("LOW", "MEDIUM", "HIGH"):
            confidence = "LOW"
        
        return SemanticHypothesis(
            hypothesis=data.get("hypothesis", ""),
            confidence_level=confidence,
            assumptions=data.get("assumptions", []),
            evidence=data.get("evidence", []),
            what_might_be_missing=data.get("what_might_be_missing", ""),
            next_question=data.get("next_question", ""),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"⚠️ Failed to parse hypothesis JSON: {e}")
        return None


class CustomSession:
    """Deterministic multi-agent orchestrator using direct LLM calls."""

    def __init__(
        self,
        graph: AgentGraph,
        mode: str,
        prompts: dict[str, str],
        tools: InstrumentedTools,
        log_path: Path,
        llm: GeminiClient,
        task_context: "TaskContext | None" = None,
    ) -> None:
        self.graph = graph
        self.mode = mode
        self.prompts = prompts
        self.tools = tools
        self.log_path = log_path
        self.llm = llm
        self.task_context = task_context
        
        # Determine task directory
        # log_path is like: /project/runs/<task>/<run_id>/raw_logs.jsonl
        # Task dir is: /project/evaluation/tasks/<task_id>/
        self.task_dir: Path | None = None
        if task_context:
            # Go up 4 levels: raw_logs.jsonl -> run_id -> task -> runs -> project_root
            project_root = self.log_path.parent.parent.parent.parent
            self.task_dir = project_root / "evaluation" / "tasks" / task_context.task_id
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
        }
    
    def _get_task_path(self, path: str | Path) -> Path:
        """Convert a relative path to absolute path within task directory."""
        path = Path(path) if isinstance(path, str) else path
        if self.task_dir and not path.is_absolute():
            return self.task_dir / path
        return path
    
    def _run_tests_in_task_dir(self, command: list[str] | None = None, cwd: Path | str | None = None) -> dict:
        """Run tests in the task directory if available."""
        if cwd is None and self.task_dir:
            cwd = self.task_dir
        elif isinstance(cwd, str):
            cwd = self._get_task_path(cwd)
        return self.tools.run_tests(command=command, cwd=cwd)
    
    def _read_file_in_task_dir(self, path: str | Path) -> str:
        """Read file from task directory."""
        return self.tools.read_file(self._get_task_path(path))
    
    def _read_file_window_in_task_dir(self, path: str | Path, start: int, end: int) -> str:
        """Read file window from task directory."""
        return self.tools.read_file_window(self._get_task_path(path), start, end)
    
    def _list_files_in_task_dir(self, root: str | Path | None = None, path: str | Path | None = None) -> list[str]:
        """List files in task directory."""
        dir_path = path or root or "."
        return self.tools.list_files(root=self._get_task_path(dir_path))

    def run(self, max_iterations: int = 5) -> RunResult:
        """Run the agent pipeline with optional multi-turn execution.
        
        Args:
            max_iterations: Maximum number of tool execution iterations (default: 5)
        """
        mode_def = self.graph.modes[self.mode]
        analysis_text = ""
        critic_text = ""
        executor_reply = ""
        parsed_hypothesis: SemanticHypothesis | None = None
        all_tool_results: list[str] = []
        
        # Initialize conversation history for context passing
        history = ConversationHistory()
        
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
            
            # Use JSON mode for analysis agent, regular mode for others
            start_time = time.perf_counter()
            if agent_name == "analysis":
                print("📊 Using JSON mode for structured output...")
                try:
                    llm_response = self.llm.generate_json(system=prompt, user=user_message)
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
            if agent_name == "executor":
                executor_reply = reply

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
        )

    def _get_next_executor_action(self, history: ConversationHistory, base_user_message: str) -> str:
        """Get next executor action based on tool results."""
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
        """Parse executor JSON and invoke the requested tool.
        
        Returns:
            tuple of (tool_name, args_dict, result_string, should_continue)
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
        """Legacy method for single tool execution (backward compatibility)."""
        tool_name, args, result, _ = self._execute_tool_with_continue(executor_reply)
        return tool_name, args, result


class SummaryBuilder:
    def __init__(
        self,
        model_id: str,
        tool_call_count: int,
        hypothesis_text: str,
        evaluation_text: str,
        parsed_hypothesis: SemanticHypothesis | None = None,
    ) -> None:
        self.model_id = model_id
        self.tool_call_count = tool_call_count
        self.hypothesis_text = hypothesis_text
        self.evaluation_text = evaluation_text
        self.parsed_hypothesis = parsed_hypothesis

    def build(self, timestamp: str) -> Summary:
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
