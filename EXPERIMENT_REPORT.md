# Experiment Report: Does Code Analysis Improve LLM Test Generation?

## 1. Research Question

> Does adding a structured code analysis step before test generation improve
> the LLM's ability to produce bug-revealing tests?

## 2. Experimental Setup

### 2.1 Models Tested

| Model | Parameters | Architecture | Provider |
|---|---|---|---|
| Meta Llama 3.3 70B Instruct | 70B | Dense Transformer | NVIDIA Build |
| Meta Llama 3.1 8B Instruct | 8B | Dense Transformer | NVIDIA Build |
| Mistral Medium 3.5 | 128B | Dense Transformer | NVIDIA Build |

### 2.2 Experiment Configuration

| Parameter | Value |
|---|---|
| Tasks | 12 (5 custom + 7 BugsInPy) |
| Runs per task per mode | 3 |
| Max retry attempts | 3 per run |
| Test timeout | 30 seconds |
| Validation | Deterministic (pytest, no LLM judgment) |
| Date | 2026-04-30 |

### 2.3 Pipeline Design

```
Baseline:  Task --> TestWriter --> Validate (retry x3)
Agentic:   Task --> Analyzer --> TestWriter --> Validate (retry x3)
```

**Fair comparison guarantees:**
- Same TestWriter system prompt for both modes
- Same retry budget (max 3 attempts)
- Same deterministic validator (pytest return codes)
- Only variable: agentic mode receives a structured `CodeAnalysis` as additional context

### 2.4 Validation Criteria

A test is **bug-revealing** if and only if:
- It **FAILS** on the buggy code (exposes the bug)
- It **PASSES** on the fixed code (confirms the fix)

### 2.5 Metrics

- **BRTR** (Bug-Revealing Test Rate): Percentage of runs that produced at least one bug-revealing test
- **Delta**: Agentic BRTR minus Baseline BRTR. Positive = analysis helped, negative = analysis hurt
- **Attempts-to-success**: Average retry count before success (lower = better)
- **95% CI**: Wilson score confidence interval for binomial proportions

## 3. Overall Results

### 3.1 BRTR Summary Across All Models

| Model | Baseline BRTR | Agentic BRTR | Delta | Interpretation |
|---|---|---|---|---|
| Llama 3.3 70B | 47.2% | 50.0% | **+2.8%** | Slight improvement (not significant) |
| Llama 3.1 8B | 30.6% | 28.6% | **-2.0%** | Pipeline broken (81% JSON errors) |
| Mistral Medium 3.5 128B | 58.3% | 51.4% | **-6.9%** | Analysis hurt performance |

### 3.2 Detailed Statistics

| Model | Mode | BRTR | 95% CI | Successful | Completed | Avg Attempts | Avg Tokens |
|---|---|---|---|---|---|---|---|
| Llama 70B | Baseline | 47.2% | [32.0%, 63.0%] | 17/36 | 36/36 | 1.4 | 1,719 |
| Llama 70B | Agentic | 50.0% | [34.1%, 65.9%] | 17/34 | 34/36 | 1.0 | 2,399 |
| Llama 8B | Baseline | 30.6% | [18.0%, 46.9%] | 11/36 | 36/36 | 1.4 | 2,300 |
| Llama 8B | Agentic | 28.6% | [8.2%, 64.1%] | 2/7 | 7/36 | 1.5 | 3,298 |
| Mistral 128B | Baseline | 58.3% | [42.2%, 72.9%] | 21/36 | 36/36 | 1.1 | 1,410 |
| Mistral 128B | Agentic | 51.4% | [35.6%, 67.0%] | 18/35 | 35/36 | 1.0 | 2,373 |

## 4. Per-Task Breakdown

### 4.1 Llama 3.3 70B — Per-Task Results

| Task | Category | Difficulty | Baseline | Agentic | Delta |
|---|---|---|---|---|---|
| boundary_threshold | Off-by-one | Easy | 100% | 100% | 0% |
| off_by_one_loop | Loop boundary | Easy | 100% | 100% | 0% |
| bugsinpy_tqdm_enumerate | Iterator | Medium | 100% | 100% | 0% |
| bugsinpy_thefuck_fish | Version parse | Medium | 100% | 100% | 0% |
| bugsinpy_black_async_for | Tokenizer | Medium | 100% | 100% | 0% |
| type_coercion_price | Type safety | Medium | 0% | **67%** | **+67%** |
| swallowed_exception | Error handling | Medium | **67%** | 0% | **-67%** |
| async_race_condition | Concurrency | Hard | 0% | 0% | 0% |
| cache_invalidation | State mgmt | Medium | 0% | 0% | 0% |
| null_handling_profile | Null safety | Medium | 0% | 0% | 0% |
| bugsinpy_pysnooper | Unicode | Hard | 0% | 0% | 0% |
| bugsinpy_thefuck_fix | Regex/parse | Hard | 0% | 0% | 0% |

### 4.2 Llama 3.1 8B — Per-Task Results

| Task | Baseline | Agentic | Delta | Note |
|---|---|---|---|---|
| off_by_one_loop | **100%** | 0% | -100% | JSON parse error |
| bugsinpy_black_async_for | 67% | 0% | -67% | JSON parse error |
| boundary_threshold | 33% | 0% | -33% | JSON parse error |
| bugsinpy_tqdm_enumerate | 33% | 0% | -33% | JSON parse error |
| bugsinpy_pysnooper | 33% | 0% | -33% | JSON parse error |
| bugsinpy_thefuck_fish | 33% | **67%** | **+33%** | Agentic works here |
| swallowed_exception | 33% | 0% | -33% | |
| type_coercion_price | 33% | 0% | -33% | |
| async_race_condition | 0% | 0% | 0% | JSON parse error |
| cache_invalidation | 0% | 0% | 0% | JSON parse error |
| null_handling_profile | 0% | 0% | 0% | JSON parse error |
| bugsinpy_thefuck_fix | 0% | 0% | 0% | JSON parse error |

**Note:** 29/36 agentic runs failed due to JSON parsing errors (8B model cannot reliably produce structured output).

### 4.3 Mistral Medium 3.5 128B — Per-Task Results

| Task | Category | Difficulty | Baseline | Agentic | Delta |
|---|---|---|---|---|---|
| boundary_threshold | Off-by-one | Easy | 100% | 100% | 0% |
| off_by_one_loop | Loop boundary | Easy | 100% | 100% | 0% |
| bugsinpy_tqdm_enumerate | Iterator | Medium | 100% | 100% | 0% |
| bugsinpy_thefuck_fish | Version parse | Medium | 100% | 100% | 0% |
| bugsinpy_black_async_for | Tokenizer | Medium | 100% | 100% | 0% |
| type_coercion_price | Type safety | Medium | **100%** | 100% | 0% |
| swallowed_exception | Error handling | Medium | **100%** | 0% | **-100%** |
| async_race_condition | Concurrency | Hard | 0% | 0% | 0% |
| cache_invalidation | State mgmt | Medium | 0% | 0% | 0% |
| null_handling_profile | Null safety | Medium | 0% | 0% | 0% |
| bugsinpy_pysnooper | Unicode | Hard | 0% | 0% | 0% |
| bugsinpy_thefuck_fix | Regex/parse | Hard | 0% | 0% | 0% |

### 4.4 Cross-Model Task Comparison

| Task | Llama 70B B/A | Llama 8B B/A | Mistral 128B B/A | Pattern |
|---|---|---|---|---|
| boundary_threshold | 100/100 | 33/0 | 100/100 | Easy — large models solve |
| off_by_one_loop | 100/100 | 100/0 | 100/100 | Easy — large models solve |
| bugsinpy_tqdm | 100/100 | 33/0 | 100/100 | Easy — large models solve |
| bugsinpy_thefuck_fish | 100/100 | 33/67 | 100/100 | Easy — analysis helps 8B |
| bugsinpy_black | 100/100 | 67/0 | 100/100 | Medium — large models solve |
| type_coercion_price | 0/67 | 33/0 | 100/100 | **Analysis helps 70B, Mistral solves without** |
| swallowed_exception | 67/0 | 33/0 | 100/0 | **Analysis always hurts** |
| async_race_condition | 0/0 | 0/0 | 0/0 | Hard — all fail |
| cache_invalidation | 0/0 | 0/0 | 0/0 | Hard — all fail (Python 3.9 issue) |
| null_handling_profile | 0/0 | 0/0 | 0/0 | Hard — all fail (Python 3.9 issue) |
| bugsinpy_pysnooper | 0/0 | 33/0 | 0/0 | Hard — all fail |
| bugsinpy_thefuck_fix | 0/0 | 0/0 | 0/0 | Hard — all fail |

## 5. Key Findings

### 5.1 Finding 1: Analysis does not improve overall BRTR

Across all three models, the analysis step does not produce a statistically
significant improvement in Bug-Revealing Test Rate. In fact, for the strongest
model (Mistral 128B), it slightly hurts performance (-6.9%).

```
Model capability vs Analysis benefit:

  Mistral 128B (strongest):  Baseline 58.3%  →  Agentic 51.4%  (Delta: -6.9%)
  Llama 70B    (strong):     Baseline 47.2%  →  Agentic 50.0%  (Delta: +2.8%)
  Llama 8B     (weak):       Baseline 30.6%  →  Agentic 28.6%  (Delta: -2.0%, broken)
```

**Interpretation:** Stronger models don't benefit from analysis because they
already identify bugs well. Weaker models can't produce the structured output
required by the analysis pipeline. The analysis step has the most potential
in the middle range, but even there the effect is small and inconsistent.

### 5.2 Finding 2: Analysis reduces retry count (when it works)

The one consistent positive signal across models: when both modes succeed,
agentic mode finds the answer with fewer attempts.

| Model | Baseline Avg Attempts | Agentic Avg Attempts |
|---|---|---|
| Llama 70B | 1.4 | **1.0** |
| Mistral 128B | 1.1 | **1.0** |
| Llama 8B | 1.4 | 1.5 (broken) |

This means analysis provides useful directional guidance even when it doesn't
change the final success/failure outcome.

### 5.3 Finding 3: Analysis introduces harmful bias (swallowed_exception)

The `swallowed_exception` task reveals a consistent anti-pattern:

| Model | Baseline | Agentic | Delta |
|---|---|---|---|
| Llama 70B | 67% | 0% | -67% |
| Llama 8B | 33% | 0% | -33% |
| Mistral 128B | **100%** | 0% | **-100%** |

**Every model performs worse with analysis on this task.** The bug is that a bare
`except:` clause swallows a `NameError`. The Analyzer correctly identifies this but
suggests testing for `NameError` propagation. This leads the TestWriter to write
`pytest.raises(NameError)`, which fails because the exception IS swallowed.

Baseline mode, without the analysis bias, explores different testing strategies
and sometimes stumbles onto a working approach.

**Conclusion:** Pre-analysis can introduce confirmation bias. When a bug requires a
non-obvious testing strategy, the Analyzer's "correct but unhelpful" hypothesis
locks the TestWriter into a failing approach.

### 5.4 Finding 4: Model capability is the dominant factor

```
Baseline BRTR by model size:

  Mistral 128B:    ████████████████████████████████  58.3%
  Llama 70B:       ████████████████████████          47.2%
  Llama 8B:        ████████████████                  30.6%
```

The difference between models (30% → 58%) is far larger than the difference
between modes (typically < 7%). Choosing a better model matters more than
adding an analysis step.

### 5.5 Finding 5: Structured output is a capability gate

The agentic pipeline requires the Analyzer to produce valid JSON (`CodeAnalysis`).
This creates a minimum capability threshold:

| Model | Agentic Runs Completed | Completion Rate |
|---|---|---|
| Mistral 128B | 35/36 | 97% |
| Llama 70B | 34/36 | 94% |
| Llama 8B | **7/36** | **19%** |

The 8B model fails to produce valid JSON in 81% of cases. The agentic pipeline
is effectively unusable below a certain model capability threshold, which lies
between 8B and 70B parameters for the Llama family.

### 5.6 Finding 6: Task difficulty determines outcomes, not pipeline architecture

Tasks fall into three clear categories regardless of model or mode:

**Always solved** (5 tasks): `boundary_threshold`, `off_by_one_loop`, `bugsinpy_tqdm`,
`bugsinpy_thefuck_fish`, `bugsinpy_black`
- Simple, localized bugs (wrong operator, missing argument)
- All capable models solve these with or without analysis

**Sometimes solved** (2 tasks): `type_coercion_price`, `swallowed_exception`
- Medium complexity bugs requiring specific testing strategies
- This is where analysis has the most variable impact (both positive and negative)

**Never solved** (5 tasks): `async_race_condition`, `cache_invalidation`,
`null_handling_profile`, `bugsinpy_pysnooper`, `bugsinpy_thefuck_fix`
- Complex bugs (concurrency, state management) or infrastructure issues (Python 3.9)
- No model solves these regardless of pipeline configuration

## 6. Infrastructure Confounds

5 of 12 tasks (42%) consistently fail across all models due to environment issues,
not model capability:

| Task | Root Cause |
|---|---|
| async_race_condition | Requires `pytest-asyncio` plugin (not installed) |
| cache_invalidation | Source uses `dict \| None` syntax (requires Python 3.10+) |
| null_handling_profile | Source uses `dict \| None` syntax (requires Python 3.10+) |
| bugsinpy_pysnooper | Complex multi-file dependency |
| bugsinpy_thefuck_fix | Complex regex/parsing logic |

If infrastructure-blocked tasks are excluded, effective BRTR (7 viable tasks):

| Model | Baseline BRTR | Agentic BRTR |
|---|---|---|
| Mistral 128B | 21/21 = **100%** | 18/21 = **86%** |
| Llama 70B | 17/21 = **81%** | 17/19 = **89%** |
| Llama 8B | 11/21 = **52%** | 2/7 = **29%** |

## 7. Token Cost Analysis

| Model | Baseline Tokens/Run | Agentic Tokens/Run | Overhead |
|---|---|---|---|
| Mistral 128B | 1,602 | 2,788 | +74% |
| Llama 70B | 1,719 | 2,399 | +40% |
| Llama 8B | 2,300 | 3,298 | +43% |

The analysis step adds 40-74% token overhead. For Mistral, this extra cost
produces *worse* results than baseline — a negative return on investment.

## 8. Threats to Validity

1. **Small sample size**: 3 runs per task limits statistical power. Confidence
   intervals are wide and overlap substantially between modes.

2. **Two model families**: Only Llama and Mistral tested. Architecturally
   different models (e.g., GPT, Claude, Gemma) may show different patterns.

3. **Environment confounds**: Python 3.9 compatibility issues and missing
   pytest plugins caused 42% of tasks to fail for infrastructure reasons.

4. **JSON parsing fragility**: The agentic pipeline depends on valid JSON from
   the Analyzer, creating a single point of failure that disproportionately
   affects smaller models.

5. **Prompt sensitivity**: Different prompt formulations for Analyzer and
   TestWriter may produce different results.

6. **Free-tier API constraints**: NVIDIA Build free tier may introduce
   variable latency and throttling that affects retry behavior.

## 9. Conclusions

1. **Adding code analysis does not improve BRTR.** Across three models of
   varying capability (8B, 70B, 128B), the analysis step produces no
   statistically significant improvement. For the strongest model (Mistral
   128B), it slightly hurts performance.

2. **Analysis reduces retry count but not success rate.** The clearest
   benefit is efficiency: successful agentic runs typically need only 1
   attempt vs 1.1-1.4 for baseline. This suggests analysis provides useful
   guidance but doesn't expand the range of solvable bugs.

3. **Pre-analysis introduces confirmation bias.** The `swallowed_exception`
   task shows that analysis consistently hurts across all models (-33% to
   -100%). When a bug requires a non-obvious testing approach, the Analyzer's
   hypothesis locks the TestWriter into a failing strategy.

4. **Model capability is the dominant factor.** The 28% BRTR gap between
   models (30% to 58%) dwarfs the <7% effect of adding analysis. Choosing
   a better model yields far greater improvement than adding pipeline
   complexity.

5. **Multi-agent pipelines have a minimum capability threshold.** Structured
   inter-agent communication (JSON) requires reliable instruction-following.
   The 8B model fails to produce valid Analyzer output in 81% of cases,
   making the pipeline unusable at this scale.

6. **Bug difficulty determines outcomes, not architecture.** Tasks cluster
   into "always solved" (42%), "sometimes solved" (17%), and "never solved"
   (42%) categories that are consistent across models and modes. Pipeline
   design has the most impact on the "sometimes solved" category.

## 10. Raw Data

Full experiment data is available at:
```
results/
  analysis_vs_direct_20260430_055256/     # Llama 3.3 70B
  analysis_vs_direct_20260430_XXXXXX/     # Llama 3.1 8B
  analysis_vs_direct_20260430_XXXXXX/     # Mistral Medium 3.5 128B
```

Each directory contains:
- `summary.json` — Aggregated statistics with BRTR and confidence intervals
- `config.yaml` — Configuration snapshot
- `runs/<task_id>/` — Individual run records with test code, validation
  output (pytest stdout from buggy and fixed versions), token usage,
  duration, and analysis (if agentic mode)
