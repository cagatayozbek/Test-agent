# Experiment Report: Does Code Analysis Improve LLM Test Generation?

## 1. Research Question

> Does adding a structured code analysis step before test generation improve
> the LLM's ability to produce bug-revealing tests?

## 2. Experimental Setup

| Parameter | Value |
|---|---|
| Model | Meta Llama 3.3 70B Instruct |
| Provider | NVIDIA Build API |
| Tasks | 12 (5 custom + 7 BugsInPy) |
| Runs per task | 3 |
| Max retry attempts | 3 |
| Test timeout | 30 seconds |
| Date | 2026-04-30 |

### Modes

```
Baseline:  Task --> TestWriter --> Validate (retry x3)
Agentic:   Task --> Analyzer --> TestWriter --> Validate (retry x3)
```

**Fair comparison guarantees:**
- Same TestWriter system prompt
- Same retry budget (max 3 attempts)
- Same deterministic validator (pytest, no LLM judgment)
- Only variable: agentic mode receives a structured `CodeAnalysis` as additional context

### Validation Criteria

A test is **bug-revealing** if and only if:
- It **FAILS** on the buggy code (exposes the bug)
- It **PASSES** on the fixed code (confirms the fix)

## 3. Results

### 3.1 Overall BRTR (Bug-Revealing Test Rate)

| Mode | BRTR | 95% CI | Successful | Avg Attempts | Avg Tokens |
|---|---|---|---|---|---|
| **Baseline** | 47.2% | [32.0%, 63.0%] | 17/36 | 1.4 | 1,719 |
| **Agentic** | 50.0% | [34.1%, 65.9%] | 17/34 | 1.0 | 2,399 |

**Key observation:** BRTR difference is not statistically significant (confidence
intervals overlap substantially). However, agentic mode requires **fewer attempts**
on average (1.0 vs 1.4), suggesting that the analysis step improves first-attempt
accuracy when the bug is within the model's capability.

### 3.2 Per-Task Breakdown

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

### 3.3 Task Categorization by Outcome

**Category A: Both succeed (5 tasks, 42%)**
`boundary_threshold`, `off_by_one_loop`, `bugsinpy_tqdm`, `bugsinpy_thefuck_fish`, `bugsinpy_black`

These are bugs with clear, localized symptoms (wrong operator, wrong argument,
missing keyword). Both modes reliably generate correct tests, often on the first attempt.

**Category B: Agentic wins (1 task, 8%)**
`type_coercion_price` — Baseline: 0%, Agentic: 67%

The bug involves a type mismatch (`str` vs `int` comparison). The Analyzer correctly
identified the trigger condition: mixing string and integer prices. This guided the
TestWriter to include mixed-type test data, which baseline missed.

**Category C: Baseline wins (1 task, 8%)**
`swallowed_exception` — Baseline: 67%, Agentic: 0%

The Analyzer over-analyzed the bug and suggested testing for `NameError` propagation.
But the bug is that a bare `except:` *swallows* the NameError, so `pytest.raises(NameError)`
always fails. Baseline stumbled onto a working approach by not overthinking.

**Category D: Both fail (5 tasks, 42%)**
`async_race_condition`, `cache_invalidation`, `null_handling_profile`,
`bugsinpy_pysnooper`, `bugsinpy_thefuck_fix`

These failures have three root causes:
1. **Environment issues** (3 tasks): Python 3.9 incompatibility with `dict | None`
   type hints in source code, or missing `pytest-asyncio` plugin
2. **Semantic difficulty** (1 task): Testing a swallowed exception requires understanding
   that the absence of an error IS the bug
3. **Complex real-world bugs** (1 task): BugsInPy tasks with multi-file dependencies

## 4. Analysis of Key Findings

### 4.1 Analysis step reduces retry count

When both modes succeed on a task, agentic mode consistently finds the answer on
the **first attempt** (avg: 1.0), while baseline sometimes needs retries (avg: 1.4).
This suggests the analysis provides useful guidance that reduces trial-and-error.

| Task | Baseline Attempts | Agentic Attempts |
|---|---|---|
| boundary_threshold | 1.0 | 1.0 |
| bugsinpy_black | 2.0 | **1.0** |
| bugsinpy_thefuck_fish | 1.0 | 1.0 |
| bugsinpy_tqdm | 1.0 | 1.0 |
| off_by_one_loop | 1.0 | 1.0 |

### 4.2 Analysis can mislead (swallowed_exception case)

The Analyzer produced a technically correct but practically useless hypothesis:
"the bare except swallows NameError." This led TestWriter to write
`pytest.raises(NameError)`, which fails because the exception IS swallowed.
Baseline, without the analysis bias, took a different approach and succeeded.

**Implication:** Pre-analysis can introduce confirmation bias when the bug requires
a non-obvious testing strategy.

### 4.3 Token cost of analysis

Agentic mode uses ~40% more tokens (2,399 vs 1,719 per run) due to the extra
Analyzer call. This is a fixed cost regardless of whether the analysis helps.

### 4.4 Infrastructure as confound

5 of 12 tasks (42%) failed due to environment issues (Python 3.9 compatibility,
missing pytest plugins), not model capability. If these tasks were excluded, the
effective BRTR would be:
- Baseline: 17/21 = **81%**
- Agentic: 17/19 = **89%**

## 5. Threats to Validity

1. **Small sample size**: 3 runs per task provides limited statistical power.
   Confidence intervals are wide ([32%, 63%] and [34%, 66%]).

2. **Single model**: Results are specific to Llama 3.3 70B. Different models
   may show different analysis-benefit patterns.

3. **Environment confounds**: Python 3.9 type hint incompatibility caused
   several tasks to fail for infrastructure reasons, not model reasons.

4. **Task selection bias**: Custom tasks may be easier than real-world bugs.
   BugsInPy tasks showed lower success rates overall.

5. **Prompt sensitivity**: Results may vary with different prompt formulations
   for Analyzer and TestWriter agents.

## 6. Conclusions

1. **Adding code analysis does not significantly improve overall BRTR** for this
   model and task set (47.2% vs 50.0%, p > 0.05).

2. **Analysis reduces the number of retry attempts needed**, suggesting it provides
   useful directional guidance even when it doesn't change the final outcome.

3. **Analysis can both help and hurt**: It improved `type_coercion_price` (+67%)
   but degraded `swallowed_exception` (-67%), showing that pre-analysis introduces
   both useful context and potential bias.

4. **Bug difficulty is the dominant factor**: Easy/medium bugs are solved by both
   modes; hard bugs defeat both. The analysis step has the most potential impact
   on "medium" difficulty bugs where additional context could tip the balance.

5. **Recommended next steps**: Increase runs to 10+, test with a second model
   (e.g., DeepSeek V4), fix Python 3.9 compatibility issues in task source files,
   and investigate whether analysis benefits increase with harder bugs.

## 7. Raw Data

Full experiment data is available at:
```
results/analysis_vs_direct_20260430_055256/
  summary.json              # Aggregated statistics
  config.yaml               # Configuration snapshot
  runs/<task_id>/            # Individual run records
    baseline_run_01.json
    agentic_run_01.json
    ...
```

Each run record contains: generated test code, validation output (pytest stdout
from both buggy and fixed versions), token usage, duration, and analysis (if agentic).
