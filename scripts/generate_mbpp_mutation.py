#!/usr/bin/env python3
"""Generate single-mutation bug tasks from the MBPP-sanitized dataset.

Strategy
--------
For each MBPP problem (which ships with `code` and `test_list`):
  1. Parse the code with `ast`.
  2. Enumerate mutation candidates: comparison-op flips, binary-op flips,
     boolean-op flips, and small integer-constant flips.
  3. For each candidate mutant (one mutation at a time):
       - sanity: original code must pass all `test_list` asserts.
       - kill:   mutant must fail at least one assert.
  4. Keep the first viable mutant per problem (single bug, subtle).
  5. Emit tasks_v2 layout: buggy/source.py (mutant), fixed/source.py (original),
     metadata.json with source=MBPP-mutation and the mutation operator name.

Why mutation testing?
---------------------
MBPP problems are hand-vetted but bug-free. Synthetic mutations let us
control difficulty (single-op change) and decouple bug_description from
human paraphrasing: the description is mechanically derived from the AST diff.

Caveats reported in the methodology section:
  - Mutations are synthetic; results may not transfer to natural human bugs.
  - The MBPP test_list has only 3 asserts; some mutations are equivalent
    under this oracle (rejected: no assert flips).
  - At most one mutant per problem.

Usage
-----
    python scripts/generate_mbpp_mutation.py --target 50
    python scripts/generate_mbpp_mutation.py --target 50 --dry
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import random
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from datasets import load_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "evaluation" / "tasks_v2"
DATASET_NAME = "mbpp"
DATASET_CONFIG = "sanitized"
DATASET_SPLITS = "train+test+validation+prompt"
SOURCE_URL = "https://huggingface.co/datasets/google-research-datasets/mbpp"
SEED = 42

CMP_FLIPS: dict[type, type] = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt,
    ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}
BINOP_FLIPS: dict[type, type] = {
    ast.Add: ast.Sub, ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv, ast.FloorDiv: ast.Mult,
    ast.Div: ast.Mult, ast.Mod: ast.FloorDiv,
}
BOOLOP_FLIPS: dict[type, type] = {ast.And: ast.Or, ast.Or: ast.And}

OP_SYMBOL: dict[type, str] = {
    ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
    ast.Eq: "==", ast.NotEq: "!=",
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
    ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%",
    ast.And: "and", ast.Or: "or",
}


def constant_flip(value):
    """Return a flipped value or None if the constant is not mutable."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, int) and not isinstance(value, bool):
        if value == 0:
            return 1
        if value == 1:
            return 0
        if value > 1:
            return value - 1
        if value < 0:
            return value + 1
    return None


@dataclass
class MutationSpec:
    """A single mutation, addressable by its position in ast.walk(tree)."""
    walk_index: int
    kind: str
    description: str
    # For Compare nodes, which op-index to flip (a Compare can chain ops).
    cmp_op_index: Optional[int] = None


def enumerate_mutations(tree: ast.AST) -> list[MutationSpec]:
    """Walk tree once; emit one MutationSpec per applicable site.

    walk_index is the position of the target node in ast.walk(tree). Because
    ast.walk is deterministic and deepcopy preserves structure, the same index
    on a deep copy yields the corresponding node.
    """
    out: list[MutationSpec] = []
    for idx, node in enumerate(ast.walk(tree)):
        if isinstance(node, ast.Compare):
            for op_idx, op in enumerate(node.ops):
                if type(op) in CMP_FLIPS:
                    new_cls = CMP_FLIPS[type(op)]
                    out.append(MutationSpec(
                        walk_index=idx,
                        kind="comparison_operator",
                        description=f"`{OP_SYMBOL[type(op)]}` -> `{OP_SYMBOL[new_cls]}`",
                        cmp_op_index=op_idx,
                    ))
        elif isinstance(node, ast.BinOp) and type(node.op) in BINOP_FLIPS:
            new_cls = BINOP_FLIPS[type(node.op)]
            out.append(MutationSpec(
                walk_index=idx,
                kind="arithmetic_operator",
                description=f"`{OP_SYMBOL[type(node.op)]}` -> `{OP_SYMBOL[new_cls]}`",
            ))
        elif isinstance(node, ast.BoolOp) and type(node.op) in BOOLOP_FLIPS:
            new_cls = BOOLOP_FLIPS[type(node.op)]
            out.append(MutationSpec(
                walk_index=idx,
                kind="boolean_operator",
                description=f"`{OP_SYMBOL[type(node.op)]}` -> `{OP_SYMBOL[new_cls]}`",
            ))
        elif isinstance(node, ast.Constant):
            flipped = constant_flip(node.value)
            if flipped is not None:
                out.append(MutationSpec(
                    walk_index=idx,
                    kind="constant_literal",
                    description=f"`{node.value!r}` -> `{flipped!r}`",
                ))
    return out


def apply_mutation(tree: ast.AST, spec: MutationSpec) -> ast.AST:
    """Deep-copy tree and apply the mutation at spec.walk_index. Returns the copy."""
    new_tree = copy.deepcopy(tree)
    for i, node in enumerate(ast.walk(new_tree)):
        if i != spec.walk_index:
            continue
        if spec.kind == "comparison_operator" and isinstance(node, ast.Compare):
            op_idx = spec.cmp_op_index or 0
            old_cls = type(node.ops[op_idx])
            node.ops[op_idx] = CMP_FLIPS[old_cls]()
        elif spec.kind == "arithmetic_operator" and isinstance(node, ast.BinOp):
            node.op = BINOP_FLIPS[type(node.op)]()
        elif spec.kind == "boolean_operator" and isinstance(node, ast.BoolOp):
            node.op = BOOLOP_FLIPS[type(node.op)]()
        elif spec.kind == "constant_literal" and isinstance(node, ast.Constant):
            node.value = constant_flip(node.value)
        return new_tree
    raise RuntimeError(f"walk_index {spec.walk_index} not found")


def run_tests(code: str, test_list: list[str], test_imports: list[str], timeout: int = 5) -> tuple[int, int, bool]:
    """Run each assertion against `code`. Returns (passed, total, crashed_unexpectedly)."""
    passed = 0
    crashed = False
    imports_block = "\n".join(test_imports)
    for assertion in test_list:
        body = imports_block + "\n" + code + "\n" + assertion + "\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(body)
            path = f.name
        try:
            r = subprocess.run(
                [sys.executable, path],
                capture_output=True, text=True, timeout=timeout,
            )
            if r.returncode == 0:
                passed += 1
            else:
                err = r.stderr + r.stdout
                # AssertionError = legitimate test failure (the signal we want).
                # Anything else (NameError, TypeError, ZeroDivisionError) is a
                # gross crash and disqualifies the mutation as "subtle".
                if "AssertionError" not in err:
                    crashed = True
        except subprocess.TimeoutExpired:
            crashed = True
        finally:
            Path(path).unlink(missing_ok=True)
    return passed, len(test_list), crashed


def find_killing_mutation(
    code: str, test_list: list[str], test_imports: list[str]
) -> Optional[tuple[str, MutationSpec, int]]:
    tree = ast.parse(code)
    specs = enumerate_mutations(tree)
    random.shuffle(specs)

    for spec in specs:
        try:
            mutated_tree = apply_mutation(tree, spec)
            mutated_src = ast.unparse(mutated_tree)
        except Exception:
            continue
        passed, total, crashed = run_tests(mutated_src, test_list, test_imports)
        if crashed:
            continue
        killed = total - passed
        if killed >= 1:
            return mutated_src, spec, killed
    return None


def is_single_function(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return len(funcs) >= 1


def derive_entry_point(code: str) -> Optional[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return None


def build_metadata(
    *, task_id: str, mbpp_id: int, prompt: str, entry_point: str,
    spec: MutationSpec, num_killed: int, total_tests: int,
) -> dict:
    return {
        "task_id": task_id,
        "task_name": entry_point,
        "difficulty": "easy",
        "bug_type": spec.kind,
        "bug_description": (
            f"Synthetic single-mutation bug derived from MBPP problem {mbpp_id}. "
            f"Mutation: {spec.description} ({spec.kind.replace('_', ' ')}). "
            f"This mutation flips {num_killed}/{total_tests} of the MBPP "
            "test assertions when applied to the canonical solution."
        ),
        "test_hint": (
            f"Underlying task: {prompt.strip()} "
            f"Pick a small input where the {spec.kind.replace('_', ' ')} "
            "actually affects the output, and assert the canonical value."
        ),
        "expected_failure_signal": (
            f"At least one MBPP assertion fails on the buggy version "
            f"(the mutation flips {num_killed} of {total_tests} canonical asserts)."
        ),
        "source": "MBPP-mutation",
        "source_url": SOURCE_URL,
        "original_task_id": str(mbpp_id),
        "mbpp_prompt": prompt.strip(),
        "tags": ["mbpp", "synthetic", "mutation", spec.kind],
    }


def convert_problem(ex: dict, *, dry: bool, idx_for_name: int) -> Optional[Path]:
    code = ex["code"]
    test_list: list = list(ex["test_list"])
    test_imports: list = list(ex["test_imports"]) if ex["test_imports"] else []

    if not is_single_function(code):
        return None
    entry_point = derive_entry_point(code)
    if not entry_point:
        return None

    # Sanity gate: original passes all asserts.
    passed, total, crashed = run_tests(code, test_list, test_imports)
    if crashed or passed != total:
        return None

    result = find_killing_mutation(code, test_list, test_imports)
    if result is None:
        return None
    mutated_src, spec, num_killed = result

    # Re-emit the fixed (original) source through ast.unparse so that the only
    # textual diff between buggy/ and fixed/ is the mutation itself. Without
    # this, MBPP's inconsistent whitespace would create spurious diff lines.
    fixed_src = ast.unparse(ast.parse(code))

    mbpp_id = ex["task_id"]
    task_id = f"mbpp_mutation_{idx_for_name:03d}"
    target = TASKS_DIR / task_id

    if dry:
        print(f"  [DRY] {task_id} (mbpp#{mbpp_id}, {spec.kind}, killed {num_killed}/{total})")
        return target

    (target / "buggy").mkdir(parents=True, exist_ok=True)
    (target / "fixed").mkdir(parents=True, exist_ok=True)
    (target / "buggy" / "source.py").write_text(mutated_src + "\n", encoding="utf-8")
    (target / "fixed" / "source.py").write_text(fixed_src + "\n", encoding="utf-8")
    (target / "metadata.json").write_text(
        json.dumps(
            build_metadata(
                task_id=task_id, mbpp_id=mbpp_id, prompt=ex["prompt"],
                entry_point=entry_point, spec=spec,
                num_killed=num_killed, total_tests=total,
            ),
            indent=2, ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"  [OK]  {task_id} (mbpp#{mbpp_id}, {spec.kind}, killed {num_killed}/{total})")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MBPP-mutation tasks")
    parser.add_argument("--target", type=int, default=50,
                        help="Number of tasks to produce (default: 50)")
    parser.add_argument("--dry", action="store_true", help="Show plan without writing")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed (default: 42)")
    args = parser.parse_args()

    random.seed(args.seed)
    print(f"Loading {DATASET_NAME}/{DATASET_CONFIG}/{DATASET_SPLITS} ...")
    ds = load_dataset(DATASET_NAME, DATASET_CONFIG, split=DATASET_SPLITS)
    print(f"  {len(ds)} sanitized problems loaded")

    indices = list(range(len(ds)))
    random.shuffle(indices)

    produced = 0
    visited = 0
    for ds_idx in indices:
        if produced >= args.target:
            break
        ex = ds[ds_idx]
        visited += 1
        out = convert_problem(ex, dry=args.dry, idx_for_name=produced)
        if out is not None:
            produced += 1

    print(f"\nVisited {visited} MBPP problems; produced {produced}/{args.target} tasks.")


if __name__ == "__main__":
    main()
