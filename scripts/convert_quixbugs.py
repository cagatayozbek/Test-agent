#!/usr/bin/env python3
"""Convert QuixBugs Python programs to bugtest tasks_v2 format.

Usage:
    python scripts/convert_quixbugs.py --task bitcount
    python scripts/convert_quixbugs.py --all
    python scripts/convert_quixbugs.py --list
    python scripts/convert_quixbugs.py --task bitcount --dry
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "evaluation" / "quixbugs_raw"
TASKS_DIR = REPO_ROOT / "evaluation" / "tasks_v2"

SKIP = {
    "node",
    "breadth_first_search",
    "depth_first_search",
    "detect_cycle",
    "minimum_spanning_tree",
    "reverse_linked_list",
    "shortest_path_length",
    "shortest_path_lengths",
    "shortest_paths",
    "topological_ordering",
}


# Per-algorithm curated metadata. Keys MUST match python_programs/*.py stems.
# difficulty: easy | medium | hard (test-generation difficulty, not algorithmic complexity)
# bug_type: defect class (used for post-hoc stratification in analysis)
# bug_description: characterizes the defect without leaking the fix; sent to the LLM in the prompt
# test_hint: a concrete input suggestion for the generated test; sent to the LLM in the prompt
# expected_failure_signal: how the test should fail on the buggy version; reporting + sanity-check only
TASK_CATALOG: dict[str, dict[str, str]] = {
    "bitcount": {
        "difficulty": "easy",
        "bug_type": "bitwise_operator",
        "bug_description": "The buggy version updates `n` with XOR (`n ^= n - 1`) instead of AND (`n &= n - 1`). XOR does not clear the lowest set bit, so the loop never terminates.",
        "test_hint": "Use an input with multiple 1-bits such as bitcount(127); assert that the returned count is correct.",
        "expected_failure_signal": "The test either times out (>5s) or receives a wrong count.",
    },
    "bucketsort": {
        "difficulty": "medium",
        "bug_type": "wrong_variable_reference",
        "bug_description": "The inner loop iterates over `arr` but should iterate over the bucket counts array; as a result, the output is unsorted or contains the wrong number of elements.",
        "test_hint": "Call with a small list containing repeated values (e.g. [3, 1, 2, 1]) and a sufficient bucket count (k=4); assert the output equals the sorted list.",
        "expected_failure_signal": "Output is not sorted or its element multiset differs from the input.",
    },
    "find_first_in_sorted": {
        "difficulty": "easy",
        "bug_type": "loop_boundary",
        "bug_description": "The binary search loop condition is `lo <= hi`; with certain equal-value configurations `mid` does not advance and the loop never terminates.",
        "test_hint": "Search for the first occurrence in a sorted array with duplicates (e.g. [3, 4, 5, 5, 5, 6], target=5 → expected 2).",
        "expected_failure_signal": "Test times out or returns the wrong index.",
    },
    "find_in_sorted": {
        "difficulty": "easy",
        "bug_type": "off_by_one_recursion",
        "bug_description": "When recursing into the upper half the lower bound is `mid` instead of `mid + 1`, which causes infinite recursion when the target lies in the upper half.",
        "test_hint": "Try a call like find_in_sorted([3, 4, 5, 6, 7], 7) where the target is the last element.",
        "expected_failure_signal": "Test times out or raises RecursionError.",
    },
    "flatten": {
        "difficulty": "easy",
        "bug_type": "yield_wrong_value",
        "bug_description": "In the non-list branch the code yields `flatten(x)` (a generator) instead of `x`; the resulting list contains generator objects rather than scalar values.",
        "test_hint": "Call with a small nested list (e.g. [1, [2, 3], [[4]]]) and assert `list(flatten(...))` equals [1, 2, 3, 4].",
        "expected_failure_signal": "Output contains generator objects instead of scalars.",
    },
    "gcd": {
        "difficulty": "easy",
        "bug_type": "argument_order",
        "bug_description": "The recursive call passes arguments as `(a % b, b)`; the correct order is `(b, a % b)`. Because `a % b < b`, the recursion repeats with the same arguments and never terminates.",
        "test_hint": "Use a call like gcd(35, 21); observe a timeout/recursion error or assert the result equals 7.",
        "expected_failure_signal": "Test raises RecursionError or times out.",
    },
    "get_factors": {
        "difficulty": "medium",
        "bug_type": "wrong_base_case",
        "bug_description": "For a prime number the function returns `[]`; it should return `[n]`. Prime inputs lose their own factor.",
        "test_hint": "Assert that get_factors(7) returns [7] (a prime number).",
        "expected_failure_signal": "The function returns [] for a prime input.",
    },
    "hanoi": {
        "difficulty": "medium",
        "bug_type": "wrong_target_variable",
        "bug_description": "In the single-disk branch the move appended is `(start, helper)` instead of `(start, end)`; the generated moves are inconsistent with Tower-of-Hanoi semantics.",
        "test_hint": "Assert that hanoi(2, start=1, end=3) returns exactly [(1,2),(1,3),(2,3)].",
        "expected_failure_signal": "The move list points to wrong destinations; an equality assertion will fail.",
    },
    "is_valid_parenthesization": {
        "difficulty": "medium",
        "bug_type": "missing_final_check",
        "bug_description": "The function returns True after scanning all characters but never checks whether the depth counter ended at zero; the correct version requires a final `depth == 0` check.",
        "test_hint": "Assert that is_valid_parenthesization('((') returns False (more openings than closings).",
        "expected_failure_signal": "The function returns True for an unbalanced input that has too many opening parens.",
    },
    "kheapsort": {
        "difficulty": "medium",
        "bug_type": "wrong_slice_start",
        "bug_description": "After seeding the heap the loop should iterate over `arr[k:]`, not the full `arr`; otherwise the first k elements are processed twice.",
        "test_hint": "Call with a small list (e.g. [3, 2, 1, 5, 4], k=2) and assert the output equals the sorted list.",
        "expected_failure_signal": "Output length exceeds the input length or the elements are not sorted.",
    },
    "knapsack": {
        "difficulty": "hard",
        "bug_type": "off_by_one_comparison",
        "bug_description": "The weight comparison uses `weight < j` but should use `weight <= j`; items that exactly fill the remaining capacity are excluded.",
        "test_hint": "Construct an instance where the optimal solution exactly fills capacity (e.g. capacity=3, items=[(3, 10), (1, 5)]); assert the optimal value.",
        "expected_failure_signal": "The returned value is smaller than the true optimum because exact-fit items are skipped.",
    },
    "kth": {
        "difficulty": "hard",
        "bug_type": "missing_decrement",
        "bug_description": "When recursing into the upper partition the index `k` is passed unchanged; the correct version passes `k - num_lessoreq`. The index semantics break and the wrong element is returned.",
        "test_hint": "Assert that kth([3, 1, 2, 5, 4], 3) returns the correct k-th order statistic (e.g. 4).",
        "expected_failure_signal": "Wrong order statistic is returned, particularly when k targets the upper partition.",
    },
    "lcs_length": {
        "difficulty": "hard",
        "bug_type": "dp_index_error",
        "bug_description": "On a character match the DP update reads `dp[i-1, j] + 1` but should read `dp[i-1, j-1] + 1`; chaining the same column inflates the reported LCS length.",
        "test_hint": "Assert the known result on a small instance, e.g. lcs_length('ABCBDAB', 'BDCAB') == 4.",
        "expected_failure_signal": "The returned LCS length differs from (typically exceeds) the true value.",
    },
    "levenshtein": {
        "difficulty": "hard",
        "bug_type": "extra_increment",
        "bug_description": "When the first characters are equal the result is `1 + levenshtein(source[1:], target[1:])`; the correct version omits the `1 +`. Equal characters should not increase the edit distance.",
        "test_hint": "Use two words whose first characters are equal and assert the result, e.g. levenshtein('abc', 'abd') == 1.",
        "expected_failure_signal": "The returned distance is larger than the true edit distance.",
    },
    "lis": {
        "difficulty": "hard",
        "bug_type": "missing_max",
        "bug_description": "The length update reads `longest = length + 1`; the correct version is `longest = max(longest, length + 1)`. Without the `max` the variable tracks the last chain instead of the longest.",
        "test_hint": "Assert the correct LIS length on a small input, e.g. lis([4, 1, 5, 2, 3]) == 3.",
        "expected_failure_signal": "The returned LIS length is smaller than the true value.",
    },
    "longest_common_subsequence": {
        "difficulty": "hard",
        "bug_type": "missing_recursion_advance",
        "bug_description": "On a match the recursion advances only `a` (`a[1:], b`); it should also advance `b` (to `b[1:]`). The same `b` character can be consumed again.",
        "test_hint": "Check that longest_common_subsequence('AGCAT', 'GAC') returns a valid LCS of the two strings.",
        "expected_failure_signal": "The returned LCS is longer than the true LCS or contains repeated characters that cannot be aligned.",
    },
    "max_sublist_sum": {
        "difficulty": "easy",
        "bug_type": "missing_zero_floor",
        "bug_description": "The Kadane update is `max_ending_here + x`; the correct version clamps it with `max(0, max_ending_here + x)`. Negative accumulation is never reset so the running sum becomes corrupted.",
        "test_hint": "Use a list containing negative values (e.g. [4, -5, 2, 1, -1, 3]) and assert the correct maximum subarray sum (5).",
        "expected_failure_signal": "The returned sum is smaller than the true maximum because negative carries are propagated.",
    },
    "mergesort": {
        "difficulty": "medium",
        "bug_type": "wrong_base_case",
        "bug_description": "The base case is `len(arr) == 0`; the correct base case is `len(arr) <= 1`. A single-element list is split further and the recursion never terminates.",
        "test_hint": "Call with a single-element list (e.g. mergesort([1])) or a small list and observe a recursion error or timeout.",
        "expected_failure_signal": "RecursionError or timeout.",
    },
    "next_palindrome": {
        "difficulty": "hard",
        "bug_type": "missing_return",
        "bug_description": "The all-nines branch returns a value but the ordinary increment branch has no return statement; the function returns None for typical inputs.",
        "test_hint": "Call next_palindrome([1, 4, 3, 4, 1]) and assert the result is a list (not None).",
        "expected_failure_signal": "The function returns None; a comparison against the expected list raises TypeError or fails.",
    },
    "next_permutation": {
        "difficulty": "medium",
        "bug_type": "reversed_comparison",
        "bug_description": "The pivot-finding comparison is `perm[j] < perm[i]`; the correct comparison is `perm[i] < perm[j]`. The algorithm performs the wrong swap and does not produce the lexicographic next permutation.",
        "test_hint": "Assert the known lex-next on a small input, e.g. next_permutation([3, 2, 4, 1]) == [3, 4, 1, 2].",
        "expected_failure_signal": "The returned permutation is not the lexicographic next.",
    },
    "pascal": {
        "difficulty": "medium",
        "bug_type": "off_by_one_range",
        "bug_description": "The inner loop is `range(0, r)`; it should be `range(0, r + 1)`. Each row is missing its final element (the trailing 1).",
        "test_hint": "Assert that pascal(3) produces rows of lengths [1, 2, 3].",
        "expected_failure_signal": "Each row is one element shorter than expected (e.g. the last row has only 2 elements).",
    },
    "possible_change": {
        "difficulty": "medium",
        "bug_type": "missing_base_case",
        "bug_description": "There is no base case for an empty `coins` list; only `total < 0` is handled. When coins is exhausted with a positive total, indexing raises IndexError.",
        "test_hint": "Call possible_change([], 5) and assert it returns 0 (rather than raising IndexError).",
        "expected_failure_signal": "The test catches IndexError or observes an incorrect value.",
    },
    "powerset": {
        "difficulty": "medium",
        "bug_type": "missing_subset_concat",
        "bug_description": "The recursive result only contains subsets that include `first`; the subsets without `first` (the `rest_subsets`) are not concatenated. The correct version is `rest_subsets + [[first] + s for s in rest_subsets]`.",
        "test_hint": "Assert that powerset([1, 2]) has length 4 (including the empty set).",
        "expected_failure_signal": "The power set has size 2^(n-1) or less instead of 2^n.",
    },
    "quicksort": {
        "difficulty": "medium",
        "bug_type": "strict_comparison",
        "bug_description": "The greater partition filters with `x > pivot`; equal values are dropped entirely. The correct comparison (after removing the pivot itself) is `x >= pivot`.",
        "test_hint": "Use a list with duplicate values (e.g. [3, 1, 3, 2]); assert the output is sorted and the length is preserved.",
        "expected_failure_signal": "The output length is less than the input length because duplicates of the pivot are lost.",
    },
    "rpn_eval": {
        "difficulty": "hard",
        "bug_type": "swapped_operands",
        "bug_description": "The operator is invoked as `op(token, a, b)`; the correct order is `op(token, b, a)`. Non-commutative operations (subtraction, division) are applied with swapped operands.",
        "test_hint": "Use an RPN expression containing subtraction or division (e.g. ['5', '1', '-'] → 4) and assert the correct result.",
        "expected_failure_signal": "Subtraction or division returns the wrong sign or value.",
    },
    "shunting_yard": {
        "difficulty": "hard",
        "bug_type": "missing_push",
        "bug_description": "The operator branch is missing `opstack.append(token)`; the output stream contains only operands and no operators.",
        "test_hint": "Assert that shunting_yard(['1', '+', '2']) returns ['1', '2', '+'].",
        "expected_failure_signal": "Output contains no operators at all (only operands).",
    },
    "sieve": {
        "difficulty": "easy",
        "bug_type": "wrong_quantifier",
        "bug_description": "The primality predicate is `any(n % p > 0)`; the correct predicate is `all(n % p > 0)`. `any` is true for nearly every n, so composite numbers are also reported as prime.",
        "test_hint": "Assert that sieve(7) returns exactly [2, 3, 5, 7].",
        "expected_failure_signal": "The output contains composite numbers such as [2, 3, 4, 5, 6, 7].",
    },
    "sqrt": {
        "difficulty": "medium",
        "bug_type": "wrong_convergence_check",
        "bug_description": "The convergence check is `abs(x - approx)`; for Newton-Raphson the residual should be `abs(x - approx ** 2)`. The loop terminates without converging to the actual square root.",
        "test_hint": "Assert that sqrt(2, 0.01) is approximately 1.41 (within epsilon).",
        "expected_failure_signal": "The returned value is far from the true square root, or the loop exits prematurely.",
    },
    "subsequences": {
        "difficulty": "medium",
        "bug_type": "wrong_base_case",
        "bug_description": "The base case for k=0 returns `[]`; the correct base case is `[[]]` (a list containing the empty subsequence). With `[]` the combinatorial count is zero.",
        "test_hint": "Assert that subsequences(a=1, b=5, k=2) has length C(4, 2) = 6.",
        "expected_failure_signal": "The output is an empty list; its length is 0.",
    },
    "to_base": {
        "difficulty": "hard",
        "bug_type": "wrong_concat_order",
        "bug_description": "The accumulation is `result + alphabet[i]`; the correct order is `alphabet[i] + result`. The resulting digits are produced in reverse.",
        "test_hint": "Assert that to_base(31, 16) returns '1F'.",
        "expected_failure_signal": "The function returns the reverse of the expected string (e.g. 'F1').",
    },
    "wrap": {
        "difficulty": "hard",
        "bug_type": "missing_final_append",
        "bug_description": "At the end of the loop the remaining `text` is not appended to the lines list; the trailing words are lost from the output.",
        "test_hint": "Assert that wrap('aaa bbb ccc', 4) returns ['aaa', 'bbb', 'ccc'].",
        "expected_failure_signal": "The output list is one entry shorter than expected because the final line is missing.",
    },
}


def list_available_tasks() -> list[str]:
    buggy_dir = RAW_DIR / "python_programs"
    fixed_dir = RAW_DIR / "correct_python_programs"
    if not (buggy_dir.exists() and fixed_dir.exists()):
        raise SystemExit(f"QuixBugs raw bulunamadi. Beklenen yol: {RAW_DIR}")

    buggy = {p.stem for p in buggy_dir.glob("*.py") if not p.stem.endswith("_test")}
    fixed = {p.stem for p in fixed_dir.glob("*.py") if not p.stem.endswith("_test")}
    return sorted((buggy & fixed) - SKIP)


def convert_task(name: str, *, dry: bool) -> Path | None:
    buggy_src = RAW_DIR / "python_programs" / f"{name}.py"
    fixed_src = RAW_DIR / "correct_python_programs" / f"{name}.py"

    if not buggy_src.exists() or not fixed_src.exists():
        print(f"  [SKIP] {name}: kaynak dosya eksik")
        return None

    if name not in TASK_CATALOG:
        print(f"  [WARN] {name}: TASK_CATALOG'da yok, generic metadata yazilacak")

    catalog = TASK_CATALOG.get(name, {})
    task_id = f"quixbugs_{name}"
    target = TASKS_DIR / task_id

    metadata = {
        "task_id": task_id,
        "task_name": name,
        "difficulty": catalog.get("difficulty", ""),
        "bug_type": catalog.get("bug_type", ""),
        "bug_description": catalog.get(
            "bug_description",
            f"QuixBugs '{name}' algoritmasinda tek satirlik defect var.",
        ),
        "test_hint": catalog.get("test_hint", ""),
        "expected_failure_signal": catalog.get("expected_failure_signal", ""),
        "source": "QuixBugs",
        "source_url": "https://github.com/jkoppel/QuixBugs",
        "tags": ["quixbugs", "algorithmic", catalog.get("difficulty", "")],
    }

    if dry:
        print(f"  [DRY] {name} -> {target}")
        print(f"        difficulty: {metadata['difficulty']}, bug_type: {metadata['bug_type']}")
        return target

    (target / "buggy").mkdir(parents=True, exist_ok=True)
    (target / "fixed").mkdir(parents=True, exist_ok=True)

    # Byte-level copy preserves original line endings (e.g. wrap.py uses CRLF)
    # so the converted task is bit-identical to the upstream QuixBugs source.
    (target / "buggy" / "source.py").write_bytes(buggy_src.read_bytes())
    (target / "fixed" / "source.py").write_bytes(fixed_src.read_bytes())
    (target / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"  [OK]  {task_id}  ({metadata['difficulty']}, {metadata['bug_type']})")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QuixBugs Python programlarini tasks_v2 formatina donusturur"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", help="Tek bir QuixBugs algoritmasi adi (orn: bitcount)")
    group.add_argument("--all", action="store_true", help="Tum uygun algoritmalari donustur")
    group.add_argument("--list", action="store_true", help="Donusturulebilir algoritmalari listele")
    parser.add_argument("--dry", action="store_true", help="Sadece goster, dosya yazma")
    args = parser.parse_args()

    available = list_available_tasks()

    if args.list:
        print(f"Donusturulebilir {len(available)} algoritma:")
        for name in available:
            cat = TASK_CATALOG.get(name, {})
            tag = f"[{cat.get('difficulty', '?')}/{cat.get('bug_type', '?')}]"
            print(f"  - {name:30s} {tag}")
        missing = [n for n in available if n not in TASK_CATALOG]
        if missing:
            print(f"\nUYARI: {len(missing)} algoritma TASK_CATALOG'da eksik: {missing}")
        return

    if args.task:
        if args.task not in available:
            if args.task in SKIP:
                raise SystemExit(
                    f"'{args.task}' helper bagimliligi nedeniyle MVP'de atlaniyor."
                )
            raise SystemExit(
                f"'{args.task}' QuixBugs'ta bulunamadi. --list ile listeyi gorun."
            )
        convert_task(args.task, dry=args.dry)
    elif args.all:
        print(
            f"Donusturuluyor: {len(available)} algoritma"
            + (" (DRY RUN)" if args.dry else "")
        )
        for name in available:
            convert_task(name, dry=args.dry)


if __name__ == "__main__":
    main()
