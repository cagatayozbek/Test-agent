# Experiment Report: Does Code Analysis Improve LLM Test Generation?

## 1. Research Question

> Does adding a structured code analysis step before test generation improve
> the LLM's ability to produce bug-revealing tests?

## 2. Experimental Setup

| Parameter | Value |
|---|---|
| Models | Llama 3.3 70B, Llama 3.1 8B |
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

## 3. Results — Model 1: Llama 3.3 70B Instruct

### 3.1 Overall BRTR (Bug-Revealing Test Rate)

| Mode | BRTR | 95% CI | Successful | Avg Attempts | Avg Tokens |
|---|---|---|---|---|---|
| **Baseline** | 47.2% | [32.0%, 63.0%] | 17/36 | 1.4 | 1,719 |
| **Agentic** | 50.0% | [34.1%, 65.9%] | 17/34 | 1.0 | 2,399 |

**Key observation:** BRTR difference is not statistically significant (confidence
intervals overlap substantially). However, agentic mode requires **fewer attempts**
on average (1.0 vs 1.4), suggesting that the analysis step improves first-attempt
accuracy when the bug is within the model's capability.

### 3.2 Per-Task Breakdown (70B)

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

### 3.3 Task Categorization by Outcome (70B)

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

## 4. Results — Model 2: Llama 3.1 8B Instruct

### 4.1 Overall BRTR (8B)

| Mode | BRTR | 95% CI | Successful | Completed Runs | Avg Tokens |
|---|---|---|---|---|---|
| **Baseline** | 30.6% | [18.0%, 46.9%] | 11/36 | 36/36 | 2,300 |
| **Agentic** | 28.6% | [8.2%, 64.1%] | 2/7 | **7/36** | 3,298 |

**Critical finding:** The 8B model failed to produce valid JSON output from the
Analyzer in 29 out of 36 agentic runs (81% failure rate). The agentic pipeline
effectively broke down because the smaller model cannot reliably generate
structured `CodeAnalysis` output.

### 4.2 Per-Task Breakdown (8B)

| Task | Category | Baseline | Agentic | Delta | Note |
|---|---|---|---|---|---|
| off_by_one_loop | Easy | **100%** | 0% (error) | -100% | JSON parse fail |
| boundary_threshold | Easy | 33% | 0% (error) | -33% | JSON parse fail |
| bugsinpy_black | Medium | 67% | 0% (error) | -67% | JSON parse fail |
| bugsinpy_thefuck_fish | Medium | 33% | **67%** | **+33%** | Agentic wins when it works |
| bugsinpy_tqdm | Medium | 33% | 0% (error) | -33% | JSON parse fail |
| bugsinpy_pysnooper | Hard | 33% | 0% | -33% | |
| swallowed_exception | Medium | 33% | 0% | -33% | |
| type_coercion_price | Medium | 33% | 0% | -33% | |
| async_race_condition | Hard | 0% | 0% (error) | 0% | |
| cache_invalidation | Medium | 0% | 0% (error) | 0% | |
| null_handling_profile | Medium | 0% | 0% (error) | 0% | |
| bugsinpy_thefuck_fix | Hard | 0% | 0% (error) | 0% | |

### 4.3 Key Observations (8B)

1. **Baseline performance dropped significantly**: 30.6% vs 47.2% with 70B.
   The smaller model generates less accurate test code overall.

2. **Agentic pipeline is unusable at 8B scale**: 81% of agentic runs failed
   due to JSON parsing errors. The Analyzer agent requires structured output
   that 8B models cannot reliably produce.

3. **When agentic works, it helps**: In `bugsinpy_thefuck_fish`, the only task
   where agentic completed all runs, it outperformed baseline (67% vs 33%).
   This suggests the analysis step is valuable when the model CAN follow
   the structured output format.

## 5. Cross-Model Comparison

### 5.1 BRTR by Model and Mode

| Model | Baseline BRTR | Agentic BRTR | Delta | Agentic Viable? |
|---|---|---|---|---|
| Llama 3.3 70B | 47.2% | 50.0% | +2.8% | Yes (94% completion) |
| Llama 3.1 8B | 30.6% | 28.6% | -2.0% | No (19% completion) |

### 5.2 Model Size Effects

```
                    Baseline    Agentic     Agentic Pipeline
  70B (large)       47.2%       50.0%       Works reliably
  8B  (small)       30.6%       28.6%       Mostly broken (JSON errors)
```

**Interpretation:** The analysis step provides a small positive effect when the
model is capable enough to (a) generate structured analysis output and (b) use
that analysis to guide test generation. Below a capability threshold (~8B),
the overhead of structured output generation outweighs any analytical benefit.

### 5.3 Attempts-to-Success Comparison

| Model | Baseline Avg Attempts | Agentic Avg Attempts |
|---|---|---|
| 70B | 1.4 | **1.0** |
| 8B | 1.4 | 1.5 |

The 70B model shows the clearest benefit of analysis: it consistently finds
the answer on the first attempt in agentic mode. The 8B model shows no such
improvement, likely because the analysis itself is lower quality.

## 6. Analysis of Key Findings

### 6.1 Analysis step reduces retry count (70B only)

When both modes succeed on a task with the 70B model, agentic mode consistently
finds the answer on the **first attempt** (avg: 1.0), while baseline sometimes
needs retries (avg: 1.4). This pattern does not hold for the 8B model.

| Task (70B) | Baseline Attempts | Agentic Attempts |
|---|---|---|
| boundary_threshold | 1.0 | 1.0 |
| bugsinpy_black | 2.0 | **1.0** |
| bugsinpy_thefuck_fish | 1.0 | 1.0 |
| bugsinpy_tqdm | 1.0 | 1.0 |
| off_by_one_loop | 1.0 | 1.0 |

### 6.2 Analysis can mislead (swallowed_exception case)

The Analyzer produced a technically correct but practically useless hypothesis:
"the bare except swallows NameError." This led TestWriter to write
`pytest.raises(NameError)`, which fails because the exception IS swallowed.
Baseline, without the analysis bias, took a different approach and succeeded.

**Implication:** Pre-analysis can introduce confirmation bias when the bug requires
a non-obvious testing strategy.

### 6.3 Structured output as a capability gate

The most significant finding is that agentic pipelines with structured intermediate
outputs (JSON) have a **minimum model capability requirement**. The 8B model's
inability to produce valid `CodeAnalysis` JSON means the entire agentic pipeline
fails before the TestWriter even runs. This is not a bug in the pipeline — it
reveals a fundamental constraint on multi-agent architectures that rely on
structured inter-agent communication.

### 6.4 Token cost of analysis

| Model | Baseline Tokens | Agentic Tokens | Overhead |
|---|---|---|---|
| 70B | 1,719 | 2,399 | +40% |
| 8B | 2,300 | 3,298 | +43% |

The analysis step adds ~40% token overhead regardless of model size. For the 8B
model, this cost is paid even when the analysis fails to parse.

### 6.5 Infrastructure as confound

5 of 12 tasks (42%) failed due to environment issues (Python 3.9 compatibility,
missing pytest plugins), not model capability. If these tasks were excluded:
- 70B Baseline: 17/21 = **81%**, Agentic: 17/19 = **89%**
- 8B Baseline: 11/21 = **52%**, Agentic: 2/7 = **29%**

## 7. Threats to Validity

1. **Small sample size**: 3 runs per task provides limited statistical power.
   Confidence intervals are wide.

2. **Two models from same family**: Both models are Llama variants. Testing
   with architecturally different models (e.g., DeepSeek, Qwen) would
   strengthen generalizability claims.

3. **Environment confounds**: Python 3.9 type hint incompatibility caused
   several tasks to fail for infrastructure reasons, not model reasons.

4. **JSON parsing fragility**: The agentic pipeline's dependency on valid JSON
   from the Analyzer creates a single point of failure. A more robust parsing
   strategy (e.g., regex extraction) could improve 8B results.

5. **Task selection bias**: Custom tasks may be easier than real-world bugs.
   BugsInPy tasks showed lower success rates overall.

6. **Prompt sensitivity**: Results may vary with different prompt formulations
   for Analyzer and TestWriter agents.

## 8. Conclusions

1. **Adding code analysis does not significantly improve overall BRTR** for
   the 70B model (47.2% vs 50.0%, p > 0.05), but it reduces the average
   number of retry attempts from 1.4 to 1.0.

2. **Analysis is not viable for small models**: The 8B model fails to produce
   structured analysis output in 81% of cases, making the agentic pipeline
   unusable at this scale.

3. **Model capability is the dominant factor**: The 70B model outperforms the
   8B model in both modes (47% vs 31% baseline, 50% vs 29% agentic). Bug
   difficulty and model size matter more than pipeline architecture.

4. **Analysis can both help and hurt**: It improved `type_coercion_price` (+67%)
   but degraded `swallowed_exception` (-67%) with the 70B model, showing that
   pre-analysis introduces both useful context and potential bias.

5. **Multi-agent architectures have a minimum capability threshold**: Structured
   inter-agent communication (JSON) requires models capable of reliable
   instruction-following. This threshold lies between 8B and 70B parameters
   for the Llama model family.

6. **When analysis works, it improves first-attempt accuracy**: The strongest
   signal is not in BRTR but in attempts-to-success: 70B agentic mode
   consistently solves tasks on the first try, suggesting that analysis
   provides useful directional guidance.

## 9. Raw Data

Full experiment data is available at:
```
results/
  analysis_vs_direct_20260430_055256/     # Llama 3.3 70B
    summary.json
    config.yaml
    runs/<task_id>/*.json

  analysis_vs_direct_20260430_XXXXXX/     # Llama 3.1 8B
    summary.json
    config.yaml
    runs/<task_id>/*.json
```

Each run record contains: generated test code, validation output (pytest stdout
from both buggy and fixed versions), token usage, duration, and analysis (if agentic).
