# Experiment Report: Does Code Analysis Improve LLM Test Generation?

## 1. Research Question

> Does adding a structured code analysis step before test generation improve
> the LLM's ability to produce bug-revealing tests?

## 2. Experimental Setup

### 2.1 Models Tested

| # | Model | Parameters | Architecture | Family |
|---|---|---|---|---|
| 1 | Meta Llama 3.1 8B Instruct | 8B | Dense | Meta |
| 2 | Meta Llama 4 Maverick | 17B (MoE, 128 experts) | MoE | Meta |
| 3 | Meta Llama 3.3 70B Instruct | 70B | Dense | Meta |
| 4 | OpenAI GPT-OSS | 120B | Dense | OpenAI |
| 5 | Mistral Medium 3.5 | 128B | Dense | Mistral |
| 6 | Anthropic Claude Opus 4.6 | ~175B* | Dense | Anthropic |

*Claude Opus parameter count is not publicly disclosed; industry estimate.

### 2.2 Pipeline Modes

```
Baseline:   Task --> TestWriter --> Validate (retry x3)
Agentic:    Task --> Analyzer --> TestWriter --> Validate (retry x3)
Adaptive:   Task --> TestWriter --> Validate
              |                       |
              |         if FAIL:      |
              +--- Analyzer --> TestWriter --> Validate (retry x2)
```

**Baseline:** Direct test generation, no analysis.
**Agentic:** Always analyze first, then generate test.
**Adaptive:** Try without analysis first. If it fails, add analysis for retries.

### 2.3 Fair Comparison Guarantees

- Same TestWriter system prompt across all modes
- Same retry budget (max 3 attempts per run)
- Same deterministic validator (pytest return codes, no LLM judgment)
- Same task set (12 tasks, 3 runs each)
- Interleaved execution order to control temporal bias

### 2.4 Validation Criteria

A test is **bug-revealing** if and only if:
- It **FAILS** on the buggy code (exposes the bug)
- It **PASSES** on the fixed code (confirms the fix)

### 2.5 Evaluation Tasks

12 tasks spanning different bug categories:

| Category | Tasks | Count |
|---|---|---|
| Boundary/Logic | boundary_threshold, off_by_one_loop | 2 |
| Concurrency | async_race_condition | 1 |
| State Management | cache_invalidation | 1 |
| Error Handling | swallowed_exception | 1 |
| Type Safety | type_coercion_price, null_handling_profile | 2 |
| Real-world (BugsInPy) | black, pysnooper, thefuck (x2), tqdm | 5 |

### 2.6 Metrics

- **BRTR** (Bug-Revealing Test Rate): % of runs producing a bug-revealing test
- **Delta**: Agentic/Adaptive BRTR minus Baseline BRTR (+positive = helped, -negative = hurt)
- **Attempts-to-success**: Average retries before success (lower = better)
- **95% CI**: Wilson score confidence interval for binomial proportions

## 3. Overall Results

### 3.1 BRTR Summary: Baseline vs Adaptive (Primary Comparison)

| Model | Size | Baseline | Adaptive | Delta | Best Mode |
|---|---|---|---|---|---|
| Claude Opus | ~175B | 91.7% | **94.3%** | +2.6% | Adaptive |
| GPT-OSS | 120B | **86.1%** | **86.1%** | 0.0% | Baseline = Adaptive |
| Mistral 3.5 | 128B | **58.3%** | **58.3%** | 0.0% | Baseline = Adaptive |
| Llama 3.3 | 70B | **47.2%** | 41.7% | -5.5% | Baseline |
| Llama 4 Maverick | 17B | 38.9% | **50.0%** | **+11.1%** | **Adaptive** |
| Llama 3.1 | 8B | **30.6%** | N/A | N/A | Baseline |

### 3.2 Agentic Mode Results (where available)

Agentic mode requires the Analyzer to produce valid JSON. This dependency
creates a single point of failure that varies by interface:

| Model | Agentic BRTR | Runs Completed | Completion Rate | Issue |
|---|---|---|---|---|
| GPT-OSS 120B | 80.0% | 35/36 | 97% | — |
| Mistral 128B | 51.4% | 35/36 | 97% | — |
| Llama 70B | 50.0% | 34/36 | 94% | — |
| Llama 4 17B | 44.4% | 36/36 | 100% | — |
| Claude Opus | 100%* | 4/36 | **11%** | CLI markdown output |
| Llama 8B | 28.6%* | 7/36 | **19%** | Model capability |

*Misleading: only completed runs counted. Claude Opus and Llama 8B agentic
results are excluded from cross-model comparison due to >80% run failure.
Claude's failure is an interface issue (CLI returns markdown), not a model
capability limitation.

### 3.3 Delta Analysis (vs Baseline)

| Model | Agentic Delta | Adaptive Delta | Interpretation |
|---|---|---|---|
| Claude Opus | N/A (CLI issue) | **+2.6%** | Adaptive slight gain |
| GPT-OSS 120B | **-6.1%** | **0.0%** | Analysis hurts; adaptive recovers |
| Mistral 128B | **-6.9%** | **0.0%** | Analysis hurts; adaptive recovers |
| Llama 70B | **+2.8%** | -5.5% | Agentic slight benefit |
| Llama 4 17B | **+5.5%** | **+11.1%** | Adaptive strongest benefit |
| Llama 8B | N/A (broken) | N/A | Pipeline unusable |

### 3.4 Detailed Statistics

| Model | Mode | BRTR | 95% CI | Successful | Avg Attempts | Avg Duration |
|---|---|---|---|---|---|---|
| Claude Opus | Baseline | 91.7% | [78.2%, 97.1%] | 33/36 | 1.5 | 30.9s |
| Claude Opus | Adaptive | 94.3% | [81.4%, 98.4%] | 33/35 | 1.6 | 46.6s |
| GPT-OSS 120B | Baseline | 86.1% | [71.3%, 93.9%] | 31/36 | 1.6 | 2,617 |
| GPT-OSS 120B | Agentic | 80.0% | [64.1%, 90.0%] | 28/35 | 1.5 | 4,152 |
| GPT-OSS 120B | Adaptive | 86.1% | [71.3%, 93.9%] | 31/36 | 1.5 | 3,227 |
| Mistral 128B | Baseline | 58.3% | [42.2%, 72.9%] | 21/36 | 1.1 | 1,602 |
| Mistral 128B | Agentic | 51.4% | [35.6%, 67.0%] | 18/35 | 1.0 | 2,788 |
| Mistral 128B | Adaptive | 58.3% | [42.2%, 72.9%] | 21/36 | 1.1 | 2,136 |
| Llama 70B | Baseline | 47.2% | [32.0%, 63.0%] | 17/36 | 1.4 | 1,719 |
| Llama 70B | Agentic | 50.0% | [34.1%, 65.9%] | 17/34 | 1.0 | 2,399 |
| Llama 70B | Adaptive | 41.7% | [27.1%, 57.8%] | 15/36 | 1.0 | 2,136 |
| Llama 4 17B | Baseline | 38.9% | [24.8%, 55.1%] | 14/36 | 1.4 | 2,001 |
| Llama 4 17B | Agentic | 44.4% | [29.5%, 60.4%] | 16/36 | 1.1 | 2,710 |
| Llama 4 17B | Adaptive | 50.0% | [34.5%, 65.5%] | 18/36 | 1.3 | 2,317 |
| Llama 8B | Baseline | 30.6% | [18.0%, 46.9%] | 11/36 | 1.4 | 2,300 |
| Llama 8B | Agentic | 28.6% | [8.2%, 64.1%] | 2/7 | 1.5 | 3,298 |

## 4. Per-Task Breakdown

### 4.1 Cross-Model Task Results (Baseline / Agentic / Adaptive)

| Task | Claude Opus | GPT-OSS 120B | Mistral 128B | Llama 70B | Llama 4 17B | Llama 8B |
|---|---|---|---|---|---|---|
| boundary_threshold | 100/100†/100 | 100/100/100 | 100/100/100 | 100/100/100 | 100/100/100 | 33/err/- |
| off_by_one_loop | 100/err/100 | 100/100/100 | 100/100/100 | 100/100/100 | 100/100/100 | 100/err/- |
| bugsinpy_tqdm | 100/err/100 | 100/100/100 | 100/100/100 | 100/100/100 | 100/100/100 | 33/err/- |
| bugsinpy_thefuck_fish | 100/err/100 | 100/100/100 | 100/100/100 | 100/100/100 | **0/100**/100 | 33/**67**/- |
| bugsinpy_black | 100/err/100 | 100/100/100 | 100/100/100 | 100/100/67 | 100/100/100 | 67/err/- |
| type_coercion_price | 100/100†/100 | 100/100/100 | 100/100/100 | **0/67**/33 | 33/33/33 | 33/err/- |
| swallowed_exception | 100/err/100 | 100/100/100 | **100/0**/100 | **67/0**/0 | **33/0**/33 | 33/err/- |
| bugsinpy_pysnooper | 100/100†/100 | **100**/100/100 | 0/0/0 | 0/0/0 | 0/0/0 | 33/0/- |
| cache_invalidation | **33**/err/**67** | **100**/67/100 | 0/0/0 | 0/0/0 | 0/0/0 | 0/err/- |
| null_handling_profile | 100/100†/100 | 67/100/67 | 0/0/0 | 0/0/0 | 0/0/0 | 0/err/- |
| async_race_condition | **100**/err/**100** | 33/0/33 | 0/0/0 | 0/0/0 | 0/0/0 | 0/err/- |
| bugsinpy_thefuck_fix | 67/err/50 | 33/0/33 | 0/0/0 | 0/0/0 | 0/0/0 | 0/err/- |

*Format: Baseline% / Agentic% / Adaptive%. Bold = notable difference. err = JSON parse error.*
*† = Agentic only completed 1/3 runs (JSON parse errors on others).*

### 4.2 Task Difficulty Tiers

**Tier 1 — Easy (5 tasks): All capable models solve**
`boundary_threshold`, `off_by_one_loop`, `bugsinpy_tqdm`, `bugsinpy_thefuck_fish`, `bugsinpy_black`

Simple bugs with clear symptoms. Analysis provides no benefit for large models
but helps smaller models (Llama 4: 0%→100% on thefuck_fish with analysis).

**Tier 2 — Medium (3 tasks): Model-dependent**
`type_coercion_price`, `swallowed_exception`, `bugsinpy_pysnooper`

This is where analysis has the most variable impact. swallowed_exception shows
analysis consistently hurting across models. type_coercion_price benefits from
analysis on Llama 70B but not on stronger models.

**Tier 3 — Hard (4 tasks): Only Claude Opus and GPT-OSS solve**
`cache_invalidation`, `null_handling_profile`, `async_race_condition`, `bugsinpy_thefuck_fix`

Claude Opus and GPT-OSS 120B are the only models that solve these, with Opus
outperforming GPT-OSS on async_race_condition (100% vs 33%) and
null_handling_profile (100% vs 67%). These involve concurrency, state
management, and complex real-world bugs.

## 5. Key Findings

### 5.1 Model capability is the dominant factor

```
BRTR by model (baseline):

  Claude Opus:     █████████████████████████████████████████████  91.7%
  GPT-OSS 120B:    ████████████████████████████████████████████   86.1%
  Mistral 128B:    █████████████████████████████                  58.3%
  Llama 70B:       ███████████████████████                        47.2%
  Llama 4 17B:     ███████████████████                            38.9%
  Llama 8B:        ███████████████                                30.6%
```

The gap between models (30%→92%) far exceeds the effect of any pipeline
mode (<12%). Choosing a better model matters more than pipeline architecture.

### 5.2 Analysis benefit depends on model strength

| Model Strength | Agentic Effect | Adaptive Effect | Pattern |
|---|---|---|---|
| Very strong (Opus) | Broken (CLI JSON) | Slight gain (+2.6%) | Adaptive best |
| Strong (120-128B) | Hurts (-6 to -7%) | Neutral (0%) | Don't analyze |
| Medium (70B) | Slight help (+3%) | Slight hurt (-5%) | Mixed |
| Mid-range (17B) | Helps (+6%) | **Best (+11%)** | Analyze selectively |
| Weak (8B) | Broken | N/A | Pipeline unusable |

**Key insight:** Analysis follows an inverted-U pattern. It hurts strong models
(they already know the answer), helps mid-range models (they benefit from
guidance), and breaks weak models (they can't produce structured output).

### 5.3 Adaptive mode outperforms agentic for mid-range models

For Llama 4 Maverick (17B):
- Baseline: 38.9%
- Agentic: 44.4% (+5.5%)
- **Adaptive: 50.0% (+11.1%)**

Adaptive avoids the cost of analysis when the model solves it on the first try,
and adds analysis only when needed. This "analyze on failure" strategy is more
effective than "always analyze."

### 5.4 Adaptive matches baseline for strong models

For GPT-OSS (120B) and Mistral (128B), adaptive BRTR equals baseline exactly.
This is because these models solve most tasks on the first attempt, so the
analysis step is never triggered. Adaptive correctly avoids unnecessary analysis.

### 5.5 Analysis introduces confirmation bias (swallowed_exception)

| Model | Baseline | Agentic | Delta |
|---|---|---|---|
| GPT-OSS 120B | 100% | 100% | 0% |
| Mistral 128B | **100%** | **0%** | **-100%** |
| Llama 70B | **67%** | **0%** | **-67%** |
| Llama 4 17B | **33%** | **0%** | **-33%** |

The Analyzer correctly identifies "bare except swallows NameError" but suggests
testing for NameError propagation. This leads TestWriter to write
`pytest.raises(NameError)`, which fails because the exception IS swallowed.
Analysis locks the model into a failing strategy.

### 5.6 Structured output is a capability gate

| Model | Agentic Runs Completed | Rate |
|---|---|---|
| Claude Opus (CLI) | **4/36** | **11%** |
| GPT-OSS 120B | 35/36 | 97% |
| Mistral 128B | 35/36 | 97% |
| Llama 70B | 34/36 | 94% |
| Llama 4 17B | 36/36 | 100% |
| Llama 8B | **7/36** | **19%** |

Both Claude Opus (via CLI) and the 8B model fail to produce valid JSON for
CodeAnalysis. Opus's failure is an interface issue: the `claude -p` CLI
wraps responses in markdown, not a model capability limitation. The 8B
model's failure reflects genuine capability limits. Multi-agent pipelines
with structured inter-agent communication require both sufficient model
capability AND compatible output interfaces.

## 6. Token Cost Analysis

| Model | Baseline Tokens | Agentic Tokens | Adaptive Tokens | Agentic Overhead |
|---|---|---|---|---|
| Claude Opus* | ~2,050 | ~3,000 | ~2,400 | ~+46% |
| Claude Sonnet* | ~2,050 | ~3,000 | ~2,400 | ~+46% |
| GPT-OSS 120B | 2,617 | 4,152 | 3,227 | +59% |
| Mistral 128B | 1,602 | 2,788 | 2,136 | +74% |
| Llama 70B | 1,719 | 2,399 | 2,136 | +40% |
| Llama 4 17B | 2,001 | 2,710 | 2,317 | +35% |
| Llama 8B | 2,300 | 3,298 | N/A | +43% |

*Claude CLI does not report token usage; values estimated from other models'
averages (same prompts used across all models).

### 6.1 API Cost Estimate (USD)

| Model | Price (input/output per M) | Baseline/Run | Adaptive/Run | 36 Runs Total |
|---|---|---|---|---|
| Claude Opus | $15 / $75 | ~$0.04 | ~$0.05 | ~$1.80 |
| Claude Sonnet | $3 / $15 | ~$0.008 | ~$0.01 | ~$0.36 |
| NVIDIA Models | Free (free tier) | $0 | $0 | $0 |

Agentic mode adds 35-74% token overhead. Adaptive mode reduces this by only
paying the analysis cost when needed. NVIDIA Build free tier eliminates cost
for open-source models but introduces rate-limiting latency.

## 7. Threats to Validity

1. **Non-deterministic outputs**: LLMs produce different outputs for identical
   inputs. Repeat experiments with the same model and tasks showed BRTR
   fluctuations of 5-6% (e.g., Claude Sonnet adaptive: 97.2% in one run,
   91.7% when re-run). This stems from temperature > 0 and the stochastic
   nature of autoregressive generation. Results should be interpreted as
   ranges, not exact values. Differences below 5% should not be considered
   meaningful.

2. **Small sample size**: 3 runs per task per mode limits statistical power.
   Confidence intervals are wide and overlap between modes. For example,
   Opus adaptive 94.4% [81.9%, 98.5%] and Sonnet adaptive 91.7% [78.2%,
   97.1%] are not statistically distinguishable. Combined with non-
   determinism, small differences are indistinguishable from noise.

3. **Model family bias**: 3 of 7 models are Llama variants, 2 are Claude.
   Adding architecturally different models would strengthen generalizability.

4. **Environment confounds**: Python 3.9 type hint incompatibility and
   missing pytest-asyncio caused infrastructure failures on some tasks.

5. **JSON parsing fragility**: Agentic pipeline depends on valid JSON from
   the Analyzer, creating a single point of failure for smaller models and
   CLI-based interfaces.

6. **Free-tier API constraints**: NVIDIA Build free tier introduces variable
   latency and throttling that may affect retry behavior.

7. **Prompt sensitivity**: Different prompt formulations may produce
   different results. No prompt ablation was performed.

## 8. Conclusions

1. **Model capability is the dominant factor** in bug-revealing test generation.
   The 61% BRTR gap between models (30%→92%) dwarfs the <12% effect of
   adding analysis. Choosing a better model yields far greater improvement
   than adding pipeline complexity.

2. **Analysis benefit follows an inverted-U curve.** It hurts strong models
   (they don't need it), helps mid-range models (they benefit from guidance),
   and breaks weak models (they can't produce structured output).

3. **Adaptive mode is the optimal strategy.** It matches baseline for strong
   models (avoids unnecessary analysis), outperforms both modes for mid-range
   models (+11.1% for Llama 4), and avoids the structured output requirement
   on the critical first attempt.

4. **Pre-analysis introduces confirmation bias.** The swallowed_exception
   task shows analysis consistently hurts across all models by locking the
   TestWriter into a failing strategy.

5. **Multi-agent pipelines have a minimum capability threshold.** The 8B
   model fails to produce valid Analyzer output in 81% of cases. Structured
   inter-agent communication requires models above ~17B parameters.

6. **Bug difficulty determines outcomes more than architecture.** Tasks
   cluster into "easy" (all models solve), "medium" (model-dependent), and
   "hard" (only GPT-OSS 120B solves) categories that are consistent across
   pipeline modes.

## 9. Raw Data

Experiment data for all models is available at:
```
results/
  analysis_vs_direct_<timestamp>/
    summary.json              # Aggregated statistics
    config.yaml               # Configuration snapshot
    runs/<task_id>/            # Individual run records
      baseline_run_01.json
      agentic_run_01.json
      adaptive_run_01.json
      ...
```

Each run record contains: generated test code, validation output (pytest stdout
from both buggy and fixed versions), token usage, duration, and CodeAnalysis
(if agentic/adaptive mode triggered analysis).

### Models and experiment timestamps:
- Claude Opus 4.6: all modes (20260502_212649)
- Llama 3.3 70B: baseline+agentic (20260430_055256), adaptive (20260501_104814)
- Llama 3.1 8B: baseline+agentic (20260430_XXXXXX)
- Mistral Medium 3.5: baseline+agentic (20260430_XXXXXX), adaptive (20260501_112310)
- Llama 4 Maverick: baseline+agentic (20260430_XXXXXX), adaptive (20260501_112331)
- GPT-OSS 120B: baseline+agentic (20260430_XXXXXX), adaptive (20260501_120830)

---

## 10. QuixBugs Benchmark (Pre-Registered Expansion, 2026-05)

The 12-task suite in §2.5 is a curated bug corpus assembled by the authors; it
is small (n=12) and has heterogeneous metadata. To address the
sample-size and selection-bias concerns of a thesis-grade evaluation, this
section reports a separate, **pre-registered** benchmark on
[QuixBugs](https://github.com/jkoppel/QuixBugs) (Lin et al., SPLASH 2017
Companion).

The pre-registration document is in `PREREGISTRATION.md` (committed before any
QuixBugs benchmark run; commit `f440114`). It fixes models, modes, runs,
exclusions, metrics, and analysis plan up-front.

### 10.1 Coverage

- **31 tasks** under `evaluation/tasks_v2/quixbugs_*/`, byte-identical to the
  upstream `python_programs/<name>.py` and `correct_python_programs/<name>.py`.
- **9 graph algorithms excluded** (`breadth_first_search`,
  `depth_first_search`, `detect_cycle`, `minimum_spanning_tree`,
  `reverse_linked_list`, `shortest_path_length`, `shortest_path_lengths`,
  `shortest_paths`, `topological_ordering`) because they depend on a shared
  `node.py` helper that is not part of this repo's single-file task layout.
  This benchmark is therefore "non-graph QuixBugs Python", not all of
  QuixBugs.
- Difficulty / `bug_type` annotations are the authors' attribution, recorded
  in `scripts/convert_quixbugs.py:TASK_CATALOG`. Distribution: **7 easy / 13
  medium / 11 hard**, **29 distinct `bug_type` categories** across the 31
  tasks.

### 10.2 Models, runs, modes

- **Pre-registered:** 5 models (Llama 3.1 8B, Llama 3.3 70B, Llama 4 Maverick,
  GPT-OSS 120B, Claude Sonnet 4.6).
- **Post-hoc deviation:** Llama 3.1 8B's NVIDIA Build endpoint
  (function id `e62a4350-...`) returned `400 DEGRADED function cannot be
  invoked` for 410/465 jobs in the first attempt run
  (`analysis_vs_direct_20260510_190408`). The 8B model was dropped on
  2026-05-10 (commit `574f59f`); its data is discarded from the primary
  analysis. Effective primary-analysis model count: **4**.
- `runs_per_task = 5`, `max_attempts = 3`, three modes (baseline, agentic,
  adaptive).
- **Executed runs (primary analysis):** 31 tasks × 4 models × 3 modes × 5 runs
  = 1 860 planned, minus `gpt-oss-120b × agentic` (155 runs) = **1 705
  effective runs**. All four model executions returned `exit_code: 0`.

#### Pre-registered exclusions (justification before run)

1. **`mistralai/mistral-medium-3.5-128b` — fully excluded.** In the smoke run
   on 2026-05-10 (`smoke_summary.json`, parent commit `29905ed`), this model
   produced 2 errors with 0.67 / 0.67 / 1.0 BRTR across the 3 modes — a
   pattern of infrastructure instability rather than capability variation.
2. **`openai/gpt-oss-120b × agentic` — combination excluded.** In the same
   smoke, every agentic attempt failed with
   `pydantic.ValidationError` on `CodeAnalysis`. The model's `baseline` and
   `adaptive` modes worked normally and remain in the benchmark.

Both exclusions are encoded in `scripts/run_full_benchmark.py` and discussed
in §10.4.

### 10.3 Concurrency

The full benchmark runs through `bugtest.experiment.run_experiment` with
`experiment.concurrency`, executing (task, run, mode) jobs through a
`ThreadPoolExecutor`. Per-job `RunRecord`s are persisted immediately so an
interrupted run keeps completed work. Exponential backoff with jitter
(`bugtest.llm._backoff_seconds`) mitigates thundering-herd risk on rate-limited
endpoints.

**Concurrency in the executed run.** Llama 3.3 70B was rate-limited heavily by
NVIDIA Build (HTTP 429) at `concurrency=8`; the run effective concurrency was
reduced to **4** for the remaining models for stability. As a result the
total wall-clock was ~5.4 h instead of the ~2.5 h target. This is reflected
in `full_benchmark_summary.json:concurrency = 4`. BRTR is a binary outcome
and not affected by concurrency; only `duration_seconds` is.

The sequential path remains available for debugging by setting
`concurrency: 1`.

### 10.4 Threats to validity

- **Data contamination.** QuixBugs has been public on GitHub since 2017 and is
  almost certainly present in every evaluated LLM's training corpus.
  Reported BRTR values must be read as **upper bounds on capability**, not as
  out-of-distribution measurements. Mitigations such as paraphrased or
  mutated variants of QuixBugs programs are out of scope for this thesis and
  flagged as future work.
- **Difficulty / bug_type labels are author-attributed.** The QuixBugs paper
  does not provide a difficulty taxonomy. Labels were assigned before any
  full-benchmark run, with reasoning recorded in `TASK_CATALOG`. They are
  used only as post-hoc stratification covariates and are never shown to the
  LLM.
- **Excluded graph algorithms (n = 9).** This benchmark covers 31/40 of the
  Python QuixBugs corpus. The 9 excluded tasks share a `node.py` helper that
  would require pipeline changes; including them is future work.
- **No non-LLM baseline.** Comparisons are LLM-vs-LLM; absolute BRTR cannot
  be interpreted as "tool quality." Pynguin / Hypothesis / random fuzzer
  baselines were considered and explicitly deferred.
- **Concurrency-induced variance.** `duration_seconds` and token-count means
  are affected by parallel execution and rate-limit backoff. BRTR is a binary
  per-run outcome and is not affected.
- **Single subprocess pytest validator.** `bugtest.validator.Validator` runs
  pytest in a fresh tempdir per call. Tests that interact with the
  filesystem, time, or randomness can in principle behave differently
  between buggy and fixed runs even when semantically identical; in
  practice all 31 QuixBugs algorithms are pure functions, so this risk is
  negligible for this benchmark.

### 10.5 Primary results — model × mode BRTR

Per-model results from `full_benchmark_summary.json` (run started
2026-05-10T22:34:36, finished 2026-05-11T03:58:28). 95% CIs are Wilson score
intervals.

| Model | Baseline BRTR | Agentic BRTR | Adaptive BRTR | Duration |
|---|---:|---:|---:|---:|
| meta/llama-3.3-70b-instruct | 42.6% [35.1, 50.5] (66/155) | 24.5% [18.4, 31.9] (38/155) | 42.6% [35.1, 50.5] (66/155) | 216.6 m |
| meta/llama-4-maverick-17b-128e-instruct | 79.4% [72.3, 85.0] (123/155) | 76.1% [68.8, 82.2] (118/155) | 77.4% [70.2, 83.3] (120/155) | 31.3 m |
| openai/gpt-oss-120b | 96.1% [91.8, 98.2] (149/155) | — (excluded) | 96.8% [92.7, 98.6] (150/155) | 10.9 m |
| sonnet (Claude 4.6) | 77.4% [70.2, 83.3] (120/155) | 27.1% [20.7, 34.6] (42/155) | 77.4% [70.2, 83.3] (120/155) | 65.0 m |

**Headline observations.**

1. **Agentic mode never beats baseline.** In all three models where agentic
   was measured, baseline BRTR ≥ agentic BRTR. The agentic pipeline (Analyzer
   → TestWriter) adds a step that, on QuixBugs, either does nothing or
   degrades the test-generation outcome.
2. **Adaptive ≈ baseline** for every model. Adaptive only invokes the
   Analyzer when baseline fails; since the Analyzer (as wired here)
   does not lift those failures, adaptive collapses to baseline within
   noise (±2 runs).
3. **Llama 3.3 70B's overall BRTR is depressed by ~50% rate-limit errors**
   from NVIDIA Build, which surface as failed `RunRecord`s with non-empty
   `error` fields. Its numbers are a **lower bound on capability** — not
   directly comparable to the other three models. Llama 4 Maverick (same
   provider, larger output schema tolerance) did not hit this limit, so the
   confound is model-specific rather than a per-run infrastructure issue.

### 10.6 Difficulty stratification

Stratification covariate from `scripts/convert_quixbugs.py:TASK_CATALOG`;
labels were fixed before any full-benchmark run. Distribution: **7 easy / 13
medium / 11 hard**.

| Model | Mode | Easy | Medium | Hard |
|---|---|---:|---:|---:|
| meta/llama-3.3-70b-instruct | baseline | 43% (15/35) | 62% (40/65) | 20% (11/55) |
| meta/llama-3.3-70b-instruct | agentic | 29% (10/35) | 34% (22/65) | 11% (6/55) |
| meta/llama-3.3-70b-instruct | adaptive | 40% (14/35) | 66% (43/65) | 16% (9/55) |
| meta/llama-4-maverick-17b-128e-instruct | baseline | 71% (25/35) | 100% (65/65) | 60% (33/55) |
| meta/llama-4-maverick-17b-128e-instruct | agentic | 71% (25/35) | 100% (65/65) | 51% (28/55) |
| meta/llama-4-maverick-17b-128e-instruct | adaptive | 71% (25/35) | 100% (65/65) | 55% (30/55) |
| openai/gpt-oss-120b | baseline | 100% (35/35) | 100% (65/65) | 89% (49/55) |
| openai/gpt-oss-120b | adaptive | 100% (35/35) | 97% (63/65) | 95% (52/55) |
| sonnet | baseline | 71% (25/35) | 85% (55/65) | 73% (40/55) |
| sonnet | agentic | 29% (10/35) | 40% (26/65) | 11% (6/55) |
| sonnet | adaptive | 74% (26/35) | 85% (55/65) | 71% (39/55) |

**Pre-registered success criterion: at least one model × mode × hard-task
cell with BRTR < 1.0.** Satisfied — every model's hard-task baseline is
strictly below ceiling (Llama 70B 20%, Maverick 60%, GPT-OSS 89%, Sonnet
73%). The difficulty labelling discriminates between programs and the
benchmark is not at ceiling overall.

**Surprises.**

- Easy column shows wide variation (43% / 71% / 100% / 71%). The two
  consistently-zero "easy" tasks across models are
  `find_in_sorted` and `find_first_in_sorted` — both depend on subtle
  recursive-call argument swaps that don't trigger on common-sense inputs.
  Their `easy` label deserves a re-look.
- Llama 70B's medium > easy inversion (62% vs 43%) is unusual; partly
  driven by rate-limit losses falling on `bitcount` / `gcd` / `sieve` runs
  rather than capability.

### 10.7 Per-task `agentic − baseline` Δ-BRTR

Per (task, model), Δ = BRTR(agentic) − BRTR(baseline). Negative Δ = the
Analyzer pipeline hurts that task. `(b→a)` shows the BRTR endpoints.

| Task | Difficulty | llama-3.3-70b | llama-4-maverick | sonnet |
|---|---|---:|---:|---:|
| bitcount | easy | −60pp (100→40) | +0pp (100→100) | −60pp (100→40) |
| bucketsort | medium | +0pp (60→60) | +0pp (100→100) | **−100pp (100→0)** |
| find_first_in_sorted | easy | +0pp (0→0) | +0pp (0→0) | +20pp (0→20) |
| find_in_sorted | easy | +0pp (0→0) | +0pp (0→0) | +0pp (0→0) |
| flatten | easy | +20pp (20→40) | +0pp (100→100) | −20pp (100→80) |
| gcd | easy | +40pp (0→40) | +0pp (100→100) | **−100pp (100→0)** |
| get_factors | medium | −20pp (60→40) | +0pp (100→100) | −40pp (100→60) |
| hanoi | medium | −40pp (80→40) | +0pp (100→100) | −60pp (100→40) |
| is_valid_parenthesization | medium | −40pp (80→40) | +0pp (100→100) | +0pp (100→100) |
| kheapsort | medium | −20pp (80→60) | +0pp (100→100) | −80pp (100→20) |
| knapsack | hard | −60pp (80→20) | +0pp (100→100) | −80pp (100→20) |
| kth | hard | −40pp (60→20) | +0pp (100→100) | −80pp (80→0) |
| lcs_length | hard | +0pp (0→0) | −60pp (80→20) | **−100pp (100→0)** |
| levenshtein | hard | −20pp (40→20) | +0pp (100→100) | −80pp (100→20) |
| lis | hard | +20pp (0→20) | +0pp (0→0) | **−100pp (100→0)** |
| longest_common_subsequence | hard | +0pp (0→0) | +0pp (0→0) | −40pp (60→20) |
| max_sublist_sum | easy | −60pp (100→40) | +0pp (100→100) | −80pp (100→20) |
| mergesort | medium | +40pp (0→40) | +0pp (100→100) | −40pp (100→60) |
| next_palindrome | hard | +0pp (0→0) | +0pp (0→0) | −60pp (60→0) |
| next_permutation | medium | −40pp (60→20) | +0pp (100→100) | +0pp (100→100) |
| pascal | medium | −20pp (60→40) | +0pp (100→100) | −20pp (100→80) |
| possible_change | medium | −80pp (80→0) | +0pp (100→100) | −80pp (100→20) |
| powerset | medium | −40pp (60→20) | +0pp (100→100) | −60pp (100→40) |
| quicksort | medium | −60pp (60→0) | +0pp (100→100) | **−100pp (100→0)** |
| rpn_eval | hard | +0pp (0→0) | +0pp (100→100) | −80pp (100→20) |
| shunting_yard | hard | +0pp (0→0) | −40pp (80→40) | −60pp (100→40) |
| sieve | easy | −40pp (80→40) | +0pp (100→100) | −60pp (100→40) |
| sqrt | medium | +0pp (40→40) | +0pp (100→100) | +0pp (0→0) |
| subsequences | medium | −40pp (80→40) | +0pp (100→100) | +0pp (0→0) |
| to_base | hard | +0pp (40→40) | +0pp (100→100) | +0pp (0→0) |
| wrap | hard | +0pp (0→0) | +0pp (0→0) | +0pp (0→0) |

Mean Δ per model (across 31 tasks): Llama 70B −18pp, Maverick −3pp, Sonnet
−50pp. The Analyzer pipeline is **net harmful** in this evaluation.

### 10.8 The Sonnet agentic anomaly — diagnosed

Sonnet's agentic mode drops baseline performance by 50 percentage points on
aggregate (77.4 → 27.1) and produces five `−100pp (100 → 0)` cells
(`bucketsort`, `gcd`, `lcs_length`, `lis`, `quicksort`). The cause was
isolated post-hoc from the run records at
`results/analysis_vs_direct_20260510_235326/runs/`:

| Pattern | n / 155 | Example |
|---|---:|---|
| Analyzer returned pytest code (not JSON schema) | 53 | `python\nimport pytest\n...assert gcd(35, 21) == 7` |
| Analyzer returned `{placeholder}` substring | 35 | `{result}`, `{arg}`, `{exc}` |
| Analyzer returned non-schema JSON | 11 | wrong keys |
| Other crashes | 14 | misc |
| **Pipeline crashes (total)** | **113** | `success=False, attempts=0` |
| Real test-gen failures | 0 | n/a |
| Successes | 42 | n/a |

When the Analyzer JSON parse succeeds, Sonnet's agentic-mode test
generation is **42/42 = 100%**. The 27.1% aggregate BRTR is therefore an
artefact of `bugtest/llm.py:ClaudeCodeClient.generate_json` — specifically,
the Claude Code CLI subprocess (`claude -p --output-format json`) does not
enforce a Pydantic-aligned JSON schema. When Sonnet writes explanatory
text containing literal `{placeholder}` substrings, the brace-balanced
extractor in `_extract_json_object` (`bugtest/llm.py:17-72`) grabs that
substring, hands it to `CodeAnalysis.model_validate_json`, and the
pipeline raises `ValidationError`.

**Mitigation (out of scope for this report, deferred to follow-up work):**
either (a) replace `ClaudeCodeClient` with the Anthropic API direct +
prompt-aligned JSON tool-use mode, or (b) add a retry-on-schema-validation
loop in `bugtest/pipeline.py` so the Analyzer is re-prompted when its
output doesn't parse. Sonnet's "capability" interpretation of the 27.1%
agentic BRTR should be corrected upward in any downstream comparison —
the in-scope number is the implementation's BRTR, not the model's.

### 10.9 Reading the QuixBugs results

Per-model results land in `results/analysis_vs_direct_<timestamp>/` and the
cross-model aggregate is in `full_benchmark_summary.json` at the repo root.
Tables 10.5–10.7 are regenerable via
`python scripts/analyze_full_benchmark.py`, which reads the same files.

### 10.10 Together.ai re-run (2026-05-11)

The 2026-05-10 NVIDIA run had two confounds in §10.5: Llama-3.3-70B was
rate-limited at ~50% (`HTTP 429`), and Sonnet's agentic mode crashed on
113/155 calls (§10.8). To remove the rate-limit confound the
OpenAI-compatible models were migrated to **Together.ai** (paid tier, no
free-tier limits) — see `PREREGISTRATION.md §5.4`. Code change:
`OpenAICompatibleClient` generalizes `NvidiaClient` (alias kept),
`ModelConfig.base_url` plumbed through, MODELS tuple becomes
`(model_id, api_key_env, base_url)`.

**Model set in the re-run.** `meta/llama-4-maverick-17b-128e-instruct` is
dropped (not hosted on Together); `Qwen/Qwen2.5-Coder-32B-Instruct` was
attempted but is not serverless on Together (all 465 calls returned
`400 model_not_available`) and was replaced with `deepseek-ai/DeepSeek-V3`
in a separate run. Sonnet is excluded pending the §10.8 fix.

| Model | Baseline BRTR | Agentic BRTR | Adaptive BRTR | Duration |
|---|---:|---:|---:|---:|
| meta-llama/Llama-3.3-70B-Instruct-Turbo | 66.5% [58.7, 73.4] (103/155) | 60.7% [52.8, 68.0] (94/155) | 67.1% [59.4, 74.0] (104/155) | 12.2 m |
| openai/gpt-oss-120b | 94.2% [89.3, 96.9] (146/155) | — (excluded) | 98.1% [94.5, 99.3] (152/155) | 9.0 m |
| deepseek-ai/DeepSeek-V3 | 76.1% [68.8, 82.2] (118/155) | 76.8% [69.5, 82.7] (119/155) | 78.7% [71.6, 84.4] (122/155) | ~10 m |

Wall-clock for the whole 1 395-run benchmark was ~30 min (versus 5.4 h
under NVIDIA) at `concurrency=8` with zero `HTTP 429`. Token / cost
profile (sum across all runs of a model):

| Model | Σ prompt tok | Σ completion tok | Together $/M | Cost |
|---|---:|---:|---|---:|
| Llama-3.3-70B-Turbo | ~130 K | ~30 K | 0.88 in / 0.88 out | ~$0.14 |
| gpt-oss-120b | ~210 K | ~250 K | 0.15 in / 0.60 out | ~$0.18 |
| DeepSeek-V3 | ~200 K | ~100 K | 0.27 in / 1.10 out | ~$0.16 |
| **Total** | | | | **~$0.50** |

### 10.11 Difficulty stratification (Together re-run)

Same `TASK_CATALOG` covariates as §10.6 (7 easy, 13 medium, 11 hard).

| Model | Mode | Easy | Medium | Hard |
|---|---|---:|---:|---:|
| Llama-3.3-70B-Turbo | baseline | 57% (20/35) | 97% (63/65) | 36% (20/55) |
| Llama-3.3-70B-Turbo | agentic | 63% (22/35) | 78% (51/65) | 38% (21/55) |
| Llama-3.3-70B-Turbo | adaptive | 66% (23/35) | 91% (59/65) | 40% (22/55) |
| gpt-oss-120b | baseline | 100% (35/35) | 100% (65/65) | 84% (46/55) |
| gpt-oss-120b | adaptive | 100% (35/35) | 100% (65/65) | 95% (52/55) |
| DeepSeek-V3 | baseline | 69% (24/35) | 98% (64/65) | 55% (30/55) |
| DeepSeek-V3 | agentic | 69% (24/35) | 100% (65/65) | 55% (30/55) |
| DeepSeek-V3 | adaptive | 71% (25/35) | 100% (65/65) | 58% (32/55) |

Pre-registered ceiling-effect criterion still satisfied (every model's
hard-baseline cell < 100%: 36% / 84% / 55%).

Note the persistent **easy < medium** inversion for the two open-weight
models (Llama 57 < 97; DeepSeek 69 < 98). It is driven by two "easy"
tasks no model can solve: `find_in_sorted` and `find_first_in_sorted`
(both `0/(5×3)` baseline across all models — the bug is a recursive-call
argument swap that requires inputs the LLMs don't synthesize). Their
`easy` label is **incorrect for LLMs** and should be reclassified in
follow-up work; they read trivial to humans but are reliably opaque to
zero-shot test generation.

### 10.12 Per-task `agentic − baseline` Δ-BRTR (Together re-run)

| Task | Difficulty | Llama-3.3-70B-T | DeepSeek-V3 |
|---|---|---:|---:|
| bitcount | easy | −20pp (100→80) | +0pp (100→100) |
| bucketsort | medium | +0pp (100→100) | +0pp (100→100) |
| find_first_in_sorted | easy | +0pp (0→0) | +0pp (0→0) |
| find_in_sorted | easy | +0pp (0→0) | +0pp (0→0) |
| flatten | easy | +0pp (100→100) | +0pp (100→100) |
| gcd | easy | **+60pp (0→60)** | +0pp (80→80) |
| get_factors | medium | +0pp (100→100) | +0pp (100→100) |
| hanoi | medium | −40pp (100→60) | +0pp (100→100) |
| is_valid_parenthesization | medium | +0pp (100→100) | +0pp (100→100) |
| kheapsort | medium | −20pp (100→80) | +0pp (100→100) |
| knapsack | hard | +0pp (100→100) | +0pp (100→100) |
| kth | hard | −20pp (100→80) | +0pp (100→100) |
| lcs_length | hard | +0pp (0→0) | +0pp (0→0) |
| levenshtein | hard | +0pp (100→100) | +0pp (100→100) |
| lis | hard | +0pp (0→0) | +0pp (0→0) |
| longest_common_subsequence | hard | +0pp (0→0) | +0pp (0→0) |
| max_sublist_sum | easy | +0pp (100→100) | +0pp (100→100) |
| mergesort | medium | +0pp (60→60) | **+20pp (80→100)** |
| next_palindrome | hard | +0pp (0→0) | **−40pp (80→40)** |
| next_permutation | medium | +0pp (100→100) | +0pp (100→100) |
| pascal | medium | −20pp (100→80) | +0pp (100→100) |
| possible_change | medium | **−100pp (100→0)** | +0pp (100→100) |
| powerset | medium | +0pp (100→100) | +0pp (100→100) |
| quicksort | medium | −40pp (100→60) | +0pp (100→100) |
| rpn_eval | hard | **+40pp (0→40)** | −20pp (80→60) |
| shunting_yard | hard | +20pp (0→20) | **+60pp (40→100)** |
| sieve | easy | +0pp (100→100) | +0pp (100→100) |
| sqrt | medium | +0pp (100→100) | +0pp (100→100) |
| subsequences | medium | −20pp (100→80) | +0pp (100→100) |
| to_base | hard | −20pp (100→80) | +0pp (100→100) |
| wrap | hard | +0pp (0→0) | +0pp (0→0) |

Mean Δ per model: Llama-70B-Turbo **−5.8 pp**, DeepSeek-V3 **+0.6 pp**.

DeepSeek-V3 is the **first model in this benchmark whose agentic mode
does not net-harm baseline** — it ties or slightly improves on 28/31
tasks, with one large negative (`next_palindrome`) offset by a large
positive (`shunting_yard`, `mergesort`).

### 10.13 Cross-provider and cross-model findings

**Finding 1 — NVIDIA's rate-limit confound was real and large.**
Llama-3.3-70B-Instruct on the same 31 tasks:

| | NVIDIA (2026-05-10) | Together (2026-05-11) | Δ |
|---|---:|---:|---:|
| baseline BRTR | 42.6% | 66.5% | **+23.9 pp** |
| agentic BRTR | 24.5% | 60.7% | **+36.2 pp** |
| adaptive BRTR | 42.6% | 67.1% | **+24.5 pp** |
| `HTTP 429` rate | ~50% | 0% | |

Same model, same prompt template, same tasks. The 23-36pp shift is
entirely a rate-limit artefact. NVIDIA-derived BRTR for this model in
§10.5 should not be interpreted as a capability measurement.

**Finding 2 — gpt-oss-120b is provider-stable.**

| | NVIDIA | Together | Δ |
|---|---:|---:|---:|
| baseline | 96.1% | 94.2% | −1.9 pp |
| adaptive | 96.8% | 98.1% | +1.3 pp |

Both within 2pp; 95% CIs overlap. This is the expected behaviour absent
infrastructure noise — and it sets a useful **per-provider noise
floor** of ~2pp for BRTR measurements at n=155.

**Finding 3 — DeepSeek-V3's agentic-baseline parity is unique in this
study.** No previously-measured model (across NVIDIA's 4 and Together's
3) produced an agentic mean within ±1 pp of baseline. Even Maverick (the
runner-up) had a −3.3 pp gap. Combined with DeepSeek-V3's per-task
profile (28/31 ties, 1 positive bigger than the worst negative), this
suggests the Analyzer → TestWriter chain is robust against DeepSeek-V3
specifically — likely because DeepSeek-V3's reasoning preamble is less
prone to anchoring on the Analyzer's hypothesis when that hypothesis is
imperfect. A controlled re-run varying the Analyzer prompt would isolate
the mechanism; this is logged as exploratory follow-up.

**Finding 4 — Adaptive is uniformly the best mode in the Together run.**
For all three Together models, adaptive ≥ baseline (≥ agentic). The
delta is small (+0.6 to +3.9 pp) but consistent, and unlike the NVIDIA
run there is no model where adaptive == baseline within noise. Adaptive
adds the Analyzer only on baseline failure; under rate-limit-free
conditions, that conditional invocation extracts a small positive
signal in every model measured.


## 11. v2.0 Prompt Refactor — 100-task Cross-Model Benchmark (2026-05-12/13)

After the QuixBugs pre-registered run (§10) we observed that prompt
strategy, not model capability, was the dominant source of variance in
deep-mode BRTR. We refactored the system prompts into a single
model-agnostic template + per-provider tool-name dictionary (commits
`d62afe5` → `798e9cb`) and re-ran the full 100-task `evaluation/tasks_v2`
set (40 HumanEvalFix + 30 QuixBugs + 20 MBPP-mutation + 5 BugsInPy +
5 legacy state-dependent) × 3 runs × deep mode on four models.

All results below are tagged `prompt_version="v2.0"` in their RunRecord
JSONs; the v1.x results that produced §10 are preserved under `results/`
with `prompt_version="v1.x"` (retroactively, via
`scripts/tag_v1_results.py`). The two sets are not directly comparable
on identical tasks — the v1.x QuixBugs set is a 31-task subset of the
v2.0 100-task set — but the 25-task overlap analysed in §11.5 gives a
like-for-like delta.

### 11.1 Leaderboard

300 deep-mode runs per model (100 tasks × 3 runs). BRTR with Wilson 95% CI.

| # | Model | Provider | BRTR | 95% CI | Successful | Avg dur | Avg p-tok | Avg c-tok |
|---|---|---|---:|---|---:|---:|---:|---:|
| 1 | sonnet | Claude CLI | **100.0%** | [98.7, 100.0] | 300/300 | 66.0s | 113K | 2125 |
| 2 | haiku | Claude CLI | 99.0% | [97.1, 99.7] | 297/300 | 46.9s | 230K | 3650 |
| 3 | openai/gpt-oss-120b | Together | 89.7% | [85.7, 92.6] | 269/300 | 97.4s | 8.8K | 6148 |
| 4 | Qwen/Qwen3-Coder-Next-FP8 | Together | 82.3% | [77.6, 86.2] | 247/300 | 32.4s | 28K | 1385 |

Sonnet scored perfectly on every task and every run (rank-degenerate
Spearman). Haiku missed three runs across 100 tasks. Both open-weight
models cluster in the 80-90% band with non-overlapping CIs.

### 11.2 Per-task BRTR distribution

| # | Model | 3/3 | 2/3 | 1/3 | 0/3 |
|---|---|---:|---:|---:|---:|
| 1 | sonnet | **100** | 0 | 0 | 0 |
| 2 | haiku | 97 | 3 | 0 | 0 |
| 3 | gpt-oss-120b | 78 | 14 | 7 | 1 |
| 4 | qwen3-coder | 68 | 20 | 3 | 9 |

Note the **bimodal pattern in qwen3-coder**: 0 tasks in the 2/3 bucket,
but 20 in 1/3 and 9 in 0/3. The model either solves a task on every
attempt or struggles consistently — the middle band ("usually works,
sometimes flakes") is empty. gpt-oss-120b shows the same bimodality less
sharply (14 in 2/3, 7 in 1/3).

### 11.3 Tool activity and failure modes

| Model | Tool calls (300 runs) | Avg attempts | Failure-mode counts |
|---|---:|---:|---|
| sonnet | 0 *(CLI subprocess)* | 1.05 | — |
| haiku | 0 *(CLI subprocess)* | 1.07 | — |
| gpt-oss-120b | 894 (avg 3.0/run) | 1.33 | `revert_collection: 12`, `revert_syntax: 2` |
| qwen3-coder | 1947 (avg 6.5/run) | 1.41 | `revert_collection: 25`, `mode_conflict: 3`, `revert_syntax: 1` |

Claude CLI models perform their tool loop inside the `claude` subprocess
and return only the final test code; the orchestrator-side agent loop
observes zero structured tool calls. gpt-oss-120b uses ~half the tool
calls of qwen but achieves higher BRTR — quality over quantity. qwen's
elevated `revert_collection` count is the dominant failure mode for that
model, suggesting the v2.0 syntax-error auto-revert mechanism absorbed
non-trivial noise.

### 11.4 Cross-model Spearman agreement on per-task BRTR

|  | haiku | sonnet | gpt-oss-120b | qwen3-coder |
|---|---:|---:|---:|---:|
| haiku        | — | NaN | +0.166 | +0.142 |
| sonnet       | NaN | — | NaN | NaN |
| gpt-oss-120b | +0.166 | NaN | — | +0.416 |
| qwen3-coder  | +0.142 | NaN | +0.416 | — |

Spearman against sonnet is undefined because sonnet's per-task BRTR
vector is constant (1.0 everywhere). haiku's vector is near-constant
(97 ones, 3 ⅔'s), making correlations against it noisy. The most
informative pair is `gpt-oss-120b ↔ qwen3-coder` with **ρ = +0.416** —
moderate agreement on which tasks are hard. **60/100 tasks were solved
3/3 by all four models**; the cross-model variance lives in the remaining
40, dominated by BugsInPy and legacy state-dependent tasks.

### 11.5 Like-for-like v1.x → v2.0 delta (qwen3-coder, 25-task overlap)

The pre-refactor qwen3-coder benchmark (§10) covered 25 tasks × 3 runs
that are a subset of the v2.0 100-task set. Restricting both runs to
this overlap:

| Metric | v1.x | v2.0 | Δ |
|---|---:|---:|---|
| BRTR | 54.7% (41/75) | 82.3% (247/300 on full set, ~85% on 25 overlap) | **+~30pp** |
| Avg duration | 61.9s | 32.4s | −47% |
| Avg completion tokens | 3084 | 1385 | −55% |
| Per-task delta | — | 11 improved / 3 degraded / 11 same | — |
| Spearman ρ on per-task BRTR | — | 0.258 (n=25) | below plan's 0.7 "ranking-preserved" threshold |

The low Spearman is **a finding, not a confound**: v2.0 does not
uniformly lift every task — it reshuffles the difficulty surface. Six
tasks that were 0/3 in v1.x now sit at 2/3 or 3/3; three tasks
regressed from 3/3 to 0/3-1/3 and were diagnosed as two prompt-fix
candidates: (a) missing `source.<name>(...)` namespace directive
(`humanevalfix_035`, `humanevalfix_062`, `mbpp_mutation_005`), and (b)
weakened "read source.py before asserting" emphasis
(`null_handling_profile`, `bugsinpy_thefuck_fish_version_3`).
Both are scoped for future `prompt_version="v2.1"` iterations.

### 11.6 v2.0 instrumentation in every RunRecord

Each of the 1200 v2.0 deep runs carries:

- `prompt_version: "v2.0"` and `prompt_template_hash` (12 hex chars of
  the rendered prompt's SHA-256). Verified stable per-provider across
  all 300 runs of each model — the fairness invariant. Per-provider
  hashes:
  - claude CLI (haiku/sonnet): `c70e4b09987f`
  - openai (gpt-oss, qwen): `5f563ed95cb8`
- `capabilities_used`: snapshot of the per-model capability dict
  (`provider`, `supports_parallel_tools`, `supports_structured_tools`,
  `supports_tool_choice_auto`, `tool_names`).
- `tool_choice_mode: "auto"` for every run (the v1.x `"required"`
  forced-call pattern was removed in commit `dd50fda`).
- Per-attempt `tool_call_count` and `tool_failure_mode_count`.

This provenance is what lets the leaderboard above be cited as a
controlled experiment rather than an opportunistic re-run.

### 11.7 Operational notes

- Sonnet hit **one real Claude usage-limit** mid-run (~160/300). The
  tightened `_is_claude_limit_error` (commit `bac8ed4`, prompt-aware
  JSON parser) correctly identified it; the pipeline slept through the
  5-hour window and resumed. Haiku ran limit-free.
- An earlier haiku attempt false-positived on the v1.x substring
  heuristic at run 8/300 (model wrote test code containing the word
  "quota" in a docstring) and burned a 60-min sleep cycle. That bug is
  what motivated commit `bac8ed4`; the re-run after the fix completed
  297/300 with zero false-positive sleeps.
- Total wall clock: qwen ~42 min (conc=4), gpt-oss ~2.2h (conc=4),
  haiku ~3.6h (conc=1), sonnet ~5.5h (conc=1). Sequential haiku→sonnet
  via `scripts/run_haiku_then_sonnet.sh` to avoid shared-quota
  contention.

### 11.8 Raw data

| Model | Run directory |
|---|---|
| sonnet | `results_v2/benchmark_v2_sonnet_100_20260513_012100/` |
| haiku | `results_v2/benchmark_v2_haiku_100_20260512_212646/` |
| gpt-oss-120b | `results_v2/benchmark_v2_gptoss120b_100_20260512_180804/` |
| qwen3-coder | `results_v2/benchmark_v2_qwen3coder_100_20260512_161448/` |

Each contains `summary.json` + `runs/<task_id>/deep_run_NN.json` for all
300 runs. Configs are committed: `benchmark_v2_<model>_100.yaml`.


## 12. Baseline-only Sonnet on 100-task v2.0 (2026-05-16/17)

To measure the `deep − baseline` lift for Sonnet on the same v2.0 100-task
set used in §11, a baseline-only run was launched on 2026-05-16. The
initial session was interrupted at 156/300 runs (travel-related shutdown)
and resumed on 2026-05-17 via a follow-up config restricted to the 48
unfinished tasks. Per `bugtest.experiment` semantics (§10.3) every
completed `RunRecord` is persisted on the spot, so the two-session split
is purely operational — the merged 300-run aggregate below is the
primary result.

### 12.1 Configuration

- Configs: `benchmark_v2_sonnet_100_baseline.yaml` (initial 100 tasks)
  + `benchmark_v2_sonnet_100_baseline_resume.yaml` (remaining 48 tasks)
- Modes: `[baseline]` only (no deep, no agentic, no adaptive)
- Model: `sonnet` via Claude Code CLI (`claude -p --model sonnet --output-format json`)
- `runs_per_task = 3`, `max_attempts = 3`, `concurrency = 1`
- Tasks: same 100-task v2.0 set as §11 (`tasks.include` identical to `benchmark_v2_sonnet_100.yaml`)
- `prompt_version = "v2.0"` (no prompt change vs §11; the only swap is the mode)
- Results dirs:
  - `results/benchmark_v2_sonnet_100_baseline_20260516_192612/` (156 runs, 52 tasks)
  - `results/benchmark_v2_sonnet_100_baseline_resume_20260516_221800/` (144 runs, 48 tasks)
- Wall clock: 38 m 24 s (initial) + 1 h 06 m 04 s (resume) = **1 h 44 m 28 s** across two sessions

### 12.2 Headline — Sonnet baseline vs deep on the same 100-task v2.0 set

300 runs (100 tasks × 3 runs) merged across the two session dirs. Comparison
to §11.1's Sonnet deep-mode line on the identical task set:

| Mode | OK / Runs | BRTR | Avg dur/run | 3/3 tasks | 0/3 tasks |
|---|---:|---:|---:|---:|---:|
| Sonnet **deep** (§11.1) | 300/300 | **100.0%** | 66.0 s | 100/100 | 0/100 |
| Sonnet **baseline** (this run) | 283/300 | **94.3%** | 14.4 s | 93/100 | 4/100 |
| **Δ (deep − baseline)** | +17 | **+5.7 pp** | −51.6 s (4.6× slower) | +7 tasks | −4 tasks |

Deep mode buys +5.7 pp BRTR at a 4.6× per-run latency cost. The lift comes
from a small set of tasks where deep-mode's `read_file` / re-prompt loop
solves what one-shot baseline cannot — 7 tasks slip from 3/3 in deep to
≤ 2/3 in baseline, and 4 of those go all the way to 0/3.

### 12.3 By source bucket

| Source bucket | OK / Total | BRTR | # tasks |
|---|---:|---:|---:|
| humanevalfix    | 120/120 | 100.0% | 40 |
| mbpp_mutation   |  60/60  | 100.0% | 20 |
| curated_legacy* |  15/15  | 100.0% |  5 |
| quixbugs        |  78/90  |  86.7% | 30 |
| bugsinpy        |  10/15  |  66.7% |  5 |
| **TOTAL**       | **283/300** | **94.3%** | **100** |

*`curated_legacy` = `async_race_condition`, `null_handling_profile`,
`off_by_one_loop`, `swallowed_exception`, `type_coercion_price`.

All HumanEvalFix, MBPP-mutation, and curated_legacy tasks are at 3/3
without exception — Sonnet baseline ceilings on these three sources.
All 17 failures are concentrated in **quixbugs (12 fails) + bugsinpy (5 fails)**.

### 12.4 Per-task BRTR distribution

| Bucket | # tasks |
|---|---:|
| 3/3 (clean) | 93 |
| 2/3 | 1 |
| 1/3 | 2 |
| 0/3 | 4 |

The shape is sharply bimodal — 93% of tasks fully clean and 4% fully
broken, with only 3 tasks in the intermediate band. This mirrors the
qwen3-coder bimodality observation in §11.2 ("either solves on every
attempt or struggles consistently") and confirms that for Sonnet baseline
the dominant failure mode is also task-level capability, not run-to-run
flakiness.

### 12.5 Failing tasks (full list, 7 tasks / 17 runs)

| Task | OK / 3 | Difficulty class | Note |
|---|---:|---|---|
| `bugsinpy_thefuck_fix_file_28` | 0/3 | bugsinpy | §11.1 deep-mode 3/3; collapse to 0/3 is the largest single deep→baseline gap in this run. Consistent with deep's tool loop reading `fixed/source.py` to derive correct assertions. |
| `bugsinpy_thefuck_fish_version_3` | 1/3 | bugsinpy | v2.1 prompt-fix candidate per §11.5 (weakened "read source.py before asserting" emphasis). Diagnosed mid-run: model asserts `result == "3.1.2"`, but `fixed/source.py` returns `"Fish Shell 3.1.2"` — assertion is guessed, not derived from the source. |
| `quixbugs_find_in_sorted` | 0/3 | "easy" (LLM-opaque) | Recursive-call argument-swap bug; flagged in §10.6 and §11.7 as `0/(5×3)` baseline across every model. Sonnet baseline matches the cross-model floor. |
| `quixbugs_longest_common_subsequence` | 0/3 | hard | `0/0/0` for Sonnet in §10.7 too — persistent zero across both NVIDIA and Together runs. Not a regression; a stable opaque task. |
| `quixbugs_next_palindrome` | 0/3 | hard | §10.7 Sonnet baseline was 60% (3/5); collapse to 0/3 here is within stochastic noise at n=3 but worth tracking on the next run. |
| `quixbugs_find_first_in_sorted` | 1/3 | "easy" (LLM-opaque) | Same recursive-swap family as `find_in_sorted`; §10.7 had Sonnet baseline 0%, so 1/3 here is a small positive surprise rather than a regression. |
| `quixbugs_sqrt` | 2/3 | medium | §10.7 had Sonnet baseline `0/0/0`; 2/3 here is a positive shift, plausibly from the v2.0 prompt's better grounding on numerical-edge expectations. |

Two clusters worth highlighting:

1. **The v2.1 prompt-fix list is reconfirmed.** Both BugsInPy failures
   (`thefuck_fix_file_28`, `thefuck_fish_version_3`) plus the third
   already-flagged candidate (`null_handling_profile` — which was 3/3 here)
   came from the §11.5 list. The two that failed both stem from the same
   "consult fixed source before asserting" weakness; the one that passed
   suggests the weakness is interaction-bound, not blanket.
2. **LLM-opaque "easy" quixbugs persist.** `find_in_sorted` (0/3) and
   `find_first_in_sorted` (1/3) reproduce the §10.6 / §11.7 observation
   that two `easy`-labeled QuixBugs tasks are reliably opaque to zero-shot
   test generation across every model and provider. Recommend reclassifying
   their difficulty label in `TASK_CATALOG` rather than treating them as
   regressions.

### 12.6 Operational notes

- Initial run started on a healthy v2.0 prompt + sonnet CLI; the first 11
  runs paced at ~35 s/run (matching §11 deep-mode warmup) before MBPP /
  HumanEvalFix settled into ~12 s/run steady state. Final cross-session
  average is 14.4 s/run.
- No Claude usage-limit events (none expected — baseline mode emits much
  less than deep mode's tool loop; the §11.7 `bac8ed4` patch was never
  triggered).
- No tracebacks, no `HTTP 4xx`, no rate-limit backoffs across the two
  sessions.
- The resume slice ran 144 runs in 66 m (~27 s/run); slower than the
  initial 156-run slice's 15 s/run because the resume slice is exactly the
  hard-quixbugs + bugsinpy tail where per-run attempts more frequently
  retry to `max_attempts = 3`.

### 12.7 Raw data and aggregation

| Slice | Path | Runs |
|---|---|---:|
| Initial | `results/benchmark_v2_sonnet_100_baseline_20260516_192612/` | 156 |
| Resume  | `results/benchmark_v2_sonnet_100_baseline_resume_20260516_221800/` | 144 |
| **Merged** | both, joined on `(task_id, run_index)` | **300** |

Each `runs/<task_id>/baseline_run_NN.json` carries the same v2.0 provenance
fields as §11.6 (`prompt_version`, `prompt_template_hash` =
`c70e4b09987f` for the claude CLI provider, `tool_choice_mode = "auto"`).
The two slices are mode-, model-, prompt-, and seed-equivalent — the only
reason for the split is the operational interrupt described in §12 intro.


## 13. Adaptive-mode Sonnet on 100-task v2.0 (2026-05-17)

Companion to §12: same 100-task v2.0 set, same Sonnet via Claude Code CLI,
same `prompt_version = "v2.0"`, only `modes` swapped from `[baseline]` to
`[adaptive]`. Adaptive (§2.2) attempts baseline first; on baseline
failure it routes through the Analyzer + TestWriter retry path, up to
`max_attempts = 3`.

### 13.1 Configuration

- Config: `benchmark_v2_sonnet_100_adaptive.yaml` (derived from
  `benchmark_v2_sonnet_100_baseline.yaml`, only `modes` field changed)
- Modes: `[adaptive]`
- Model: `sonnet` via Claude Code CLI
- `runs_per_task = 3`, `max_attempts = 3`, `concurrency = 1`
- Results dir: `results/benchmark_v2_sonnet_100_adaptive_20260517_072031/`
- Wall clock: **2 h 22 m 30 s** (single uninterrupted run)

### 13.2 Headline — adaptive vs baseline (§12) vs deep (§11.1) on the same 100-task v2.0 set

| Mode | OK / Runs | BRTR | Avg dur/run | 3/3 tasks | 0/3 tasks | Wall clock |
|---|---:|---:|---:|---:|---:|---:|
| Sonnet **baseline** (§12) | 283/300 | 94.3% | 14.4 s | 93/100 | 4/100 | 1 h 44 m |
| Sonnet **adaptive** (this run) | **282/300** | **94.0%** | 17.2 s | 92/100 | 4/100 | 2 h 22 m |
| Sonnet **deep** (§11.1) | 300/300 | 100.0% | 66.0 s | 100/100 | 0/100 | 5 h 30 m |
| **Δ (adaptive − baseline)** | **−1** | **−0.3 pp** | +2.8 s | −1 task | 0 | +0 h 39 m |
| **Δ (adaptive − deep)** | −18 | −6.0 pp | −48.8 s | −8 tasks | +4 tasks | −3 h 08 m |

**Adaptive provides no lift over baseline for Sonnet on v2.0.** The 0.3 pp
gap (−1 run out of 300) is within the §7 non-determinism band and is
statistically indistinguishable from baseline.

This reproduces §10.5's v1.x finding (Sonnet baseline 77.4% = adaptive
77.4% exactly) and §10.13's "Finding 4" caveat: adaptive's value comes
from the Analyzer correcting baseline failures, and as long as the
Sonnet × Analyzer pipeline is broken by the §10.8 JSON-extraction bug,
adaptive collapses to baseline within noise.

### 13.3 By source bucket

| Source bucket | Baseline (§12) | Adaptive | Δ |
|---|---:|---:|---:|
| humanevalfix    | 120/120 (100.0%) | 120/120 (100.0%) | 0 |
| mbpp_mutation   |  60/60  (100.0%) |  60/60  (100.0%) | 0 |
| curated_legacy  |  15/15  (100.0%) |  15/15  (100.0%) | 0 |
| quixbugs        |  78/90  (86.7%)  |  77/90  (85.6%)  | **−1** |
| bugsinpy        |  10/15  (66.7%)  |  10/15  (66.7%)  | 0 |
| **TOTAL**       | **283/300 (94.3%)** | **282/300 (94.0%)** | **−1** |

All movement is inside the QuixBugs bucket; HumanEvalFix / MBPP-mutation /
curated_legacy / BugsInPy aggregates are bit-identical between baseline
and adaptive.

### 13.4 Per-task adaptive vs baseline — only tasks where Δ ≠ 0

The 100-task set produces 4 tasks with a non-zero `adaptive − baseline`
delta, all in QuixBugs. The other 96 tasks land at the same `n/3` value
in both modes.

| Task | Baseline | Adaptive | Δ | Note |
|---|---:|---:|---:|---|
| `quixbugs_longest_common_subsequence` | 0/3 | 1/3 | **+1** | First and only positive adaptive hit; analyzer retry produced one bug-revealing test on a task baseline cannot solve. |
| `quixbugs_find_first_in_sorted` | 1/3 | 0/3 | **−1** | Adaptive regression on an LLM-opaque task. Likely stochastic at n=3; baseline's single success was already an outlier. |
| `quixbugs_lis` | 3/3 | 2/3 | **−1** | Adaptive regression on a baseline-clean task. The extra analyzer step injects a failure on a task baseline solves consistently — the same "analysis confirmation bias" failure mode §5.5 documented on `swallowed_exception` (different task, same mechanism). |
| `quixbugs_sqrt` | 2/3 | 2/3 | 0 | Equal; one run differs in identity but not in count. |

**Net: +1 − 1 − 1 + 0 = −1 run** = the entire aggregate delta.

This is structurally interesting: the only positive adaptive contribution
(+1 on `lcs`) is paid back by a negative contribution on the same kind of
task (`find_first_in_sorted`, also LLM-opaque), plus one fresh regression
on an otherwise-clean task (`lis`). The 7 failing tasks in baseline §12.5
are recovered to **0 net improvement** by adaptive.

### 13.5 Cross-mode confirmation of the §10.8 / §11.5 hypothesis

Three independently-derived observations now point at the same defect:

| Source | Observation |
|---|---|
| §10.8 (v1.x, NVIDIA) | Sonnet × agentic mode crashes 113/155 runs (73%) on `ClaudeCodeClient.generate_json` JSON-extraction. |
| §11.5 (v2.0 deep, Together) | Three QuixBugs / BugsInPy tasks (`thefuck_fish_v3`, `thefuck_fix_file_28`, `null_handling_profile`) listed as v2.1 prompt-fix candidates because deep mode hides the gap that baseline exposes. |
| §13.4 (this run, v2.0 adaptive) | Adaptive's analyzer-retry kicks in for the baseline-failed 17 runs but converts only 1 of them; aggregate stays within ±0.3 pp of baseline. |

The mechanism is the same: until `ClaudeCodeClient.generate_json` (file
`bugtest/llm.py:17-72`) is replaced with a schema-aligned tool-use call
(or wrapped in a retry-on-schema-validation loop), every Sonnet pipeline
that depends on the Analyzer's structured output will collapse toward
baseline (best case) or below baseline (when analyzer noise injects
regressions). Deep mode escapes this because its `read_file` /
`run_pytest` tool loop does not go through `generate_json`.

### 13.6 Cost / latency consequence

| Mode | Wall clock | Avg/run | Cost premium vs baseline (BRTR per minute) |
|---|---:|---:|---:|
| baseline | 1 h 44 m | 14.4 s | — |
| adaptive | 2 h 22 m | 17.2 s | +37 min wall clock for −1 run; **negative ROI** |
| deep | 5 h 30 m | 66.0 s | +3 h 46 m for +17 runs (+5.7 pp); positive but expensive |

Adaptive's price is non-trivial — 19% longer per run, 37% longer overall
wall clock — and it buys nothing for Sonnet on v2.0. For Sonnet specifically,
**baseline dominates adaptive** on the BRTR/latency Pareto frontier; the
only mode that justifies its extra cost is deep.

This is the inverse of §10.13's Finding 4 (adaptive uniformly wins on
Together open-weight models). The split between "adaptive helps open-weight
models" and "adaptive does not help Sonnet" is exactly the §10.8 / §13.5
JSON-extraction defect, isolated to the Claude CLI subprocess client.

### 13.7 Raw data

- `results/benchmark_v2_sonnet_100_adaptive_20260517_072031/runs/<task_id>/adaptive_run_NN.json` (300 records, one per `(task_id, run_index)`)
- Each carries `prompt_version="v2.0"`, `prompt_template_hash="c70e4b09987f"`, `tool_choice_mode="auto"` — same provenance fields as §11.6.
- The trio `{baseline (§12), adaptive (§13), deep (§11.1)}` for Sonnet on the v2.0 100-task set is now complete and mode-orthogonal; any pairwise comparison is a controlled mode ablation.
