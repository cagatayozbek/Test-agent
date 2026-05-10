"""Full benchmark runner: 5 models × all converted QuixBugs tasks × 3 modes × N runs.

Per model: in-place updates bugtest_config.yaml, runs concurrent experiment, restores config.
Pre-registered exclusions:
  - mistralai/mistral-medium-3.5-128b: out (smoke instability)
  - openai/gpt-oss-120b × agentic: skipped (CodeAnalysis schema validation error)

Usage:
    python scripts/run_full_benchmark.py
    python scripts/run_full_benchmark.py --concurrency 8 --runs 5 --tasks-glob 'quixbugs_*'
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "bugtest_config.yaml"
RESULTS_DIR = REPO_ROOT / "results"
ADAPTIVE_RUNNER = REPO_ROOT / "run_adaptive_all.py"
FULL_OUTPUT = REPO_ROOT / "full_benchmark_summary.json"

# Pre-registered models (mistral excluded — see PREREGISTRATION.md)
MODELS: list[tuple[str, str]] = [
    ("meta/llama-3.1-8b-instruct", "NVIDIA_API_KEY"),
    ("meta/llama-3.3-70b-instruct", "NVIDIA_API_KEY"),
    ("meta/llama-4-maverick-17b-128e-instruct", "NVIDIA_API_KEY"),
    ("openai/gpt-oss-120b", "NVIDIA_API_KEY"),
    ("sonnet", "CLAUDE_CODE_KEY"),
]

# Pre-registered (model, mode) exclusions
MODEL_MODE_EXCLUSIONS: dict[str, list[str]] = {
    "openai/gpt-oss-120b": ["agentic"],  # Analyzer schema validation always fails
}

ALL_MODES = ["baseline", "agentic", "adaptive"]


def get_nvidia_key() -> str:
    if k := os.environ.get("NVIDIA_API_KEY"):
        return k
    if ADAPTIVE_RUNNER.exists():
        text = ADAPTIVE_RUNNER.read_text(encoding="utf-8")
        match = re.search(r'NVIDIA_API_KEY"\]\s*=\s*"(nvapi-[A-Za-z0-9_\-]+)"', text)
        if match:
            return match.group(1)
    raise SystemExit("NVIDIA_API_KEY ortamda yok ve run_adaptive_all.py'de bulunamadi")


def discover_tasks(glob_pattern: str) -> list[str]:
    tasks_dir = REPO_ROOT / "evaluation" / "tasks_v2"
    return sorted(p.name for p in tasks_dir.glob(glob_pattern) if p.is_dir())


def write_config_for(
    model_id: str,
    api_key_env: str,
    runs_per_task: int,
    concurrency: int,
    modes: list[str],
    tasks: list[str],
) -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text())
    config["model"]["model_id"] = model_id
    config["model"]["api_key_env"] = api_key_env
    config["experiment"]["runs_per_task"] = runs_per_task
    config["experiment"]["concurrency"] = concurrency
    config["experiment"]["modes"] = modes
    config["tasks"]["include"] = list(tasks)
    config["tasks"]["exclude"] = []
    CONFIG_PATH.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))


def restore_config() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text())
    config["model"]["model_id"] = "sonnet"
    config["model"]["api_key_env"] = "CLAUDE_CODE_KEY"
    config["experiment"]["runs_per_task"] = 5
    config["experiment"]["concurrency"] = 8
    config["experiment"]["modes"] = ALL_MODES
    config["tasks"]["include"] = []
    config["tasks"]["exclude"] = []
    CONFIG_PATH.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))


def run_model(
    model_id: str,
    api_key_env: str,
    env: dict,
    runs_per_task: int,
    concurrency: int,
    tasks: list[str],
) -> dict:
    modes = [m for m in ALL_MODES if m not in MODEL_MODE_EXCLUSIONS.get(model_id, [])]
    write_config_for(model_id, api_key_env, runs_per_task, concurrency, modes, tasks)

    print(f"\n{'=' * 78}")
    print(f"  MODEL: {model_id}")
    print(f"  modes: {modes} | runs/task: {runs_per_task} | tasks: {len(tasks)} "
          f"| concurrency: {concurrency}")
    print(f"{'=' * 78}")

    pre_dirs = (
        {d.name for d in RESULTS_DIR.iterdir()} if RESULTS_DIR.exists() else set()
    )

    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "bugtest", str(CONFIG_PATH)],
        env=env,
        cwd=REPO_ROOT,
        text=True,
    )
    duration = time.time() - t0

    post_dirs = (
        {d.name for d in RESULTS_DIR.iterdir()} if RESULTS_DIR.exists() else set()
    )
    new_dirs = post_dirs - pre_dirs
    new_dir_name = max(new_dirs) if new_dirs else None

    summary_data = None
    if new_dir_name:
        sp = RESULTS_DIR / new_dir_name / "summary.json"
        if sp.exists():
            summary_data = json.loads(sp.read_text())

    mode_stats: dict = {}
    if summary_data:
        for ms in summary_data.get("mode_stats", []):
            mode_stats[ms["mode"]] = {
                "brtr": ms["brtr"],
                "successful": ms["successful_runs"],
                "total": ms["total_runs"],
                "ci": [ms.get("brtr_ci_lower"), ms.get("brtr_ci_upper")],
                "avg_duration_s": ms.get("avg_duration_seconds"),
            }

    return {
        "model_id": model_id,
        "api_key_env": api_key_env,
        "duration_seconds": round(duration, 1),
        "exit_code": proc.returncode,
        "modes_run": modes,
        "mode_stats": mode_stats,
        "results_dir": new_dir_name,
        "succeeded": proc.returncode == 0 and bool(summary_data),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--tasks-glob", default="quixbugs_*")
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Subset of model IDs to run (default: all 5 pre-registered)",
    )
    args = parser.parse_args()

    if not CONFIG_PATH.exists():
        raise SystemExit(f"Config bulunamadi: {CONFIG_PATH}")

    tasks = discover_tasks(args.tasks_glob)
    if not tasks:
        raise SystemExit(f"Hicbir gorev bulunamadi (glob: {args.tasks_glob})")

    models_to_run = MODELS
    if args.models:
        models_to_run = [(m, e) for m, e in MODELS if m in args.models]
        if not models_to_run:
            raise SystemExit(f"Belirtilen modeller MODELS listesinde yok: {args.models}")

    env = os.environ.copy()
    env["NVIDIA_API_KEY"] = get_nvidia_key()
    env["CLAUDE_CODE_KEY"] = "claude-code"

    aggregate = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "tasks": tasks,
        "runs_per_task": args.runs,
        "concurrency": args.concurrency,
        "modes_default": ALL_MODES,
        "exclusions": MODEL_MODE_EXCLUSIONS,
        "models": [],
    }

    try:
        for model_id, api_key_env in models_to_run:
            result = run_model(
                model_id,
                api_key_env,
                env,
                runs_per_task=args.runs,
                concurrency=args.concurrency,
                tasks=tasks,
            )
            aggregate["models"].append(result)
            FULL_OUTPUT.write_text(
                json.dumps(aggregate, indent=2, ensure_ascii=False)
            )
    finally:
        restore_config()

    aggregate["finished_at"] = datetime.now().isoformat(timespec="seconds")
    FULL_OUTPUT.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False))

    print(f"\n\n{'=' * 90}")
    print("  TAM KOSU FINAL RAPOR")
    print(f"{'=' * 90}")
    header = f"{'Model':<48}{'Sure':>9}{'BRTR (B/A/Ad)':>26}"
    print(header)
    print("-" * 90)
    for r in aggregate["models"]:
        ms = r["mode_stats"]

        def pct(mode: str) -> str:
            if mode in ms and ms[mode]["total"] > 0:
                return f"{ms[mode]['brtr'] * 100:.0f}%"
            return "—"

        brtr = f"{pct('baseline')}/{pct('agentic')}/{pct('adaptive')}"
        name = r["model_id"][:46]
        mins = r["duration_seconds"] / 60
        print(f"{name:<48}{mins:>7.1f}m{brtr:>26}")

    print(f"\nTam rapor: {FULL_OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
