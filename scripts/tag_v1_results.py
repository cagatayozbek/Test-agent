"""Retroactively tag pre-refactor benchmark results as prompt_version='v1.x'.

The v2.0 prompt refactor introduces a `prompt_version` field on every
RunRecord and ExperimentSummary so post-hoc analysis can separate
prompts. Existing results in `results/` and `benchmark_runs/` were
produced before that field existed; without an explicit tag, downstream
code will treat them as if they had no provenance.

This script walks `results/` and `benchmark_runs/`, finds every JSON
file that looks like a run/summary record, and inserts
`prompt_version: "v1.x"` if the field is missing. It does NOT touch any
metric: no BRTRs are recomputed, no timestamps are rewritten. Files
that already carry a prompt_version are skipped (idempotent).

Default mode is a dry run that prints the planned patches. Pass --apply
to actually write. The patched JSON keeps key order and indentation as
close to the original as `json.dump(indent=2)` allows; if a downstream
diff tool is sensitive to whitespace, prefer the dry run + manual review.

Usage:
    python -m scripts.tag_v1_results              # dry run, both roots
    python -m scripts.tag_v1_results --apply
    python -m scripts.tag_v1_results --root results --apply
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

V1_TAG = "v1.x"


def _is_recordlike(obj: object) -> bool:
    """Heuristic: a JSON object is a record we should tag iff it looks like
    a RunRecord or ExperimentSummary. We don't import the Pydantic models
    here because they have already been extended for v2.0 — we want to
    tag based on the OLD shape, not enforce the new schema."""
    if not isinstance(obj, dict):
        return False
    keys = obj.keys()
    # RunRecord shape (v1.x): task_id + mode + attempts.
    if {"task_id", "mode", "attempts"} <= keys:
        return True
    # ExperimentSummary shape (v1.x): experiment_name + mode_stats.
    if {"experiment_name", "mode_stats"} <= keys:
        return True
    return False


def _tag_in_place(obj: object) -> int:
    """Recursively tag record-shaped dicts. Returns count of patched dicts."""
    patched = 0
    if isinstance(obj, dict):
        if _is_recordlike(obj) and "prompt_version" not in obj:
            obj["prompt_version"] = V1_TAG
            patched += 1
        for v in obj.values():
            patched += _tag_in_place(v)
    elif isinstance(obj, list):
        for v in obj:
            patched += _tag_in_place(v)
    return patched


def _iter_json_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        yield from sorted(root.rglob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", action="append", default=[],
        help="Directory root to scan; pass multiple times. Default: results, benchmark_runs.",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write the patched JSON. Without this, runs as a dry run.",
    )
    args = parser.parse_args()

    roots = [Path(r) for r in (args.root or ["results", "benchmark_runs"])]
    total_files = 0
    total_patched_records = 0
    files_with_changes = 0

    for path in _iter_json_files(roots):
        total_files += 1
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue  # not a JSON file we care about

        patched = _tag_in_place(data)
        if patched == 0:
            continue

        files_with_changes += 1
        total_patched_records += patched
        rel = path.relative_to(Path.cwd()) if path.is_absolute() and str(path).startswith(str(Path.cwd())) else path
        print(f"{'PATCH' if args.apply else 'WOULD-PATCH'} {rel}  (+{patched} record(s))")

        if args.apply:
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"scanned {total_files} JSON file(s); {files_with_changes} need(s) tagging; "
          f"{total_patched_records} record(s) total")
    if not args.apply:
        print("(dry run — re-run with --apply to write changes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
