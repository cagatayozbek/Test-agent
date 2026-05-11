"""Pilot run: first N BugsInPy tasks × {baseline, adaptive, deep} × 4 models × 1 run.

Streams progress to stdout so the user can watch it live.

Usage:
    python run_pilot_all.py            # default 30 tasks, 1 run each
    python run_pilot_all.py --limit 100 --runs 1
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "bugtest_config.yaml"
TASKS_DIR = ROOT / "evaluation" / "tasks_v2_bugsinpy"

MODELS = [
    # NVIDIA OSS first (faster, less subscription pressure)
    ("openai/gpt-oss-120b", "NVIDIA_API_KEY"),
    ("meta/llama-4-maverick-17b-128e-instruct", "NVIDIA_API_KEY"),
    # Claude CLI second (slower, uses Max subscription)
    ("sonnet", "CLAUDE_CODE_KEY"),
    ("opus", "CLAUDE_CODE_KEY"),
]

MODES = ["baseline", "adaptive", "deep"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30,
                        help="Number of tasks to include (default: 30)")
    parser.add_argument("--runs", type=int, default=3,
                        help="Runs per task per mode (default: 3)")
    parser.add_argument("--max-attempts", type=int, default=2,
                        help="Max retry attempts per task (default: 2 to keep pilot fast)")
    parser.add_argument("--models", nargs="+", default=None,
                        help="Override model list")
    parser.add_argument("--modes", nargs="+", default=None,
                        help="Override mode list")
    args = parser.parse_args()

    if not TASKS_DIR.exists():
        print(f"!! tasks dir missing: {TASKS_DIR}")
        sys.exit(2)

    candidate_dirs = [p for p in TASKS_DIR.iterdir() if p.is_dir() and (p / "buggy" / "source.py").exists()]
    # Sort by buggy source size ascending so smallest tasks run first.
    candidate_dirs.sort(key=lambda p: (p / "buggy" / "source.py").stat().st_size)
    all_tasks = [p.name for p in candidate_dirs]
    if not all_tasks:
        print("!! no tasks found")
        sys.exit(2)

    pilot_tasks = all_tasks[: args.limit]
    print(f"== {len(pilot_tasks)} pilot tasks (out of {len(all_tasks)} total, smallest-first)")

    models = MODELS
    if args.models:
        wanted = set(args.models)
        models = [(m, k) for (m, k) in MODELS if m in wanted]

    modes = args.modes or MODES

    env = os.environ.copy()
    env["CLAUDE_CODE_KEY"] = "claude-code"
    if "NVIDIA_API_KEY" not in env:
        # fall back to .env
        envfile = ROOT / ".env"
        if envfile.exists():
            for line in envfile.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

    statuses = []
    for model_id, api_key_env in models:
        print()
        print("=" * 70)
        print(f"MODEL: {model_id}   modes={modes}   tasks={len(pilot_tasks)}   runs={args.runs}")
        print("=" * 70)

        exp_name = f"bugsinpy_pilot_{model_id.replace('/', '_')}"

        # Resume: re-use the latest existing experiment dir for this model
        existing_dirs = sorted(
            (ROOT / "results").glob(f"{exp_name}_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if existing_dirs:
            experiment_id = existing_dirs[0].name
            print(f"[resume] continuing existing run: {experiment_id}")
        else:
            experiment_id = None  # let experiment.py auto-generate timestamped id

        # Patch config for this model run
        with CONFIG_PATH.open("r") as f:
            config = yaml.safe_load(f)
        config["model"]["model_id"] = model_id
        config["model"]["api_key_env"] = api_key_env
        config["experiment"]["modes"] = modes
        config["experiment"]["runs_per_task"] = args.runs
        config["retry"]["max_attempts"] = args.max_attempts
        config["experiment"]["name"] = exp_name
        if experiment_id:
            config["experiment"]["experiment_id"] = experiment_id
        else:
            config["experiment"].pop("experiment_id", None)
        config["tasks"]["dir"] = str(TASKS_DIR.relative_to(ROOT))
        config["tasks"]["include"] = pilot_tasks
        with CONFIG_PATH.open("w") as f:
            yaml.dump(config, f, default_flow_style=False)

        result = subprocess.run(
            [sys.executable, "-u", "-W", "ignore", "-m", "bugtest", str(CONFIG_PATH)],
            env=env,
            cwd=str(ROOT),
        )
        statuses.append((model_id, result.returncode))
        print(f">>> {model_id}: {'OK' if result.returncode == 0 else 'FAILED'}")

    print()
    print("=" * 70)
    print("PILOT COMPLETE")
    print("=" * 70)
    for m, rc in statuses:
        print(f"  {m:50s} {'OK' if rc == 0 else f'FAIL (rc={rc})'}")


if __name__ == "__main__":
    main()
