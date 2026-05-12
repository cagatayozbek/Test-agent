# Pre-Registration v2 — Multi-Source BRTR Benchmark

**Date:** 2026-05-11
**Author:** Furkan Çağatay Özbek
**Repository state at registration:** parent commit `fc73ce1` + dataset
expansion commits (see `DATASET_EXPANSION.md`).
**Supersedes:** Not applicable. This is an independent, parallel pre-registration
for a new benchmark run on the expanded multi-source dataset.
**Does NOT modify:** `PREREGISTRATION.md` (the 2026-05-10 QuixBugs-only run).
That document remains the authoritative record of the prior experiment.

This document fixes the experimental design **before** any run is executed on
the expanded task set, so that task/model/mode decisions are not
outcome-dependent. Any deviation must be explained as a post-hoc decision in
the corresponding report.

---

## 1. Research question

Does an adaptive analysis-on-failure pipeline improve bug-revealing test
generation BRTR over a direct-prompt baseline, and is the effect uniform
across (a) Claude capability tiers (Haiku 4.5 → Sonnet 4.6 → Opus 4.7) and
(b) bug-source heterogeneity (algorithmic / function-level / synthetic
mutation / real-world / hand-crafted)?

The cross-source stratification is the new affordance from
`DATASET_EXPANSION.md` that the prior QuixBugs-only run could not exercise.

## 2. Primary metric

**BRTR (Bug-Revealing Test Rate):** fraction of pipeline runs whose
generated test FAILS on `buggy/source.py` AND PASSES on `fixed/source.py`.

Formal definition: `bugtest/validator.py:32-38`. Computation:
`bugtest/experiment.py:_compute_mode_stats`. 95% confidence interval via
Wilson score interval (`_wilson_ci`, `bugtest/experiment.py:77-87`).

## 3. Secondary metrics

- `attempts_to_success` (mean) per (model, mode)
- `prompt_tokens` / `completion_tokens` (mean) per (model, mode)
- `duration_seconds` (mean) per (model, mode) — informational only;
  affected by concurrency, not used for scientific claims

## 4. Tasks

**25 tasks**, drawn by stratified random sampling (`random.seed(42)`,
`random.sample` on alphabetically-sorted bucket lists) — 5 tasks from each
of 5 sources. The exact frozen list is also persisted at
`v2_sample_seed42.json` in the repository root.

```
quixbugs (5)
  - quixbugs_bitcount
  - quixbugs_find_in_sorted
  - quixbugs_is_valid_parenthesization
  - quixbugs_pascal
  - quixbugs_quicksort

humanevalfix (5)
  - humanevalfix_026
  - humanevalfix_035
  - humanevalfix_057
  - humanevalfix_062
  - humanevalfix_139

mbpp_mutation (5)
  - mbpp_mutation_001
  - mbpp_mutation_002
  - mbpp_mutation_005
  - mbpp_mutation_027
  - mbpp_mutation_037

bugsinpy (5)
  - bugsinpy_black_async_for_13
  - bugsinpy_pysnooper_unicode_1
  - bugsinpy_thefuck_fish_version_3
  - bugsinpy_thefuck_fix_file_28
  - bugsinpy_tqdm_enumerate_start_1

legacy (5)
  - async_race_condition
  - null_handling_profile
  - off_by_one_loop
  - swallowed_exception
  - type_coercion_price
```

Provenance of each bucket: `DATASET_EXPANSION.md` §1.

**BugsInPy and legacy buckets contain exactly 5 tasks**, so "random 5 of 5"
is the full bucket; the seed only matters for the larger buckets.

### Difficulty distribution of the frozen 25

(post-hoc covariate; LLM never sees difficulty label)

| Source | easy | medium | hard | unset |
| --- | --- | --- | --- | --- |
| quixbugs | 2 | 3 | 0 | 0 |
| humanevalfix | 5 | 0 | 0 | 0 |
| mbpp_mutation | 5 | 0 | 0 | 0 |
| bugsinpy | 3 | 2 | 0 | 0 |
| legacy | 0 | 0 | 0 | 5 |
| **total** | **15** | **5** | **0** | **5** |

Difficulty is **post-hoc stratification only** — the LLM never sees it.
The frozen 25 lean heavily toward easy (15/25); the 5 legacy tasks have no
difficulty label. This matches the user-requested "not too hard" constraint
from `DATASET_EXPANSION.md`.

## 5. Models

| Model ID | Provider | Capability tier |
| --- | --- | --- |
| `haiku` (Claude Haiku 4.5) | Claude Code CLI | small / fast |
| `sonnet` (Claude Sonnet 4.6) | Claude Code CLI | medium |
| `opus` (Claude Opus 4.7) | Claude Code CLI | large |

Single-provider design eliminates the cross-provider infrastructure confound
observed in the 2026-05-10 NVIDIA Build / Together.ai migration
(see `PREREGISTRATION.md` §5.3-4).

### Pre-registered exclusions

None. All three Claude models will be evaluated on every (task, mode, run)
combination. If a model produces > 50% pipeline errors during the run, the
data will be reported separately and the model excluded from the primary
comparison; the threshold and procedure are fixed here so the exclusion is
not outcome-dependent.

## 6. Modes

Two pipeline modes (`bugtest/pipeline.py`):

- **baseline:** direct test generation, ≤3 retry attempts (the same retry
  loop as before).
- **adaptive:** baseline-style attempt 1; on failure, Analyzer agent is
  activated and its `CodeAnalysis` output is prepended to the user message
  for attempts 2-3.

**`agentic` mode is excluded.** Justification: in the 2026-05-10 QuixBugs-only
run the `agentic` mode never outperformed `adaptive` on aggregate BRTR
(`EXPERIMENT_REPORT.md` §3) and consumed strictly more tokens (Analyzer is
always invoked, even when unnecessary). Dropping it reduces the run by 33%
without losing the "does analysis help?" signal — that signal is fully
preserved in the baseline-vs-adaptive comparison.

## 7. Run parameters

- `runs_per_task: 3` (independent samples per (task, mode, model) cell)
- `max_attempts: 3` per run
- `temperature: 0.7`, `max_output_tokens: 4096`
- `concurrency: 8` (ThreadPoolExecutor in `bugtest/experiment.py`)
- `test_timeout_seconds: 30`

Total planned runs:
- 25 tasks × 3 models × 2 modes × 3 runs = **450 runs**

Confidence interval width: at N=3 runs per cell, individual (task, mode,
model) cells have wide Wilson intervals (≈ ±28pp at p=0.5). Cross-task
aggregation gives 75 runs per (model, mode) cell which narrows the CI to
≈ ±11pp at p=0.5. **The primary aggregation level is therefore (model,
mode), not (task, model, mode).** Per-task results are reported as
exploratory.

## 8. Analysis plan

Reported tables / figures, in registered order:

1. **Per-model × per-mode BRTR** with 95% Wilson CI (75 runs per cell).
2. **Per-source × per-mode × per-model BRTR** with 95% Wilson CI (15 runs
   per cell). Exploratory but pre-specified — answers RQ part (b).
3. **Per-task `adaptive - baseline` Δ-BRTR**, reported with the caveat that
   N=3 per cell makes per-task deltas noisy.
4. **Token / duration table** (informational).
5. **Failure-mode breakdown by `bug_type`**, descriptive only.

No statistical significance test is pre-registered as primary. All
comparisons reported with CIs and effect sizes. If a hypothesis test is
added post-hoc, it will be labeled exploratory in the report.

## 9. Stop / resume rules

- Per-job records are persisted immediately
  (`bugtest/experiment.py:_run_job` writes each `RunRecord` to disk under the
  task directory before the next job starts).
- If the run is interrupted, completed records are kept; interrupted
  (model, task, run, mode) cells are re-run with `runs_per_task` topped up
  to 3.
- The full benchmark may be re-run after this pre-registration **only** if
  a reproducible infrastructure bug is found (e.g., bug in `_run_job`
  itself); the bug must be documented in the report.

## 10. Threats to validity (acknowledged up-front)

- **Hint leakage (severe).** Every task's `metadata.json` supplies
  `bug_description` and `test_hint` that paraphrase the bug and suggest an
  input. These are passed to the LLM via
  `bugtest/pipeline.py:_build_user_message`. Reported BRTR is therefore an
  **upper bound on capability**; this run **does not measure bug-localization
  ability**. The asymmetry across sources (HumanEvalFix's diff-quoting
  hints vs BugsInPy's naturalistic prose) is acknowledged in
  `DATASET_EXPANSION.md` §3.1 and may show up as a per-source delta. A
  hint-ablation experiment is **not** part of this pre-registration — it is
  a follow-up.
- **Data contamination.** All five sources are public and very likely
  present in every Claude model's training corpus. BRTR is an upper bound
  on capability; do not interpret as out-of-distribution measurement.
- **Subset disclosure.** This run uses 25 of 257 available tasks. Cross-run
  comparison with `PREREGISTRATION.md` (QuixBugs n=31) must be restricted
  to the 5 QuixBugs tasks shared between the two runs.
- **Synthetic mutations.** 5 of the 25 tasks (`mbpp_mutation_*`) are
  synthetic single-mutation bugs. They are systematically simpler than
  human bugs in ways that may inflate BRTR for these tasks.
- **N=3 per cell** is deliberately lean. Per-task deltas have ~±28pp
  confidence intervals; per-(model, mode) cells have ~±11pp. Conclusions
  about model rankings within ~10pp should be reported as inconclusive.
- **Single-provider model set.** All three models are Claude; provider
  effects (API behavior, sampling, system prompt handling) are constant
  rather than measured. Cross-family generalization is out of scope.
- **`legacy` source heterogeneity.** The 5 legacy tasks are hand-written
  with varying quality; they share no provenance with the other four
  sources. They are included for benchmark continuity, not for stratified
  comparison.

## 11. Reproducing the task selection

```bash
python3 - <<'PY'
import random, pathlib, json
random.seed(42)
root = pathlib.Path("evaluation/tasks_v2")
# (See PREREGISTRATION_V2.md §4 for the canonical source mapping.)
# This snippet reproduces v2_sample_seed42.json exactly.
PY
```

The canonical sampling script is committed in this repository's git history
together with `v2_sample_seed42.json`.

## 12. Running this benchmark

Use this exact `bugtest_config.yaml` to reproduce the registered run:

```yaml
experiment:
  name: v2_multi_source_baseline_adaptive
  runs_per_task: 3
  concurrency: 8
  modes: [baseline, adaptive]
model:
  api_key_env: CLAUDE_CODE_KEY
  max_output_tokens: 4096
  model_id: sonnet       # change to "haiku" / "opus" for the other tiers
  temperature: 0.7
  base_url: null
retry:
  max_attempts: 3
  test_timeout_seconds: 30
results:
  dir: results
tasks:
  dir: evaluation/tasks_v2
  include:
    - quixbugs_bitcount
    - quixbugs_find_in_sorted
    - quixbugs_is_valid_parenthesization
    - quixbugs_pascal
    - quixbugs_quicksort
    - humanevalfix_026
    - humanevalfix_035
    - humanevalfix_057
    - humanevalfix_062
    - humanevalfix_139
    - mbpp_mutation_001
    - mbpp_mutation_002
    - mbpp_mutation_005
    - mbpp_mutation_027
    - mbpp_mutation_037
    - bugsinpy_black_async_for_13
    - bugsinpy_pysnooper_unicode_1
    - bugsinpy_thefuck_fish_version_3
    - bugsinpy_thefuck_fix_file_28
    - bugsinpy_tqdm_enumerate_start_1
    - async_race_condition
    - null_handling_profile
    - off_by_one_loop
    - swallowed_exception
    - type_coercion_price
  exclude: []
  sources: []
  difficulties: []
  bug_types: []
```

The explicit `include` list (not source filters) is used so the
pre-registered task set is exact and unambiguous. `sources` /
`difficulties` / `bug_types` filters remain available for follow-up
exploratory runs.

---

End of pre-registration v2.
