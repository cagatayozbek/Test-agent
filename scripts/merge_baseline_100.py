"""Merge the interrupted baseline run with its resume continuation into a
single folder with a freshly computed summary.json.

Sources (read-only):
  results/benchmark_v2_sonnet_100_baseline_20260516_192612/runs/   (52 tasks filled, 48 empty)
  results/benchmark_v2_sonnet_100_baseline_resume_20260516_221800/runs/ (48 tasks)

Output:
  results/benchmark_v2_sonnet_100_baseline_merged/
    runs/<task_id>/baseline_run_NN.json
    config.yaml      (copy of benchmark_v2_sonnet_100_baseline.yaml)
    summary.json     (recomputed from the 300 merged run records)
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from bugtest.experiment import _compute_mode_stats, _compute_task_stats
from bugtest.models import ExperimentSummary, RunRecord

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
SRC_BASELINE = RESULTS / "benchmark_v2_sonnet_100_baseline_20260516_192612"
SRC_RESUME = RESULTS / "benchmark_v2_sonnet_100_baseline_resume_20260516_221800"
CONFIG_SRC = ROOT / "benchmark_v2_sonnet_100_baseline.yaml"
OUT = RESULTS / "benchmark_v2_sonnet_100_baseline_merged"


def copy_runs(src_runs: Path, dst_runs: Path) -> tuple[int, int]:
    """Copy non-empty task dirs from src_runs into dst_runs. Returns (tasks, files)."""
    n_tasks = n_files = 0
    for task_dir in sorted(src_runs.iterdir()):
        if not task_dir.is_dir():
            continue
        files = sorted(task_dir.glob("*.json"))
        if not files:
            continue
        out_task = dst_runs / task_dir.name
        out_task.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, out_task / f.name)
            n_files += 1
        n_tasks += 1
    return n_tasks, n_files


def load_records(runs_dir: Path) -> list[RunRecord]:
    records: list[RunRecord] = []
    for task_dir in sorted(runs_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        for f in sorted(task_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            records.append(RunRecord.model_validate(data))
    return records


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    runs_out = OUT / "runs"
    runs_out.mkdir(parents=True)

    t1, f1 = copy_runs(SRC_BASELINE / "runs", runs_out)
    t2, f2 = copy_runs(SRC_RESUME / "runs", runs_out)
    print(f"baseline   : {t1:3d} tasks, {f1:4d} files")
    print(f"resume     : {t2:3d} tasks, {f2:4d} files")

    # Sanity: no overlap, total = 100 tasks, 300 files (3 runs/task)
    total_tasks = sum(1 for d in runs_out.iterdir() if d.is_dir())
    total_files = sum(1 for d in runs_out.iterdir() for _ in d.glob("*.json"))
    print(f"merged     : {total_tasks:3d} tasks, {total_files:4d} files")

    shutil.copy2(CONFIG_SRC, OUT / "config.yaml")

    records = load_records(runs_out)
    modes = sorted({r.mode for r in records})
    mode_stats = [_compute_mode_stats(m, [r for r in records if r.mode == m]) for m in modes]
    task_ids = sorted({r.task_id for r in records})
    task_stats = [_compute_task_stats(t, [r for r in records if r.task_id == t]) for t in task_ids]

    runs_per_task = max((r.run_number for r in records), default=0)
    max_attempts = max((len(r.attempts) for r in records), default=0)
    model_id = next((r for r in records), None)
    summary = ExperimentSummary(
        experiment_name="benchmark_v2_sonnet_100_baseline",
        model_id="sonnet",
        timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        total_tasks=len(task_ids),
        runs_per_task=runs_per_task,
        max_attempts=max_attempts,
        mode_stats=mode_stats,
        task_stats=task_stats,
        raw_brtr_baseline=[ts.baseline_brtr for ts in task_stats],
        raw_brtr_agentic=[ts.agentic_brtr for ts in task_stats],
    )
    (OUT / "summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")

    print()
    print(f"  modes seen           : {modes}")
    for ms in mode_stats:
        print(f"  {ms.mode:>10} BRTR     : {ms.brtr:.1%}  "
              f"({ms.successful_runs}/{ms.total_runs}, "
              f"CI [{ms.brtr_ci_lower:.1%}, {ms.brtr_ci_upper:.1%}])")
    print(f"  output               : {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
