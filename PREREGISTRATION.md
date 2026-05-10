# Pre-Registration — QuixBugs BRTR Benchmark

**Date:** 2026-05-10
**Author:** Furkan Çağatay Özbek
**Repository state at registration:** parent commit `29905ed`
(this file is committed before any full-benchmark run)

This document fixes the experimental design **before** the full benchmark run is
executed, so that model/mode exclusions and analysis decisions are not
outcome-dependent. Any deviation must be explained as a post-hoc decision in
`EXPERIMENT_REPORT.md`.

---

## 1. Research question

For test-generation against buggy/fixed Python programs, does an "agentic" or
"adaptive" pipeline mode produce more bug-revealing tests than a baseline
direct-prompt pipeline, across LLMs of different capability tiers?

## 2. Primary metric

**BRTR (Bug-Revealing Test Rate):** the fraction of pipeline runs whose
generated test FAILS on `buggy/source.py` AND PASSES on `fixed/source.py`.

Formal definition: `bugtest/validator.py:32-38`. Computation:
`bugtest/experiment.py:_compute_mode_stats`. 95% confidence interval reported
via Wilson score interval (`_wilson_ci`, `bugtest/experiment.py:74-84`).

## 3. Secondary metrics

- `attempts_to_success` (mean) per (model, mode)
- `prompt_tokens` / `completion_tokens` (mean) per (model, mode)
- `duration_seconds` (mean) per (model, mode) — informational only;
  affected by concurrency, not used for scientific claims

## 4. Tasks

**31 QuixBugs Python programs**, byte-identical to the upstream sources at
`evaluation/quixbugs_raw/`. Source: <https://github.com/jkoppel/QuixBugs>
(Lin, Koppel, Chen, Solar-Lezama, SPLASH 2017 Companion).

Excluded from the benchmark (9 algorithms): `breadth_first_search`,
`depth_first_search`, `detect_cycle`, `minimum_spanning_tree`,
`reverse_linked_list`, `shortest_path_length`, `shortest_path_lengths`,
`shortest_paths`, `topological_ordering`. **Reason:** these depend on a shared
`node.py` helper that is not part of the `tasks_v2/<task>/{buggy,fixed}/`
single-file convention. Their inclusion would require pipeline changes that
are out of scope for this study.

The fixed task list (31 entries):

```
bitcount, bucketsort, find_first_in_sorted, find_in_sorted, flatten, gcd,
get_factors, hanoi, is_valid_parenthesization, kheapsort, knapsack, kth,
lcs_length, levenshtein, lis, longest_common_subsequence, max_sublist_sum,
mergesort, next_palindrome, next_permutation, pascal, possible_change,
powerset, quicksort, rpn_eval, shunting_yard, sieve, sqrt, subsequences,
to_base, wrap
```

Difficulty (easy / medium / hard) and `bug_type` labels are **the authors'
attribution**, recorded in `scripts/convert_quixbugs.py:TASK_CATALOG`. Labels
were assigned before any full-benchmark run was executed and are
post-hoc-stratification covariates only — they do not affect the run itself
(the LLM never sees the difficulty label; only `bug_description` and
`test_hint` are passed via `bugtest/pipeline.py:_build_user_message`).

Distribution: 7 easy, 13 medium, 11 hard.

## 5. Models

Five LLMs are evaluated:

| Model ID                                       | Provider     |
| ---------------------------------------------- | ------------ |
| `meta/llama-3.1-8b-instruct`                   | NVIDIA Build |
| `meta/llama-3.3-70b-instruct`                  | NVIDIA Build |
| `meta/llama-4-maverick-17b-128e-instruct`      | NVIDIA Build |
| `openai/gpt-oss-120b`                          | NVIDIA Build |
| `sonnet` (Claude Sonnet 4.6)                   | Anthropic via Claude Code CLI |

### Pre-registered exclusions

1. **`mistralai/mistral-medium-3.5-128b` — fully excluded.**
   Justification: in the smoke run on 2026-05-10
   (`smoke_summary.json`, commit `29905ed`), this model produced 2 errors
   across baseline + agentic with a BRTR of 0.67 / 0.67 / 1.0, indicating
   instability. Including it would mix infrastructure failure with capability
   measurement. Listed but commented out in
   `scripts/smoke_test_all_models.py:33-34` and excluded from
   `scripts/run_full_benchmark.py:MODELS`.

2. **`openai/gpt-oss-120b` × `agentic` — excluded combination.**
   Justification: in the same smoke run this combination produced
   `pydantic.ValidationError` on `CodeAnalysis` for every attempt
   (0/0 successful runs). The Analyzer agent's structured output cannot be
   parsed for this model under our current schema. The model's `baseline` and
   `adaptive` modes worked normally and remain in the benchmark. Encoded in
   `scripts/run_full_benchmark.py:MODEL_MODE_EXCLUSIONS`.

#### Post-hoc deviations (logged honestly)

3. **`meta/llama-3.1-8b-instruct` — fully removed mid-run on 2026-05-10.**
   The first attempt of the full benchmark (results dir
   `analysis_vs_direct_20260510_190408`) produced 410/465 jobs with a
   NVIDIA-side `400 Bad Request: "Function id 'e62a4350-...': DEGRADED
   function cannot be invoked"` error. This is a service outage on
   NVIDIA Build's hosted endpoint, not an LLM-capability signal.
   Pre-mid-restart, this model was in the pre-registered set; its data is
   discarded for the primary analysis. The model may be re-added in a
   follow-up run once the endpoint recovers; that re-run will be reported
   separately and clearly labelled as a supplementary measurement.
   Effective primary-analysis model count: **4**.

## 6. Modes

Three pipeline modes (`bugtest/pipeline.py`):

- **baseline:** direct test generation, ≤3 retry attempts
- **agentic:** Analyzer first → analysis prepended to user message → TestWriter,
  ≤3 retry attempts
- **adaptive:** baseline-style attempt 1; on failure, Analyzer activated for
  attempts 2-3

## 7. Run parameters

- `runs_per_task: 5` (independent samples per (task, mode, model) cell)
- `max_attempts: 3` per run
- `temperature: 0.7`, `max_output_tokens: 4096`
- `concurrency: 8` (ThreadPoolExecutor in `bugtest/experiment.py`)
- `test_timeout_seconds: 30`

Total planned runs:
- 31 tasks × 5 models × 3 modes × 5 runs = **2 325 runs**
- Minus excluded `gpt-oss-120b × agentic` (31 × 5 = 155 runs) =
  **2 170 effective runs**

## 8. Analysis plan

Reported tables / figures, in order:

1. Per-model × per-mode BRTR with 95% Wilson CI
2. Per-model × per-mode × per-difficulty BRTR (post-hoc stratification)
3. Per-task `agentic - baseline` Δ-BRTR (which tasks benefit from the
   Analyzer)
4. Token / duration table (informational)
5. Failure-mode breakdown by `bug_type` (which categories LLMs miss)

No statistical significance test is pre-registered as primary — comparisons
are reported with CIs and effect sizes. If a hypothesis test is added
post-hoc, it will be labeled exploratory.

## 9. Stop / resume rules

- Per-job records are persisted immediately
  (`bugtest/experiment.py:_run_job` writes each `RunRecord` to disk under the
  task directory before the next job starts).
- If the run is interrupted, completed records are kept; the run is **not**
  re-randomized — interrupted (model, task, run, mode) cells will be re-run
  with `runs_per_task` topped up if needed.
- The full benchmark may be re-run after pre-registration only if a
  reproducible infrastructure bug is found (e.g., bug in
  `_run_job` itself); the bug must be documented in the report.

## 10. Threats to validity (acknowledged up-front)

- **Data contamination:** QuixBugs has been public on GitHub since 2017 and
  is highly likely present in every evaluated LLM's training corpus. Reported
  BRTR values are **upper bounds** on capability; do not interpret as
  out-of-distribution measurement.
- **Difficulty labels are authors' attribution**, not from the QuixBugs
  paper. Reasoning is in the `TASK_CATALOG` comments and will be discussed
  in the report.
- **Excluded graph algorithms (n=9)** make this a benchmark on
  "non-graph QuixBugs Python", not all of QuixBugs.
- **No non-LLM baseline** (Pynguin, Hypothesis, etc.) — comparisons are
  LLM-vs-LLM only. Absolute BRTR must not be interpreted as
  "tool quality"; only relative model/mode comparisons are within scope.
- **Concurrency-induced variation** in `duration_seconds` and token counts
  is expected. BRTR is a binary outcome and is not affected.

---

End of pre-registration.
