"""Behavioral tests for the v2.0 agent loop.

Uses a stub LLMClient that emits a scripted sequence of LLMResponse objects,
so the loop's tool dispatching, STOP-on-success short-circuit, parallel-
tool capability gating, and instrumentation propagation can be verified
without touching any real provider.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pytest

from bugtest.deep.agent import Agent, AgentResult
from bugtest.deep.llm import LLMResponse
from bugtest.deep import builtin_tools  # noqa: F401 — registers tools at import


# ── Stubs ──


@dataclass
class _StubLLM:
    """Drop-in replacement for LLMClient that returns scripted responses.

    The capability dict drives the agent's parallel-tool policy. The
    `script` is a list of LLMResponse objects yielded in order; each
    `chat()` invocation consumes one. If the script runs out, raises so
    a buggy loop can't quietly succeed.
    """
    capabilities: dict
    script: list[LLMResponse]
    _calls: list[dict] = field(default_factory=list)

    def chat(self, messages, tools=None, temperature=0.7, max_tokens=4096):
        self._calls.append({"messages_len": len(messages), "has_tools": bool(tools)})
        if not self.script:
            raise RuntimeError("stub LLM script exhausted")
        return self.script.pop(0)


def _resp(content="", tool_calls=None, p=10, c=5):
    return LLMResponse(
        content=content,
        tool_calls=tool_calls or [],
        prompt_tokens=p,
        completion_tokens=c,
    )


def _tool_call(name, args_dict, call_id="call_1"):
    return {"id": call_id, "name": name, "arguments": json.dumps(args_dict)}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "source.py").write_text(
        "def add(a, b):\n    return a - b\n", encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_benchmark.py").write_text(
        "import source\n\n\ndef test_smoke():\n    assert source is not None\n",
        encoding="utf-8",
    )
    return tmp_path


# ── Tests ──


def test_no_tool_calls_completes_immediately(workspace: Path):
    """Model emits a text-only response → loop terminates with 'completed'."""
    llm = _StubLLM(
        capabilities={"supports_parallel_tools": False},
        script=[_resp(content="I'm done.")],
    )
    agent = Agent(
        llm=llm,
        system_prompt="sys",
        tools=["safe_edit_file"],
        workspace=str(workspace),
        max_steps=5,
        prompt_version="v2.0",
        prompt_template_hash="abc123def456",
    )
    result = agent.run("do the thing")

    assert result.status == "completed"
    assert result.final_response == "I'm done."
    assert result.tool_call_count == 0
    assert result.prompt_version == "v2.0"
    assert result.prompt_template_hash == "abc123def456"
    assert result.tool_choice_mode == "auto"


def test_capabilities_used_propagates_to_result(workspace: Path):
    caps = {"supports_parallel_tools": True, "supports_structured_tools": True}
    llm = _StubLLM(capabilities=caps, script=[_resp(content="done")])
    agent = Agent(
        llm=llm, system_prompt="sys", tools=["safe_edit_file"],
        workspace=str(workspace), max_steps=3,
    )
    result = agent.run("go")
    assert result.capabilities_used == caps


def test_parallel_tool_calls_kept_when_capability_allows(workspace: Path):
    """Parallel-capable models: every tool_call in a turn is executed."""
    appended = _tool_call(
        "safe_edit_file",
        {"file_path": "tests/test_benchmark.py",
         "mode": "append",
         "append": "\n\ndef test_a():\n    assert True\n",
         "allow_bug_revealing": True},
        call_id="c1",
    )
    appended2 = _tool_call(
        "safe_edit_file",
        {"file_path": "tests/test_benchmark.py",
         "mode": "append",
         "append": "\n\ndef test_b():\n    assert True\n",
         "allow_bug_revealing": True},
        call_id="c2",
    )
    llm = _StubLLM(
        capabilities={"supports_parallel_tools": True},
        script=[
            _resp(tool_calls=[appended, appended2]),
            _resp(content="all done"),
        ],
    )
    agent = Agent(
        llm=llm, system_prompt="sys", tools=["safe_edit_file"],
        workspace=str(workspace), max_steps=5,
    )
    result = agent.run("go")
    assert result.tool_call_count == 2


def test_parallel_calls_truncated_when_capability_forbids(workspace: Path):
    """Non-parallel models drop the tail of a multi-call response."""
    c1 = _tool_call(
        "safe_edit_file",
        {"file_path": "tests/test_benchmark.py",
         "mode": "append",
         "append": "\n\ndef test_a():\n    assert True\n"},
        call_id="c1",
    )
    c2 = _tool_call(
        "safe_edit_file",
        {"file_path": "tests/test_benchmark.py",
         "mode": "append",
         "append": "\n\ndef test_b():\n    assert True\n"},
        call_id="c2",
    )
    llm = _StubLLM(
        capabilities={"supports_parallel_tools": False},
        script=[
            _resp(tool_calls=[c1, c2]),
            _resp(content="ok"),
        ],
    )
    agent = Agent(
        llm=llm, system_prompt="sys", tools=["safe_edit_file"],
        workspace=str(workspace), max_steps=5,
    )
    result = agent.run("go")
    assert result.tool_call_count == 1  # second call dropped


def test_stop_on_bug_revealed_short_circuits(workspace: Path):
    """When a tool reports bug_revealed=true, the loop asks for a single
    summary turn and exits early instead of burning the step budget."""
    bug_revealing = _tool_call(
        "safe_edit_file",
        {"file_path": "tests/test_benchmark.py",
         "mode": "append",
         "append": "\n\ndef test_bug():\n    assert source.add(2, 3) == 5\n",
         "allow_bug_revealing": True},
        call_id="c1",
    )
    llm = _StubLLM(
        capabilities={"supports_parallel_tools": False},
        script=[
            _resp(tool_calls=[bug_revealing]),
            _resp(content="Test reveals add() bug."),
            # If the loop did NOT short-circuit, it would consume another
            # response; an empty script here would surface the bug.
        ],
    )
    agent = Agent(
        llm=llm, system_prompt="sys", tools=["safe_edit_file"],
        workspace=str(workspace), max_steps=10,
    )
    result = agent.run("go")
    assert result.status == "completed"
    assert "reveals add() bug" in result.final_response
    assert result.tool_call_count == 1
    # The loop used exactly the tool-call turn + the summary turn.
    assert result.steps_used == 2


def test_reasoning_filled_propagates_when_any_call_sets_it(workspace: Path):
    with_reasoning = _tool_call(
        "safe_edit_file",
        {"file_path": "tests/test_benchmark.py",
         "mode": "append",
         "append": "\n\ndef test_r():\n    assert True\n",
         "hypothesis": "fixing observed behavior",
         "allow_bug_revealing": True},
        call_id="c1",
    )
    llm = _StubLLM(
        capabilities={"supports_parallel_tools": False},
        script=[
            _resp(tool_calls=[with_reasoning]),
            _resp(content="done"),
        ],
    )
    agent = Agent(
        llm=llm, system_prompt="sys", tools=["safe_edit_file"],
        workspace=str(workspace), max_steps=5,
    )
    result = agent.run("go")
    assert result.reasoning_filled is True


def test_failure_mode_counts_propagate_to_result(workspace: Path):
    """A mode_conflict from the tool surfaces in the AgentResult snapshot."""
    bad_call = _tool_call(
        "safe_edit_file",
        {"file_path": "tests/test_benchmark.py", "mode": "rewrite"},
        call_id="c1",
    )
    llm = _StubLLM(
        capabilities={"supports_parallel_tools": False},
        script=[
            _resp(tool_calls=[bad_call]),
            _resp(content="ack"),
        ],
    )
    agent = Agent(
        llm=llm, system_prompt="sys", tools=["safe_edit_file"],
        workspace=str(workspace), max_steps=5,
    )
    result = agent.run("go")
    assert result.tool_failure_mode_count.get("mode_conflict") == 1


def test_max_steps_exit_keeps_instrumentation(workspace: Path):
    """Even if the loop hits max_steps, the AgentResult must carry the
    instrumentation snapshot so partial-run analysis stays possible."""
    loop_call = _tool_call(
        "safe_edit_file",
        {"file_path": "tests/test_benchmark.py", "mode": "rewrite"},  # always fails
        call_id="c1",
    )
    llm = _StubLLM(
        capabilities={"supports_parallel_tools": False},
        script=[_resp(tool_calls=[loop_call]) for _ in range(10)],
    )
    agent = Agent(
        llm=llm, system_prompt="sys", tools=["safe_edit_file"],
        workspace=str(workspace), max_steps=3,
        prompt_version="v2.0",
    )
    result = agent.run("go")
    assert result.status == "max_steps"
    assert result.tool_call_count == 3
    assert result.tool_failure_mode_count.get("mode_conflict") == 3
    assert result.prompt_version == "v2.0"
