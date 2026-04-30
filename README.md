# BugTest: Does Code Analysis Improve LLM Test Generation?

An experimental framework for measuring whether a structured code analysis step
improves an LLM's ability to generate bug-revealing tests.

## Research Question

> Does adding a structured code analysis step before test generation improve
> the LLM's Bug-Revealing Test Rate (BRTR)?

## Experimental Design

```
Baseline:  Task --> TestWriter --> Validate (retry x3)
Agentic:   Task --> Analyzer --> TestWriter --> Validate (retry x3)
```

**Fair comparison**: Both modes use the **same** TestWriter prompt, **same**
retry budget, and **same** deterministic validator. The only variable is whether
the TestWriter receives a structured code analysis as additional context.

### How Validation Works

A test is **bug-revealing** if and only if:
- It **FAILS** on the buggy code (exposes the bug)
- It **PASSES** on the fixed code (confirms the fix)

Validation is purely deterministic (pytest + return code). No LLM judgment.

## Architecture

```
bugtest/
  config.py          # Experiment configuration
  llm.py             # Gemini client (google.genai SDK, system_instruction)
  models.py          # All Pydantic data models
  agents/
    protocol.py      # Agent base class
    analyzer.py      # Code analysis agent (produces CodeAnalysis)
    test_writer.py   # Test generation agent (produces pytest code)
  validator.py       # Pytest-based validation (deterministic, no LLM)
  pipeline.py        # Pipeline orchestrator with retry logic
  experiment.py      # Batch runner with statistical output
  __main__.py        # CLI entry point

evaluation/
  tasks_v2/          # 12 evaluation tasks
    <task_id>/
      buggy/source.py
      fixed/source.py
      metadata.json
```

### Agents

| Agent | Role | Output |
|---|---|---|
| **Analyzer** | Reads buggy code, identifies the bug | Structured `CodeAnalysis` JSON |
| **TestWriter** | Writes pytest test targeting the bug | Python test code |

### Key Design Decisions

1. **Gemini SDK**: Uses `system_instruction` properly (not string concatenation)
2. **Fair baseline**: Same retry budget, same prompt, same validator
3. **Deterministic validation**: pytest return codes, no LLM-as-judge
4. **Interleaved execution**: baseline/agentic runs alternate to control for temporal bias
5. **Statistical rigor**: Wilson score 95% confidence intervals for BRTR

## Setup

```bash
pip install google-genai pydantic pyyaml
```

Set your API key:
```bash
export GOOGLE_API_KEY=your_key_here
```

## Usage

### Quick Test (1 run per task)

Edit `bugtest_config.yaml`:
```yaml
experiment:
  runs_per_task: 1
tasks:
  include: ["boundary_threshold"]
```

```bash
python -m bugtest bugtest_config.yaml
```

### Full Experiment

```bash
python -m bugtest bugtest_config.yaml
```

Results are saved to `results/<experiment_id>/`:
- `summary.json` — Aggregated statistics with BRTR and confidence intervals
- `runs/<task_id>/` — Individual run records with test code and validation output
- `config.yaml` — Snapshot of experiment configuration

## Evaluation Tasks

12 tasks spanning different bug categories:

| Category | Tasks |
|---|---|
| Boundary/Logic | boundary_threshold, off_by_one_loop |
| Concurrency | async_race_condition |
| State Management | cache_invalidation |
| Error Handling | swallowed_exception |
| Type Safety | type_coercion_price, null_handling_profile |
| Real-world (BugsInPy) | black, pysnooper, thefuck (x2), tqdm |

## Metrics

- **BRTR** (Bug-Revealing Test Rate): Proportion of runs producing a bug-revealing test
- **Attempts-to-success**: Average retries needed (lower = better)
- **Token cost**: Prompt + completion tokens per run per mode
- **Wilson score 95% CI**: Proper confidence intervals for small sample sizes

## Configuration

See `bugtest_config.yaml` for all options:

```yaml
experiment:
  name: "analysis_vs_direct"
  runs_per_task: 10

model:
  model_id: "gemini-2.5-flash"
  temperature: 1.0

retry:
  max_attempts: 3
  test_timeout_seconds: 30
```

## License

MIT
