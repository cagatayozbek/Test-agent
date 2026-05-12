"""Experiment runner: batch execution with statistical output."""

import json
import math
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bugtest.config import Config, load_config
from bugtest.llm import create_client
from bugtest.models import (
    ExperimentSummary,
    ModeStats,
    RunRecord,
    Task,
    TaskMetadata,
    TaskStats,
)
from bugtest.pipeline import run_pipeline
from bugtest.validator import Validator


# --- Task loading ---


# Task-id prefix -> canonical source name. Order matters: longer prefixes first
# so "mbpp_mutation_" wins over a hypothetical "mbpp_".
_SOURCE_PREFIXES: list[tuple[str, str]] = [
    ("mbpp_mutation_", "mbpp_mutation"),
    ("humanevalfix_", "humanevalfix"),
    ("quixbugs_", "quixbugs"),
    ("bugsinpy_", "bugsinpy"),
]


def _infer_source(task_id: str, meta: TaskMetadata) -> str:
    """Return canonical lowercase source name for a task.

    Prefers the metadata.source field (already normalized by our conversion
    scripts); falls back to the task_id prefix for legacy tasks that predate
    the source-tagging convention.
    """
    if meta.source:
        return meta.source.lower().replace("-", "_")
    for prefix, src in _SOURCE_PREFIXES:
        if task_id.startswith(prefix):
            return src
    return "legacy"


def load_tasks(
    tasks_dir: Path,
    include: list[str],
    exclude: list[str],
    sources: list[str] | None = None,
    difficulties: list[str] | None = None,
    bug_types: list[str] | None = None,
) -> list[Task]:
    """Discover and load tasks from tasks_v2/, applying optional filters.

    Filters are applied in order: include, exclude, source, difficulty,
    bug_type. Empty / None lists disable that filter axis. See TasksConfig
    docstring for the canonical source names.
    """
    src_filter = {s.lower().replace("-", "_") for s in (sources or [])}
    diff_filter = {d.lower() for d in (difficulties or [])}
    bt_filter = {b.lower() for b in (bug_types or [])}

    tasks = []
    for task_path in sorted(tasks_dir.iterdir()):
        if not task_path.is_dir():
            continue
        task_id = task_path.name
        if include and task_id not in include:
            continue
        if task_id in exclude:
            continue

        buggy_dir = task_path / "buggy"
        fixed_dir = task_path / "fixed"
        if not (buggy_dir / "source.py").exists():
            continue
        if not (fixed_dir / "source.py").exists():
            continue

        metadata_path = task_path / "metadata.json"
        if metadata_path.exists():
            raw = json.loads(metadata_path.read_text(encoding="utf-8"))
            meta = TaskMetadata.model_validate(raw)
        else:
            meta = TaskMetadata()

        if not meta.get_id():
            meta.task_id = task_id

        if src_filter and _infer_source(task_id, meta) not in src_filter:
            continue
        if diff_filter and (meta.difficulty or "").lower() not in diff_filter:
            continue
        if bt_filter and (meta.bug_type or "").lower() not in bt_filter:
            continue

        tasks.append(
            Task(
                task_id=task_id,
                buggy_code=(buggy_dir / "source.py").read_text(encoding="utf-8"),
                fixed_code=(fixed_dir / "source.py").read_text(encoding="utf-8"),
                buggy_dir=buggy_dir,
                fixed_dir=fixed_dir,
                metadata=meta,
            )
        )
    return tasks


# --- Statistics ---


def _wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for binomial proportion (95% CI)."""
    if total == 0:
        return 0.0, 0.0
    p_hat = successes / total
    denom = 1 + z**2 / total
    center = (p_hat + z**2 / (2 * total)) / denom
    margin = (
        z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total) / denom
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def _compute_mode_stats(mode: str, runs: list[RunRecord]) -> ModeStats:
    total = len(runs)
    successes = sum(1 for r in runs if r.success)
    brtr = successes / total if total > 0 else 0.0
    ci_low, ci_high = _wilson_ci(successes, total)

    successful = [r for r in runs if r.success and r.attempts_to_success is not None]
    avg_att = (
        sum(r.attempts_to_success for r in successful) / len(successful)
        if successful
        else None
    )

    return ModeStats(
        mode=mode,
        total_runs=total,
        successful_runs=successes,
        brtr=round(brtr, 4),
        brtr_ci_lower=round(ci_low, 4),
        brtr_ci_upper=round(ci_high, 4),
        avg_attempts_to_success=round(avg_att, 2) if avg_att else None,
        avg_prompt_tokens=round(
            sum(r.prompt_tokens_total for r in runs) / max(total, 1), 1
        ),
        avg_completion_tokens=round(
            sum(r.completion_tokens_total for r in runs) / max(total, 1), 1
        ),
        avg_duration_seconds=round(
            sum(r.duration_seconds for r in runs) / max(total, 1), 2
        ),
    )


def _compute_task_stats(task_id: str, runs: list[RunRecord]) -> TaskStats:
    baseline = [r for r in runs if r.mode == "baseline"]
    agentic = [r for r in runs if r.mode == "agentic"]

    def brtr(rs: list[RunRecord]) -> float:
        return sum(1 for r in rs if r.success) / len(rs) if rs else 0.0

    def avg_att(rs: list[RunRecord]) -> Optional[float]:
        s = [r for r in rs if r.success and r.attempts_to_success is not None]
        return sum(r.attempts_to_success for r in s) / len(s) if s else None

    return TaskStats(
        task_id=task_id,
        baseline_brtr=round(brtr(baseline), 4),
        agentic_brtr=round(brtr(agentic), 4),
        baseline_avg_attempts=avg_att(baseline),
        agentic_avg_attempts=avg_att(agentic),
    )


# --- Main experiment ---


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def run_experiment(config_path: Path) -> ExperimentSummary:
    """Run complete experiment: all tasks x modes x N runs.

    Uses ThreadPoolExecutor when config.experiment.concurrency > 1,
    sequential loop otherwise (backward-compatible).
    """
    config = load_config(config_path)
    api_key = config.get_api_key()
    llm = create_client(
        model_id=config.model.model_id,
        api_key=api_key,
        base_url=config.model.base_url,
    )
    validator = Validator(timeout_seconds=config.retry.test_timeout_seconds)

    tasks_dir = Path(config.tasks.dir)
    tasks = load_tasks(
        tasks_dir,
        config.tasks.include,
        config.tasks.exclude,
        sources=config.tasks.sources,
        difficulties=config.tasks.difficulties,
        bug_types=config.tasks.bug_types,
    )
    print(f"Loaded {len(tasks)} tasks from {tasks_dir}")

    # Setup results directory. `DEEPTEST_RESULTS_DIR` env var overrides the
    # YAML's `results.dir` so v2.0 runs can be biriktirildi at `results_v2/`
    # without editing every config file (and v1.x results stay where they
    # are for retroactive tagging).
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    experiment_id = f"{config.experiment.name}_{ts}"
    results_root = os.environ.get("DEEPTEST_RESULTS_DIR", config.results.dir)
    results_dir = Path(results_root) / experiment_id
    runs_dir = results_dir / "runs"
    for task in tasks:
        (runs_dir / task.task_id).mkdir(parents=True, exist_ok=True)

    # Build job list: (task, run_num, mode) triples
    jobs: list[tuple[Task, int, str]] = []
    for task in tasks:
        for run_num in range(1, config.experiment.runs_per_task + 1):
            for mode in config.experiment.modes:
                jobs.append((task, run_num, mode))

    concurrency = max(1, getattr(config.experiment, "concurrency", 1))
    print(f"Total jobs: {len(jobs)}, concurrency: {concurrency}")

    write_lock = threading.Lock()
    all_runs: list[RunRecord] = []

    def _run_job(task: Task, run_num: int, mode: str) -> Optional[RunRecord]:
        try:
            record = run_pipeline(
                task=task,
                mode=mode,
                run_number=run_num,
                llm=llm,
                validator=validator,
                max_attempts=config.retry.max_attempts,
                model_id=config.model.model_id,
            )
        except Exception as e:
            # Synthesize a failed RunRecord so BRTR denominators stay correct
            # (otherwise an Analyzer schema-validation crash would silently drop
            # the run, biasing rates upward).
            print(f"ERROR [{task.task_id} {mode} run{run_num}]: {e}")
            record = RunRecord(
                task_id=task.task_id,
                mode=mode,
                run_number=run_num,
                success=False,
                attempts=[],
                total_attempts=0,
                attempts_to_success=None,
                analysis=None,
                prompt_tokens_total=0,
                completion_tokens_total=0,
                duration_seconds=0.0,
                timestamp=_now_iso(),
                error=f"{type(e).__name__}: {e}",
            )

        # Persist immediately so a crash doesn't lose work
        filename = f"{mode}_run_{run_num:02d}.json"
        out_path = runs_dir / task.task_id / filename
        with write_lock:
            out_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    started_at = time.time()
    completed = 0
    if concurrency == 1:
        # Sequential path (backward compatible, easier debugging)
        for task, run_num, mode in jobs:
            record = _run_job(task, run_num, mode)
            completed += 1
            if record is not None:
                all_runs.append(record)
                status = "OK" if record.success else "FAIL"
                print(f"  [{completed}/{len(jobs)}] {task.task_id} {mode} "
                      f"run{run_num}: {status} ({record.duration_seconds:.1f}s)")
    else:
        # Concurrent path
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_run_job, task, run_num, mode): (task, run_num, mode)
                for task, run_num, mode in jobs
            }
            for fut in as_completed(futures):
                task, run_num, mode = futures[fut]
                record = fut.result()
                completed += 1
                if record is not None:
                    all_runs.append(record)
                    status = "OK" if record.success else "FAIL"
                    elapsed = time.time() - started_at
                    rate = completed / elapsed if elapsed > 0 else 0.0
                    eta = (len(jobs) - completed) / rate if rate > 0 else 0.0
                    print(f"  [{completed}/{len(jobs)}] {task.task_id} {mode} "
                          f"run{run_num}: {status} ({record.duration_seconds:.1f}s) "
                          f"| ETA {eta/60:.1f}min")

    # Compute statistics — one ModeStats row per mode actually requested in config.
    mode_stats = [
        _compute_mode_stats(mode, [r for r in all_runs if r.mode == mode])
        for mode in config.experiment.modes
    ]

    task_ids = sorted(set(r.task_id for r in all_runs))
    task_stats = [
        _compute_task_stats(tid, [r for r in all_runs if r.task_id == tid])
        for tid in task_ids
    ]

    summary = ExperimentSummary(
        experiment_name=config.experiment.name,
        model_id=config.model.model_id,
        timestamp=_now_iso(),
        total_tasks=len(tasks),
        runs_per_task=config.experiment.runs_per_task,
        max_attempts=config.retry.max_attempts,
        mode_stats=mode_stats,
        task_stats=task_stats,
        raw_brtr_baseline=[ts.baseline_brtr for ts in task_stats],
        raw_brtr_agentic=[ts.agentic_brtr for ts in task_stats],
    )

    # Save summary + config snapshot
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "summary.json").write_text(
        summary.model_dump_json(indent=2), encoding="utf-8"
    )
    shutil.copy(config_path, results_dir / "config.yaml")

    _print_results(summary)
    return summary


def _print_results(summary: ExperimentSummary) -> None:
    """Print human-readable results table."""
    print(f"\n{'=' * 65}")
    print(f"EXPERIMENT: {summary.experiment_name}")
    print(f"Model: {summary.model_id}")
    print(f"Tasks: {summary.total_tasks}, Runs/task: {summary.runs_per_task}, "
          f"Max attempts: {summary.max_attempts}")
    print(f"{'=' * 65}")

    for ms in summary.mode_stats:
        print(f"\n  {ms.mode.upper()}:")
        print(f"    BRTR: {ms.brtr:.1%}  "
              f"(95% CI: [{ms.brtr_ci_lower:.1%}, {ms.brtr_ci_upper:.1%}])")
        print(f"    Successful: {ms.successful_runs}/{ms.total_runs}")
        if ms.avg_attempts_to_success is not None:
            print(f"    Avg attempts to success: {ms.avg_attempts_to_success:.1f}")
        print(f"    Avg tokens: {ms.avg_prompt_tokens:.0f} prompt, "
              f"{ms.avg_completion_tokens:.0f} completion")
        print(f"    Avg duration: {ms.avg_duration_seconds:.1f}s")

    print(f"\n  {'Task':<35} {'Baseline':>10} {'Agentic':>10} {'Delta':>10}")
    print(f"  {'-' * 65}")
    for ts in summary.task_stats:
        delta = ts.agentic_brtr - ts.baseline_brtr
        sign = "+" if delta >= 0 else ""
        print(f"  {ts.task_id:<35} {ts.baseline_brtr:>9.0%} "
              f"{ts.agentic_brtr:>9.0%} {sign}{delta:>9.0%}")
    print()
