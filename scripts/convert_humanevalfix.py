#!/usr/bin/env python3
"""Convert HumanEvalFix-Python (bigcode/humanevalpack) to bugtest tasks_v2 format.

Usage:
    python scripts/convert_humanevalfix.py --all          # convert all 164
    python scripts/convert_humanevalfix.py --all --dry    # preview only
    python scripts/convert_humanevalfix.py --task 0       # single problem
    python scripts/convert_humanevalfix.py --list

For each HumanEval-Python problem the dataset provides a hand-injected
single-defect variant. We pair `prompt + buggy_solution` -> buggy/source.py and
`prompt + canonical_solution` -> fixed/source.py, then derive a textual
bug_description from the line-level diff. The HumanEvalFix bug taxonomy
(6 categories) is preserved in metadata.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import textwrap
from pathlib import Path
from typing import Optional

from datasets import load_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "evaluation" / "tasks_v2"

DATASET_NAME = "bigcode/humanevalpack"
DATASET_CONFIG = "python"
DATASET_SPLIT = "test"
SOURCE_URL = "https://huggingface.co/datasets/bigcode/humanevalpack"


def difficulty_from_length(canonical_solution: str) -> str:
    n = len(canonical_solution)
    if n < 250:
        return "easy"
    if n < 500:
        return "medium"
    return "hard"


def extract_changed_lines(buggy: str, fixed: str) -> list[tuple[str, str]]:
    """Return pairs of (buggy_line, fixed_line) for lines that differ.

    Uses difflib's SequenceMatcher to align lines, then for each 'replace'
    op-code emits the changed line pairs. Adds/deletes are collapsed onto
    the closest neighbor for a compact single-line representation.
    """
    bl = buggy.splitlines()
    fl = fixed.splitlines()
    sm = difflib.SequenceMatcher(a=bl, b=fl, autojunk=False)
    pairs: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        b_seg = "\n".join(bl[i1:i2]).strip()
        f_seg = "\n".join(fl[j1:j2]).strip()
        if b_seg or f_seg:
            pairs.append((b_seg or "(missing)", f_seg or "(missing)"))
    return pairs


def build_bug_description(
    buggy_solution: str,
    canonical_solution: str,
    bug_type: str,
    failure_symptoms: str,
) -> str:
    """Generate a concise English bug description from the diff.

    The description identifies the changed line(s), tags the defect class,
    and notes the observable failure symptom. It deliberately avoids
    paraphrasing the fix beyond what is visible in the diff (so a model
    reading it still has work to do to translate the symptom into a test).
    """
    diffs = extract_changed_lines(buggy_solution, canonical_solution)
    if not diffs:
        return (
            f"Single-defect variant ({bug_type}) from HumanEvalFix; "
            f"observable failure: {failure_symptoms}."
        )

    parts: list[str] = []
    for b_line, f_line in diffs[:2]:
        b_short = re.sub(r"\s+", " ", b_line).strip()[:160]
        f_short = re.sub(r"\s+", " ", f_line).strip()[:160]
        parts.append(f"Buggy line: `{b_short}`; correct line: `{f_short}`.")

    cat_blurb = {
        "missing logic": "A required clause is omitted in the buggy version.",
        "excess logic": "The buggy version contains an extraneous operation.",
        "value misuse": "The buggy version uses a wrong literal or constant.",
        "operator misuse": "The buggy version uses the wrong operator.",
        "variable misuse": "The buggy version references the wrong variable.",
        "function misuse": "The buggy version calls the wrong function or method.",
    }.get(bug_type, f"Bug type: {bug_type}.")

    return f"{cat_blurb} {' '.join(parts)} Observable failure: {failure_symptoms}."


_DOCSTRING_EXAMPLE_RE = re.compile(r">>>\s*(.+?)(?:\n\s*([^\s>][^\n]*))?", re.DOTALL)


def extract_test_hint(prompt: str, entry_point: str) -> str:
    """Pull one or two doctest examples out of the docstring.

    HumanEval prompts ship with doctest-style examples. They are a natural
    test-hint source: concrete inputs paired with expected outputs.
    """
    # Find lines starting with `>>>`
    lines = prompt.splitlines()
    examples: list[tuple[str, Optional[str]]] = []
    i = 0
    while i < len(lines) and len(examples) < 2:
        line = lines[i].strip()
        if line.startswith(">>>"):
            call = line[3:].strip()
            expected: Optional[str] = None
            if i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if nxt and not nxt.startswith(">>>"):
                    expected = nxt
            examples.append((call, expected))
        i += 1

    if not examples:
        return (
            f"Call `{entry_point}` with a small concrete input and assert "
            "the expected return value based on the docstring."
        )

    parts: list[str] = []
    for call, expected in examples:
        if expected is not None:
            parts.append(f"`{call}` should return `{expected}`")
        else:
            parts.append(f"call `{call}`")
    return "Try the docstring examples: " + "; ".join(parts) + "."


def build_buggy_source(prompt: str, buggy_solution: str) -> str:
    """Assemble buggy/source.py: prompt provides signature + docstring."""
    return prompt + buggy_solution


def build_fixed_source(prompt: str, canonical_solution: str) -> str:
    """Assemble fixed/source.py: same prompt, canonical body."""
    return prompt + canonical_solution


def slug_from_task_id(task_id: str) -> str:
    """`Python/0` -> `0`. Used to build task names like humanevalfix_000."""
    parts = task_id.split("/")
    if len(parts) == 2 and parts[0].lower() == "python":
        return parts[1]
    return task_id.replace("/", "_")


def convert_one(example: dict, *, dry: bool) -> Path | None:
    raw_id = example["task_id"]
    num = slug_from_task_id(raw_id)
    task_id = f"humanevalfix_{num.zfill(3)}"
    target = TASKS_DIR / task_id

    buggy_src = build_buggy_source(example["prompt"], example["buggy_solution"])
    fixed_src = build_fixed_source(example["prompt"], example["canonical_solution"])

    if buggy_src.strip() == fixed_src.strip():
        # Sanity: should never happen but guard against it.
        print(f"  [SKIP] {task_id}: buggy and fixed identical")
        return None

    bug_type = example["bug_type"]
    failure_symptoms = example["failure_symptoms"]
    entry_point = example["entry_point"]
    difficulty = difficulty_from_length(example["canonical_solution"])

    metadata = {
        "task_id": task_id,
        "task_name": entry_point,
        "difficulty": difficulty,
        "bug_type": bug_type,
        "bug_description": build_bug_description(
            example["buggy_solution"],
            example["canonical_solution"],
            bug_type,
            failure_symptoms,
        ),
        "test_hint": extract_test_hint(example["prompt"], entry_point),
        "expected_failure_signal": (
            f"Observable: {failure_symptoms}. "
            f"Calling `{entry_point}` on inputs covered by the docstring "
            "examples produces a different value from the canonical version."
        ),
        "source": "HumanEvalFix",
        "source_url": SOURCE_URL,
        "original_task_id": raw_id,
        "tags": ["humanevalfix", "function_level", difficulty, bug_type.replace(" ", "_")],
    }

    if dry:
        print(f"  [DRY] {task_id} ({difficulty}, {bug_type})")
        return target

    (target / "buggy").mkdir(parents=True, exist_ok=True)
    (target / "fixed").mkdir(parents=True, exist_ok=True)
    (target / "buggy" / "source.py").write_text(buggy_src, encoding="utf-8")
    (target / "fixed" / "source.py").write_text(fixed_src, encoding="utf-8")
    (target / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"  [OK]  {task_id}  ({difficulty}, {bug_type})")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert HumanEvalFix-Python problems to tasks_v2 format"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", type=str, help="A single task id suffix, e.g. 0 or Python/0")
    group.add_argument("--all", action="store_true", help="Convert all 164 problems")
    group.add_argument("--list", action="store_true", help="List dataset entries with bug_type")
    parser.add_argument("--dry", action="store_true", help="Print actions without writing files")
    args = parser.parse_args()

    print(f"Loading {DATASET_NAME} / {DATASET_CONFIG} / {DATASET_SPLIT} ...")
    ds = load_dataset(DATASET_NAME, DATASET_CONFIG, split=DATASET_SPLIT)
    by_num = {slug_from_task_id(ex["task_id"]): ex for ex in ds}

    if args.list:
        for k, ex in sorted(by_num.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
            print(f"  {ex['task_id']:>12s}  {ex['bug_type']:18s}  -> {ex['entry_point']}")
        return

    if args.task:
        key = slug_from_task_id(args.task) if "/" in args.task else args.task
        if key not in by_num:
            raise SystemExit(f"Task '{args.task}' not in HumanEvalFix-Python.")
        convert_one(by_num[key], dry=args.dry)
        return

    if args.all:
        print(f"Converting {len(ds)} problems" + (" (DRY RUN)" if args.dry else ""))
        ok = 0
        for ex in ds:
            if convert_one(ex, dry=args.dry):
                ok += 1
        print(f"\nDone: {ok}/{len(ds)} tasks written.")


if __name__ == "__main__":
    main()
