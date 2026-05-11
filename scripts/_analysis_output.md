## A. Model × Mode × Difficulty BRTR

Stratification covariate: difficulty (easy/medium/hard). Difficulty labels are authors' attribution (`scripts/convert_quixbugs.py:TASK_CATALOG`), assigned before the full-benchmark run.

Task distribution: easy=7, medium=13, hard=11 (n=31)

| Model | Mode | Easy | Medium | Hard |
|---|---|---:|---:|---:|
| meta-llama/Llama-3.3-70B-Instruct-Turbo | baseline | 57% (20/35) | 97% (63/65) | 36% (20/55) |
| meta-llama/Llama-3.3-70B-Instruct-Turbo | agentic | 63% (22/35) | 78% (51/65) | 38% (21/55) |
| meta-llama/Llama-3.3-70B-Instruct-Turbo | adaptive | 66% (23/35) | 91% (59/65) | 40% (22/55) |
| openai/gpt-oss-120b | baseline | 100% (35/35) | 100% (65/65) | 84% (46/55) |
| openai/gpt-oss-120b | agentic | — | — | — |
| openai/gpt-oss-120b | adaptive | 100% (35/35) | 100% (65/65) | 95% (52/55) |
| deepseek-ai/DeepSeek-V3 | baseline | 69% (24/35) | 98% (64/65) | 55% (30/55) |
| deepseek-ai/DeepSeek-V3 | agentic | 69% (24/35) | 100% (65/65) | 55% (30/55) |
| deepseek-ai/DeepSeek-V3 | adaptive | 71% (25/35) | 100% (65/65) | 58% (32/55) |

## B. Per-Task `agentic − baseline` Δ-BRTR

Per (task, model), Δ = BRTR(agentic) − BRTR(baseline). Negative Δ = Analyzer hurts. Sonnet column is highlighted because its agentic mode underperformed baseline by 50pp overall, and we want to localize the source.

| Task | Difficulty | Llama-3.3-70B-Instruct-T | gpt-oss-120b | DeepSeek-V3 |
|---|---|---|---|---|
| quixbugs_bitcount | easy | -20pp (100→80) | — | +0pp (100→100) |
| quixbugs_bucketsort | medium | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_find_first_in_sorted | easy | +0pp (0→0) | — | +0pp (0→0) |
| quixbugs_find_in_sorted | easy | +0pp (0→0) | — | +0pp (0→0) |
| quixbugs_flatten | easy | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_gcd | easy | +60pp (0→60) | — | +0pp (80→80) |
| quixbugs_get_factors | medium | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_hanoi | medium | -40pp (100→60) | — | +0pp (100→100) |
| quixbugs_is_valid_parenthesization | medium | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_kheapsort | medium | -20pp (100→80) | — | +0pp (100→100) |
| quixbugs_knapsack | hard | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_kth | hard | -20pp (100→80) | — | +0pp (100→100) |
| quixbugs_lcs_length | hard | +0pp (0→0) | — | +0pp (0→0) |
| quixbugs_levenshtein | hard | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_lis | hard | +0pp (0→0) | — | +0pp (0→0) |
| quixbugs_longest_common_subsequence | hard | +0pp (0→0) | — | +0pp (0→0) |
| quixbugs_max_sublist_sum | easy | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_mergesort | medium | +0pp (60→60) | — | +20pp (80→100) |
| quixbugs_next_palindrome | hard | +0pp (0→0) | — | -40pp (80→40) |
| quixbugs_next_permutation | medium | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_pascal | medium | -20pp (100→80) | — | +0pp (100→100) |
| quixbugs_possible_change | medium | -100pp (100→0) | — | +0pp (100→100) |
| quixbugs_powerset | medium | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_quicksort | medium | -40pp (100→60) | — | +0pp (100→100) |
| quixbugs_rpn_eval | hard | +40pp (0→40) | — | -20pp (80→60) |
| quixbugs_shunting_yard | hard | +20pp (0→20) | — | +60pp (40→100) |
| quixbugs_sieve | easy | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_sqrt | medium | +0pp (100→100) | — | +0pp (100→100) |
| quixbugs_subsequences | medium | -20pp (100→80) | — | +0pp (100→100) |
| quixbugs_to_base | hard | -20pp (100→80) | — | +0pp (100→100) |
| quixbugs_wrap | hard | +0pp (0→0) | — | +0pp (0→0) |

### Worst 5 tasks per model (most negative agentic Δ):

- **meta-llama/Llama-3.3-70B-Instruct-Turbo**: possible_change (-100pp), hanoi (-40pp), quicksort (-40pp), bitcount (-20pp), kheapsort (-20pp)
- **openai/gpt-oss-120b**: 
- **deepseek-ai/DeepSeek-V3**: next_palindrome (-40pp), rpn_eval (-20pp), bitcount (+0pp), bucketsort (+0pp), find_first_in_sorted (+0pp)

## C. Quick observations

- **meta-llama/Llama-3.3-70B-Instruct-Turbo** hard-baseline BRTR: 36% (20/55) — ✓ ceiling broken
- **openai/gpt-oss-120b** hard-baseline BRTR: 84% (46/55) — ✓ ceiling broken
- **deepseek-ai/DeepSeek-V3** hard-baseline BRTR: 55% (30/55) — ✓ ceiling broken
