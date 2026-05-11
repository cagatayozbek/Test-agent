"""
Multi-provider LLM client.

Supports:
  - nvidia:<model-id>   → NVIDIA Build (OpenAI-compatible)
  - anthropic:<model-id> → Anthropic Claude API
  - claude:<model-id>   → Claude Code CLI (Max subscription, no API key needed)
  - openai:<model-id>   → OpenAI-compatible endpoints

No LangChain. Just SDK calls + subprocess for CLI.
"""

import os
import json
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Raw LLM response."""
    content: str
    tool_calls: list  # list of {id, name, arguments}
    prompt_tokens: int = 0
    completion_tokens: int = 0


_LIMIT_SIGNALS = (
    "usage limit", "rate limit", "rate_limit", "5-hour limit", "5 hour limit",
    "weekly limit", "limit_exceeded", "limit exceeded", "too many requests",
    "429", "quota", "you've reached", "you have reached", "claude usage limit",
    "max requests", "approaching usage limit",
)


def _is_claude_limit_error(stdout: str, stderr: str) -> bool:
    text_l = ((stdout or "") + " " + (stderr or "")).lower()
    return any(sig in text_l for sig in _LIMIT_SIGNALS)


def _sleep_through_claude_limit(attempt: int, wait_minutes: int = 60) -> None:
    print(f"  !! claude limit detected — sleeping {wait_minutes}min "
          f"(limit-retry {attempt + 1}/6)", flush=True)
    time.sleep(wait_minutes * 60)


class LLMClient:
    """Unified LLM client for multiple providers."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 2,
        workspace: Optional[str] = None,
    ):
        self.model = model
        self.timeout = timeout
        self.max_retries = max(max_retries, 5)  # Min 5 retries for rate limits
        # Optional workspace path used by the Claude CLI provider so its
        # built-in Read/Edit/Bash tools can touch the task workspace.
        self.workspace: Optional[str] = workspace

        if model.startswith("claude:"):
            self.provider = "claude_cli"
            self.model_id = model.removeprefix("claude:")
            self.api_key = None
            self.base_url = None
        elif model.startswith("nvidia:"):
            self.provider = "nvidia"
            self.model_id = model.removeprefix("nvidia:")
            self.api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")
            self.base_url = base_url or os.environ.get(
                "DEEPTEST_NVIDIA_BASE_URL",
                "https://integrate.api.nvidia.com/v1"
            )
        elif model.startswith("anthropic:"):
            self.provider = "anthropic"
            self.model_id = model.removeprefix("anthropic:")
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            self.base_url = None
        elif model.startswith("openai:"):
            self.provider = "openai"
            self.model_id = model.removeprefix("openai:")
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
            self.base_url = base_url
        else:
            raise ValueError(
                f"Unknown model format: {model}. "
                "Use claude:<id>, nvidia:<id>, anthropic:<id>, or openai:<id>"
            )

    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send chat completion request with optional tool definitions."""
        for attempt in range(self.max_retries + 1):
            try:
                if self.provider == "claude_cli":
                    return self._call_claude_cli(messages, tools)
                elif self.provider == "anthropic":
                    return self._call_anthropic(messages, tools, temperature, max_tokens)
                else:
                    return self._call_openai_compat(messages, tools, temperature, max_tokens)
            except Exception as e:
                if attempt < self.max_retries and self._is_retryable(e):
                    wait = 5 * (attempt + 1)  # 5, 10, 15, 20, 25s
                    time.sleep(wait)
                    continue
                raise

    def _call_claude_cli(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
    ) -> LLMResponse:
        """Call Claude via CLI. Claude CLI has its own tools (Read, Edit, Bash).

        We send a single prompt and let Claude do all the work in one shot.
        The response is treated as final text (no tool_calls returned to our loop).
        """
        # Build a single prompt from all messages
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            if role == "system":
                parts.append(content)
            elif role == "user":
                parts.append(content)
            elif role == "assistant":
                if content:
                    parts.append(f"[Previous response: {content[:500]}]")
            elif role == "tool":
                parts.append(f"[Previous tool result: {content[:1000]}]")

        prompt = "\n\n".join(parts)

        # Truncate if too large
        if len(prompt) > 30000:
            prompt = prompt[:30000] + "\n\n[...truncated]"

        # Call CLI — Claude will use its own Read/Edit/Bash tools.
        # CRITICAL: --add-dir <workspace> is required so those tools can
        # touch the task workspace; without it Claude can't write files.
        cmd = ["claude", "-p", "--model", self.model_id,
               "--output-format", "json",
               "--allowedTools", "Read,Edit,Bash,Write",
               "--dangerously-skip-permissions"]
        if self.workspace:
            cmd.extend(["--add-dir", self.workspace])
        result = None
        for limit_attempt in range(6):
            try:
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
            except subprocess.TimeoutExpired:
                raise TimeoutError("Claude CLI timed out after 900s")
            if _is_claude_limit_error(result.stdout, result.stderr):
                _sleep_through_claude_limit(limit_attempt)
                continue
            break
        # Inter-call cooldown to relax Anthropic-side queueing under Max sub
        time.sleep(3)

        raw = result.stdout.strip()
        if result.returncode != 0 and not raw:
            raise RuntimeError(f"Claude CLI error (exit {result.returncode}): {result.stderr[:500]}")

        # --output-format json wraps response: {"result": "...", "usage": {...}, ...}
        text = raw
        prompt_tokens = 0
        completion_tokens = 0
        try:
            wrapper = json.loads(raw)
            if isinstance(wrapper, dict):
                text = wrapper.get("result", raw)
                usage = wrapper.get("usage") or {}
                prompt_tokens = (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                )
                completion_tokens = usage.get("output_tokens", 0)
        except json.JSONDecodeError:
            pass

        # CLI mode: return as final text, no tool calls (CLI already executed tools).
        return LLMResponse(
            content=text,
            tool_calls=[],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def _call_openai_compat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call NVIDIA/OpenAI-compatible API."""
        from openai import OpenAI

        client = OpenAI(base_url=self.base_url, api_key=self.api_key)

        kwargs = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "required"
        else:
            # No tools = final response mode
            pass

        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })

        usage = resp.usage
        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )

    def _call_anthropic(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Call Anthropic Claude API."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        # Extract system message
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        # Convert OpenAI tool format → Anthropic tool format
        anthropic_tools = None
        if tools:
            anthropic_tools = []
            for t in tools:
                func = t["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                })

        kwargs = {
            "model": self.model_id,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        resp = client.messages.create(**kwargs)

        # Parse response
        content = ""
        tool_calls = []
        for block in resp.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": json.dumps(block.input),
                })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            prompt_tokens=resp.usage.input_tokens if resp.usage else 0,
            completion_tokens=resp.usage.output_tokens if resp.usage else 0,
        )

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        """Check if error is retryable (rate limit, server error)."""
        error_str = str(error).lower()
        return any(kw in error_str for kw in ["rate", "429", "500", "502", "503", "timeout", "too many"])
