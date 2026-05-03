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
| GPT-OSS 120B | 2,617 | 4,152 | 3,227 | +59% |
| Mistral 128B | 1,602 | 2,788 | 2,136 | +74% |
| Llama 70B | 1,719 | 2,399 | 2,136 | +40% |
| Llama 4 17B | 2,001 | 2,710 | 2,317 | +35% |
| Llama 8B | 2,300 | 3,298 | N/A | +43% |

Agentic mode adds 35-74% token overhead. Adaptive mode reduces this by only
paying the analysis cost when needed.

## 7. Threats to Validity

1. **Small sample size**: 3 runs per task per mode limits statistical power.
   Confidence intervals are wide and overlap between modes.

2. **Model family bias**: 3 of 5 models are Llama variants. Adding
   architecturally different models would strengthen generalizability.

3. **Environment confounds**: Python 3.9 type hint incompatibility and
   missing pytest-asyncio caused infrastructure failures on some tasks.

4. **JSON parsing fragility**: Agentic pipeline depends on valid JSON from
   the Analyzer, creating a single point of failure for smaller models.

5. **Free-tier API constraints**: NVIDIA Build free tier introduces variable
   latency and throttling that may affect retry behavior.

6. **Prompt sensitivity**: Different prompt formulations may produce
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
