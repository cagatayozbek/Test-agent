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
    # v2.0 instrumentation — populated by Agent.run; surfaces into RunRecord.
    tool_call_count: int = 0
    tool_failure_mode_count: dict = field(default_factory=dict)
    reasoning_filled: bool = False
    prompt_version: str = ""
    prompt_template_hash: str = ""
    capabilities_used: dict = field(default_factory=dict)
    tool_choice_mode: str = ""


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
        prompt_version: str = "",
        prompt_template_hash: str = "",
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.tools = tools
        self.workspace = workspace
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.prompt_version = prompt_version
        self.prompt_template_hash = prompt_template_hash
        self.context: dict = {
            "consecutive_failures": 0,
            "tool_failure_mode_count": {},
            "last_reasoning_filled": False,
        }

    def _bake_result(
        self,
        status: str,
        messages: list[dict],
        steps: int,
        total_prompt: int,
        total_completion: int,
        duration: float,
        tool_call_count: int,
        reasoning_seen: bool,
        error: Optional[str] = None,
        final_response: str = "",
    ) -> AgentResult:
        """Single construction point for AgentResult so every return path
        carries the same v2.0 instrumentation snapshot."""
        return AgentResult(
            status=status,
            messages=messages,
            final_response=final_response,
            error=error,
            steps_used=steps,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            duration_seconds=duration,
            tool_call_count=tool_call_count,
            tool_failure_mode_count=dict(self.context.get("tool_failure_mode_count", {})),
            reasoning_filled=reasoning_seen,
            prompt_version=self.prompt_version,
            prompt_template_hash=self.prompt_template_hash,
            capabilities_used=dict(getattr(self.llm, "capabilities", {})),
            tool_choice_mode="auto",
        )

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
        tool_call_count = 0
        reasoning_seen = False

        # Parallel-tool policy is driven by the provider's capability dict.
        # Models that can't serialize multiple tool_calls cleanly (gpt-oss
        # Harmony recovery, llama-3.x via Together) still take one at a time.
        caps = getattr(self.llm, "capabilities", None) or {}
        allow_parallel = bool(caps.get("supports_parallel_tools", False))

        while steps < self.max_steps:
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                return self._bake_result(
                    status="timeout",
                    messages=messages,
                    steps=steps,
                    total_prompt=total_prompt,
                    total_completion=total_completion,
                    duration=elapsed,
                    tool_call_count=tool_call_count,
                    reasoning_seen=reasoning_seen,
                    error=f"Agent timed out after {elapsed:.0f}s",
                )

            try:
                response = self.llm.chat(
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as e:
                return self._bake_result(
                    status="error",
                    messages=messages,
                    steps=steps,
                    total_prompt=total_prompt,
                    total_completion=total_completion,
                    duration=time.time() - start_time,
                    tool_call_count=tool_call_count,
                    reasoning_seen=reasoning_seen,
                    error=f"LLM call failed: {str(e)}",
                )

            total_prompt += response.prompt_tokens
            total_completion += response.completion_tokens
            steps += 1

            # No tool calls → agent has emitted its final summary.
            if not response.tool_calls:
                messages.append({"role": "assistant", "content": response.content})
                return self._bake_result(
                    status="completed",
                    messages=messages,
                    steps=steps,
                    total_prompt=total_prompt,
                    total_completion=total_completion,
                    duration=time.time() - start_time,
                    tool_call_count=tool_call_count,
                    reasoning_seen=reasoning_seen,
                    final_response=response.content,
                )

            tool_calls = (
                response.tool_calls if allow_parallel else response.tool_calls[:1]
            )

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

            saw_bug_revealed = False
            for tc in tool_calls:
                result = execute_tool(
                    name=tc["name"],
                    arguments=tc["arguments"],
                    workspace=self.workspace,
                    context=self.context,
                )
                tool_call_count += 1
                if self.context.get("last_reasoning_filled"):
                    reasoning_seen = True

                # Sniff the result for an explicit bug-revealed success so
                # the loop can short-circuit instead of waiting for the model
                # to figure out it should stop.
                if not saw_bug_revealed and '"bug_revealed": true' in result:
                    saw_bug_revealed = True

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            # STOP-on-success: if we just reported a bug-revealing test, ask
            # the model for its final one-sentence summary with no tools
            # available and return. Saves 1-3 wasted steps per task on weak
            # models that don't read their own tool outputs carefully.
            if saw_bug_revealed:
                try:
                    final = self.llm.chat(
                        messages=messages
                        + [{
                            "role": "user",
                            "content": (
                                "The previous tool call returned bug_revealed=true. "
                                "Emit a one-sentence final summary now. Do NOT call "
                                "any further tools."
                            ),
                        }],
                        tools=None,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                    total_prompt += final.prompt_tokens
                    total_completion += final.completion_tokens
                    steps += 1
                    messages.append({"role": "assistant", "content": final.content})
                    return self._bake_result(
                        status="completed",
                        messages=messages,
                        steps=steps,
                        total_prompt=total_prompt,
                        total_completion=total_completion,
                        duration=time.time() - start_time,
                        tool_call_count=tool_call_count,
                        reasoning_seen=reasoning_seen,
                        final_response=final.content,
                    )
                except Exception:
                    # If the wrap-up call fails, fall through to natural loop
                    # exit — the bug was already revealed; we just lose a
                    # graceful summary turn.
                    return self._bake_result(
                        status="completed",
                        messages=messages,
                        steps=steps,
                        total_prompt=total_prompt,
                        total_completion=total_completion,
                        duration=time.time() - start_time,
                        tool_call_count=tool_call_count,
                        reasoning_seen=reasoning_seen,
                        final_response="(bug revealed; final-summary turn skipped)",
                    )

        return self._bake_result(
            status="max_steps",
            messages=messages,
            steps=steps,
            total_prompt=total_prompt,
            total_completion=total_completion,
            duration=time.time() - start_time,
            tool_call_count=tool_call_count,
            reasoning_seen=reasoning_seen,
            error=f"Reached max_steps ({self.max_steps})",
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
