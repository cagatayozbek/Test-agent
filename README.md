# BugTest BugsInPy Pilot

This branch is prepared for running BugsInPy test-generation experiments with
four models:

- `sonnet`
- `opus`
- `openai/gpt-oss-120b`
- `meta/llama-4-maverick-17b-128e-instruct`

The main entrypoint is `run_pilot_all.py`. It runs the same selected task set
across the configured models and modes, then writes results under `results/`.

## What This Branch Contains

- `bugtest/`: experiment framework
- `evaluation/tasks_v2_bugsinpy/`: local BugsInPy-derived benchmark tasks
- `run_pilot_all.py`: multi-model pilot runner
- `aggregate_pilot.py`: aggregate per-model summaries after runs finish

This cleaned branch intentionally excludes reports, PDFs, logs, and unrelated
older task artifacts.

## Experiment Modes

```text
baseline: TestWriter -> Validate
adaptive: TestWriter -> Validate, then Analyzer-assisted retry after failure
deep:     Tool-augmented agent loop with deterministic validation
```

Validation is deterministic:

- test must fail on `buggy/source.py`
- test must pass on `fixed/source.py`

## Requirements

- Python 3.9+
- `pytest`
- Claude Code CLI available as `claude` for `sonnet` / `opus`
- NVIDIA API key for OSS model runs

## Install

Using `pip`:

```bash
pip install -e .
```

Or without editable install:

```bash
pip install pydantic pyyaml pytest openai google-genai
```

## Environment

Set the keys you plan to use:

```bash
export CLAUDE_CODE_KEY=claude-code
export NVIDIA_API_KEY=your_nvidia_key
```

Notes:

- `CLAUDE_CODE_KEY=claude-code` is the expected value in this repo when Claude
  Code CLI auth is already configured locally.
- `run_pilot_all.py` reads `NVIDIA_API_KEY` from the environment and falls back
  to `.env` if present.

## Default Config

`bugtest_config.yaml` controls:

- selected task subset via `tasks.include`
- default modes
- retry budget
- per-run task directory

On split branches, `tasks.include` may already be pre-filled with that branch's
assigned 25 tasks.

## How To Run

Run the branch's assigned tasks across all 4 models:

```bash
python run_pilot_all.py --limit 25 --runs 1
```

Run only selected models:

```bash
python run_pilot_all.py --limit 25 --runs 1 --models sonnet opus
```

Run only selected modes:

```bash
python run_pilot_all.py --limit 25 --runs 1 --modes baseline adaptive deep
```

Run the current config directly without the pilot wrapper:

```bash
python -m bugtest bugtest_config.yaml
```

## Results

Outputs are written to `results/<experiment_id>/`:

- `summary.json`: aggregated metrics
- `runs/<task_id>/...json`: individual run records

After multiple model runs complete:

```bash
python aggregate_pilot.py
```

This writes aggregate CSV and Markdown summaries under `results/`.

## Practical Notes

- `run_pilot_all.py` sorts BugsInPy tasks by buggy source size and picks the
  first `--limit` tasks from that ordering.
- The pilot runner rewrites `bugtest_config.yaml` during execution for each
  model. That is expected behavior.
- Existing matching `results/bugsinpy_pilot_*` directories are reused for
  resume support.

## Key Files

```text
bugtest/config.py
bugtest/experiment.py
bugtest/llm.py
bugtest/pipeline.py
bugtest/validator.py
bugtest/agents/deep_agent.py
bugtest/deep/
run_pilot_all.py
aggregate_pilot.py
bugtest_config.yaml
```
