"""
Minimal agent loop.

The loop is simple:
  1. Send messages + tool schemas to LLM
  2. If LLM returns tool_calls → execute them, add results, go to 1
  3. If LLM returns text only → done

No LangGraph, no state machines, no middleware.
Just a while loop with tool dispatch.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional

from bugtest.deep.llm import LLMClient, LLMResponse
from bugtest.deep.tools import get_tool_schemas, execute_tool


@dataclass
class AgentResult:
    """Result of an agent run."""
    status: str  # completed, error, timeout, max_steps
    messages: list[dict] = field(default_factory=list)
    final_response: str = ""
    error: Optional[str] = None
    steps_used: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    duration_seconds: float = 0.0


class Agent:
    """
    Minimal ReAct agent with tool calling.

    Usage:
        agent = Agent(
            llm=LLMClient("nvidia:meta/llama-3.3-70b-instruct"),
            system_prompt="You are a test generator...",
            tools=["run_tests", "safe_edit_file", "read_file"],
            workspace="/path/to/project",
        )
        result = agent.run("Write tests for calculator.py")
    """

    def __init__(
        self,
        llm: LLMClient,
        system_prompt: str,
        tools: Optional[list[str]] = None,
        workspace: str = ".",
        max_steps: int = 15,
        timeout_seconds: int = 120,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.tools = tools
        self.workspace = workspace
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.context: dict = {"consecutive_failures": 0}

    def run(self, user_message: str) -> AgentResult:
        """Run the agent loop until completion or limits reached."""
        start_time = time.time()

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        tool_schemas = get_tool_schemas(self.tools) if self.tools else get_tool_schemas()
        steps = 0
        total_prompt = 0
        total_completion = 0

        while steps < self.max_steps:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                return AgentResult(
                    status="timeout",
                    messages=messages,
                    error=f"Agent timed out after {elapsed:.0f}s",
                    steps_used=steps,
                    total_prompt_tokens=total_prompt,
                    total_completion_tokens=total_completion,
                    duration_seconds=elapsed,
                )

            # Call LLM — on last step, don't provide tools so it gives final text
            use_tools = tool_schemas if (tool_schemas and steps < self.max_steps - 1) else None

            try:
                response = self.llm.chat(
                    messages=messages,
                    tools=use_tools,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as e:
                return AgentResult(
                    status="error",
                    messages=messages,
                    error=f"LLM call failed: {str(e)}",
                    steps_used=steps,
                    total_prompt_tokens=total_prompt,
                    total_completion_tokens=total_completion,
                    duration_seconds=time.time() - start_time,
                )

            total_prompt += response.prompt_tokens
            total_completion += response.completion_tokens
            steps += 1

            # No tool calls → agent is done
            if not response.tool_calls:
                messages.append({"role": "assistant", "content": response.content})
                return AgentResult(
                    status="completed",
                    messages=messages,
                    final_response=response.content,
                    steps_used=steps,
                    total_prompt_tokens=total_prompt,
                    total_completion_tokens=total_completion,
                    duration_seconds=time.time() - start_time,
                )

            # Has tool calls → execute them
            # OSS models on NVIDIA build sometimes mishandle parallel tool calls;
            # Claude handles them correctly. Cap only for non-Claude models.
            is_claude = self.llm.model.startswith("claude:")
            if is_claude:
                tool_calls = response.tool_calls
            else:
                tool_calls = response.tool_calls[:1]

            # Add assistant message with tool calls
            assistant_msg = {"role": "assistant", "content": response.content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                }
                for tc in tool_calls
            ]
            messages.append(assistant_msg)

            # Execute each tool call
            for tc in tool_calls:
                result = execute_tool(
                    name=tc["name"],
                    arguments=tc["arguments"],
                    workspace=self.workspace,
                    context=self.context,
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        # Max steps reached
        return AgentResult(
            status="max_steps",
            messages=messages,
            error=f"Reached max_steps ({self.max_steps})",
            steps_used=steps,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            duration_seconds=time.time() - start_time,
        )


def run_subagent(
    llm: LLMClient,
    system_prompt: str,
    user_message: str,
    tools: Optional[list[str]] = None,
    workspace: str = ".",
    max_steps: int = 5,
    timeout_seconds: int = 60,
) -> str:
    """Run a subagent and return its final text response."""
    agent = Agent(
        llm=llm,
        system_prompt=system_prompt,
        tools=tools,
        workspace=workspace,
        max_steps=max_steps,
        timeout_seconds=timeout_seconds,
    )
    result = agent.run(user_message)
    return result.final_response or result.error or "Subagent returned no response."
