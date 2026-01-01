# DeepAgents Integration Failure Report

## Summary

DeepAgents was evaluated as a routing substrate for the multi-agent orchestration experiment. The integration exhibited **non-terminating internal loops** even under tool-free configurations, making it unsuitable for the experimental pipeline.

## Observed Behavior

1. **Tool-enabled agents**: When agents were given access to tools, DeepAgents' internal LangGraph machinery entered infinite tool-call loops, hitting recursion limits (5, 10, 15) without reaching a stop condition.

2. **Tool-free agents**: Even when agents were configured with `tools=[]`, the underlying graph still failed to terminate within reasonable recursion bounds.

3. **Direct model bypass**: Successful execution was only achieved by bypassing the DeepAgents graph entirely and invoking the LLM directly via `model.invoke()`.

## Error Evidence

```
langgraph.errors.GraphRecursionError: Recursion limit of 15 reached without
hitting a stop condition. You can increase the limit by setting the
`recursion_limit` config key.
```

## Attempted Mitigations

| Mitigation                                 | Outcome                        |
| ------------------------------------------ | ------------------------------ |
| `recursion_limit=5` in invoke config       | Loop persisted                 |
| `recursion_limit=15` in invoke config      | Loop persisted                 |
| Tool-free agent (`tools=[]`)               | Loop persisted                 |
| Prompt constraints ("then STOP")           | No effect on graph termination |
| FilesystemBackend with `virtual_mode=True` | Unrelated; loop is internal    |

## Root Cause Hypothesis

DeepAgents' internal state machine does not respect tool-free configurations for early termination. The graph architecture appears to require explicit end-node routing that is not exposed via `create_deep_agent()` API.

## Recommendation

For this experiment, **continue using the custom orchestrator** (`runner.py` + `llm_client.py`) which provides:

- Deterministic agent sequencing
- Explicit tool invocation control
- No hidden graph machinery

## Paper Statement

> "DeepAgents was evaluated as a routing substrate, but exhibited non-terminating internal loops even under tool-free configurations. The custom orchestrator was retained for experimental reproducibility."

---

_Recorded: 2025-12-31_
