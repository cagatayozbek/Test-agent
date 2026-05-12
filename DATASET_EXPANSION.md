# Dataset Expansion — v2 (2026-05-11)

This document records the expansion of the bug-revealing test-generation
benchmark from a single source (QuixBugs, n=31) to a five-source curated set
of **n=100** tasks. The original `PREREGISTRATION.md` covers the
QuixBugs-only run completed on 2026-05-10 and is left unchanged. **Any new
benchmark run that uses the expanded set must be pre-registered separately
(see `PREREGISTRATION_V2.md`).**

## 1. Final composition (100 tasks across 5 sources)

Generation initially produced 257 tasks across the four new sources plus the
existing 5 BugsInPy + 7 legacy tasks. Per author decision on 2026-05-11 the
working set was trimmed to **100 tasks** to control cost; the kept subset is
frozen in `v2_keep_100.json` (deterministic via `random.seed(42)` on
alphabetically-sorted bucket lists, guaranteed to contain the 25 pre-
registered tasks from `PREREGISTRATION_V2.md`).

| Source | kept | dropped | Origin | Difficulty (easy / med / hard / unset) | Reproducible build |
| --- | --- | --- | --- | --- | --- |
| QuixBugs (non-graph subset) | 30 | 1 | jkoppel/QuixBugs @ 4257f44 | 7 / 12 / 11 / 0 | `scripts/convert_quixbugs.py --all` |
| HumanEvalFix-Python | 40 | 124 | bigcode/humanevalpack (HF) | 32 / 6 / 2 / 0 | `scripts/convert_humanevalfix.py --all` |
| MBPP-mutation | 20 | 30 | google-research/mbpp (sanitized) + synthetic single-mutation | 20 / 0 / 0 / 0 | `scripts/generate_mbpp_mutation.py --target 50 --seed 42` |
| BugsInPy | 5 | 0 | manual simplified reproductions | 3 / 2 / 0 / 0 | preserved from prior dataset |
| legacy (hand-written) | 5 | 2 | author hand-curated | 0 / 0 / 0 / 5 | preserved |
| **total** | **100** | **157** | | **62 / 20 / 13 / 5** | |

The 157 dropped tasks are not reachable via `evaluation/tasks_v2/`; the
generation scripts can recreate them from the upstream sources if needed.
Dropped legacy: `boundary_threshold`, `cache_invalidation`. Dropped QuixBugs:
one task removed deterministically.

## 2. Provenance and verification

### 2.1 QuixBugs
- Source repo `evaluation/quixbugs_raw/` cloned from
  `https://github.com/jkoppel/QuixBugs` at commit `4257f44`.
- `buggy/source.py` and `fixed/source.py` are **byte-identical** to upstream
  `python_programs/<X>.py` and `correct_python_programs/<X>.py` respectively
  (verified by `diff -q`; zero mismatches across all 31 tasks).
- Metadata translated from Turkish to English in this expansion; bug content
  and difficulty labels unchanged.

### 2.2 HumanEvalFix
- Loaded via `datasets.load_dataset("bigcode/humanevalpack", "python",
  split="test")`. 164 problems, one defect variant each.
- `buggy/source.py` = `prompt + buggy_solution` (HF fields concatenated).
- `fixed/source.py` = `prompt + canonical_solution`.
- `bug_type` is the dataset's own taxonomy (6 categories: missing/excess logic,
  value/operator/variable/function misuse).
- `bug_description` is machine-generated from the AST diff. `test_hint` is
  extracted from the problem's docstring examples.
- **Behavioral sanity check** (5 samples): canonical version passes
  `HumanEvalFix.test` for the problem and buggy version fails. Spot-check
  validates the entire conversion pipeline.

### 2.3 MBPP-mutation
- Loaded from `mbpp` sanitized split (427 hand-vetted problems).
- For each problem the script enumerates AST mutations (comparison-op flip,
  arithmetic-op flip, boolean-op flip, small integer-constant flip) and keeps
  the first mutant that (a) does not gross-crash and (b) flips at least one of
  the MBPP `test_list` assertions. Random seed `42`.
- 67 MBPP problems visited to produce 50 tasks (74.6% hit rate). Skipped
  problems had no killable mutation under the 3-assert oracle, or were
  equivalent mutations.
- **Behavioral sanity check** (all 50): every `fixed/source.py` passes all
  MBPP asserts; every `buggy/source.py` flips ≥1 assert with no unintended
  crash. **50/50 pass.**

### 2.4 Difficulty labeling
| Source | Method | Notes |
| --- | --- | --- |
| QuixBugs | hand-curated (authors) | not from QuixBugs paper |
| HumanEvalFix | proxy: `len(canonical_solution)` < 250 → easy, 250-500 → medium, ≥500 → hard | length is an imperfect proxy; reported as such |
| MBPP-mutation | uniformly "easy" | single-op mutations on simple MBPP problems |

Difficulty is a post-hoc covariate; the LLM never sees it.

## 3. Methodological caveats

These caveats apply to **any** result reported on the expanded set. They must
be disclosed in the methods section of a paper using this benchmark.

### 3.1 Information leakage in `bug_description` / `test_hint`
Across all four sources the metadata supplies a paraphrase of the bug AND a
suggested input that triggers it. This is intentional for this benchmark
(the task is *test generation given a bug description*, not *bug
localization*) but **inflates measured BRTR relative to a hint-free
formulation**. Any direct comparison with hint-free APR benchmarks (e.g.,
Prenner et al. 2022, Xia & Zhang 2023) is invalid. An ablation removing
`bug_description` / `test_hint` is strongly recommended.

### 3.2 Subset disclosure
- QuixBugs: 31 of 40 (non-graph subset). Cannot be compared head-to-head with
  full-QuixBugs APR results.
- HumanEvalFix: all 164.
- MBPP-mutation: 50 out of an unbounded pool (mutation operator coverage is
  restricted to four categories).

### 3.3 Synthetic mutations
MBPP-mutation bugs are not natural defects. Mutation testing's classical
caveats apply:
- Some "killed mutants" may correspond to bug patterns that humans rarely
  produce.
- Equivalent mutations (not killable under the 3-assert oracle) are rejected,
  introducing selection bias toward easily-killed mutants.

### 3.4 Data contamination
QuixBugs (2017), HumanEvalFix (2023), and MBPP (2021) are all public and
nearly certain to be present in every evaluated LLM's training corpus.
Reported BRTR is an **upper bound** on capability — do not interpret as
out-of-distribution generalization.

### 3.5 Test oracle uses fixed source as ground truth
Validation does not use any of the upstream test suites (QuixBugs'
`python_testcases/`, HumanEvalFix's `test` field, or MBPP's `test_list`).
Instead, the LLM-generated test must FAIL on `buggy/source.py` and PASS on
`fixed/source.py` — a differential oracle. This is appropriate for the test-
generation task but means BRTR is not directly comparable to APR pass-rate
metrics on the same sources.

## 4. Build / regenerate from clean state

```bash
# QuixBugs (31)
python3 scripts/convert_quixbugs.py --all

# HumanEvalFix (164)
python3 scripts/convert_humanevalfix.py --all

# MBPP-mutation (50; deterministic with seed 42)
python3 scripts/generate_mbpp_mutation.py --target 50 --seed 42
```

Requires `datasets >= 4.8` and network access on first run (Hugging Face Hub).

## 5. Pre-registration for future runs on this set

This expansion is **not** itself a pre-registration. Any benchmark run that
uses tasks beyond the original n=31 must publish a new pre-registration
fixing: (a) the exact task subset, (b) model set, (c) modes, (d) sample size,
(e) analysis plan — *before* the run is executed.
