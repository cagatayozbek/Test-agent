"""
Model capability adaptor.

Maps a provider-prefixed model id (e.g. `claude:sonnet`,
`openai:openai/gpt-oss-120b`) to a flat capability dict. The orchestrator,
LLM client, and agent loop read this dict to decide:

  - whether to allow parallel tool calls,
  - whether to set `tool_choice="auto"` or fall back to harmony recovery,
  - whether the provider supports a separate `system` role,
  - which tool-name strings to substitute into the model-agnostic prompt.

Per-model rows override the per-provider defaults. Unknown ids resolve to
a defensive default (parallel=False, structured=True, OpenAI tool names)
and emit a one-time warning so a missed entry is visible without breaking
the run.
"""

from __future__ import annotations

import sys
from typing import TypedDict


class ToolNameMap(TypedDict):
    read: str
    edit: str
    run: str


class Capabilities(TypedDict):
    provider: str
    supports_parallel_tools: bool
    supports_tool_choice_auto: bool
    supports_structured_tools: bool
    supports_system_role: bool
    tool_names: ToolNameMap


# Tool names exposed to the model in the rendered system prompt.
# Orchestrator-side tools (read_file, safe_edit_file, run_tests) are used
# everywhere except the Claude Code CLI provider, which runs end-to-end in
# one subprocess and uses its own built-in Read/Edit/Bash tools.
_ORCHESTRATOR_TOOL_NAMES: ToolNameMap = {
    "read": "read_file",
    "edit": "safe_edit_file",
    "run": "run_tests",
}
_CLAUDE_CLI_TOOL_NAMES: ToolNameMap = {
    "read": "Read",
    "edit": "Edit",
    "run": "Bash (`python -m pytest`)",
}


_DEFAULT: Capabilities = {
    "provider": "openai",
    "supports_parallel_tools": False,
    "supports_tool_choice_auto": True,
    "supports_structured_tools": True,
    "supports_system_role": True,
    "tool_names": _ORCHESTRATOR_TOOL_NAMES,
}


# Exact-match overrides keyed by the full prefixed model id (lowercased).
_EXACT: dict[str, Capabilities] = {
    # Claude Code CLI subprocess — handles its own tool loop, returns final
    # text only; the agent loop sees zero structured tool_calls.
    "claude:sonnet": {
        "provider": "claude_cli",
        "supports_parallel_tools": True,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": False,
        "supports_system_role": False,
        "tool_names": _CLAUDE_CLI_TOOL_NAMES,
    },
    "claude:opus": {
        "provider": "claude_cli",
        "supports_parallel_tools": True,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": False,
        "supports_system_role": False,
        "tool_names": _CLAUDE_CLI_TOOL_NAMES,
    },
    "claude:haiku": {
        "provider": "claude_cli",
        "supports_parallel_tools": True,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": False,
        "supports_system_role": False,
        "tool_names": _CLAUDE_CLI_TOOL_NAMES,
    },

    # gpt-oss on Together emits OpenAI Harmony-channel framing as plain
    # content; tool_calls is empty. Recovery happens in deep/llm.py via
    # _parse_harmony_tool_calls. The model expects single-call turns.
    "openai:openai/gpt-oss-120b": {
        "provider": "openai",
        "supports_parallel_tools": False,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": False,
        "supports_system_role": True,
        "tool_names": _ORCHESTRATOR_TOOL_NAMES,
    },

    # DeepSeek-V3 on Together — structured tools work; parallel calls OK.
    "openai:deepseek-ai/deepseek-v3": {
        "provider": "openai",
        "supports_parallel_tools": True,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": True,
        "supports_system_role": True,
        "tool_names": _ORCHESTRATOR_TOOL_NAMES,
    },

    # DeepSeek-V4-flash on OpenRouter — reasoning model. Emits parallel tool
    # calls (e.g. two read_file in one turn) and needs them all answered, or
    # it stalls; also returns its chain-of-thought in `reasoning_details`,
    # which the agent now echoes back (see bugtest/deep/llm.py).
    "openai:deepseek/deepseek-v4-flash": {
        "provider": "openai",
        "supports_parallel_tools": True,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": True,
        "supports_system_role": True,
        "tool_names": _ORCHESTRATOR_TOOL_NAMES,
    },

    # DeepSeek-Coder 33B Instruct — older arch, single tool at a time is
    # safer in practice.
    "openai:deepseek-ai/deepseek-coder-33b-instruct": {
        "provider": "openai",
        "supports_parallel_tools": False,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": True,
        "supports_system_role": True,
        "tool_names": _ORCHESTRATOR_TOOL_NAMES,
    },

    # Qwen3-Coder — structured tools work; treat as parallel-capable.
    "openai:qwen/qwen3-coder-next-fp8": {
        "provider": "openai",
        "supports_parallel_tools": True,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": True,
        "supports_system_role": True,
        "tool_names": _ORCHESTRATOR_TOOL_NAMES,
    },

    # Llama-3.3-70B on Together — structured tools but conservative on
    # parallelism (the OSS chat templates don't all serialize parallel
    # calls cleanly).
    "openai:meta-llama/llama-3.3-70b-instruct-turbo": {
        "provider": "openai",
        "supports_parallel_tools": False,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": True,
        "supports_system_role": True,
        "tool_names": _ORCHESTRATOR_TOOL_NAMES,
    },
}


# Provider-prefix fallbacks. Used when no exact-match row applies — e.g.
# `anthropic:<some-new-model>` should still get Anthropic defaults.
_PROVIDER_DEFAULTS: dict[str, Capabilities] = {
    "claude:": {
        "provider": "claude_cli",
        "supports_parallel_tools": True,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": False,
        "supports_system_role": False,
        "tool_names": _CLAUDE_CLI_TOOL_NAMES,
    },
    "anthropic:": {
        "provider": "anthropic",
        "supports_parallel_tools": True,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": True,
        "supports_system_role": True,
        "tool_names": _ORCHESTRATOR_TOOL_NAMES,
    },
    "nvidia:": {
        "provider": "nvidia",
        "supports_parallel_tools": False,
        "supports_tool_choice_auto": True,
        "supports_structured_tools": True,
        "supports_system_role": True,
        "tool_names": _ORCHESTRATOR_TOOL_NAMES,
    },
    "openai:": _DEFAULT,
}


_warned: set[str] = set()


def for_model(model_id: str) -> Capabilities:
    """Resolve a capability dict for the given provider-prefixed model id.

    Resolution order:
      1. Exact-match (case-insensitive) in `_EXACT`.
      2. Longest provider prefix in `_PROVIDER_DEFAULTS`.
      3. `_DEFAULT` plus a one-time stderr warning so missing rows surface.
    """
    key = model_id.lower()
    if key in _EXACT:
        return _EXACT[key]

    for prefix, caps in _PROVIDER_DEFAULTS.items():
        if key.startswith(prefix):
            return caps

    if model_id not in _warned:
        _warned.add(model_id)
        print(
            f"[capabilities] no capability row for model_id={model_id!r}; "
            "falling back to OpenAI defaults",
            file=sys.stderr,
        )
    return _DEFAULT
