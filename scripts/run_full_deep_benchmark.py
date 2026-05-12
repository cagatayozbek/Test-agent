"""Run the full deep-mode benchmark across 4 models on the PREREG_V2 25-task set.

Per-pre-registration parameters: deep mode only, runs_per_task=3, concurrency=8,
max_attempts=3, temperature=0.7. Model order is chosen so the cheapest
Together.ai runs go first (fastest feedback if anything is misconfigured), then
the slow Claude CLI runs at the end.

Required env: CLAUDE_CODE_KEY (any non-empty value for the CLI provider),
              TOGETHER_API_KEY (a tgp_ key for sc3/sc4).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"

# Cheapest-first order so configuration mistakes surface in minutes, not hours.
BENCHMARKS = [
    ("deepseek", "benchmark_deep_deepseek.yaml"),
    ("llama",    "benchmark_deep_llama.yaml"),
    ("sonnet",   "benchmark_deep_sonnet.yaml"),
    ("haiku",    "benchmark_deep_haiku.yaml"),
]


def _latest_run_dir(experiment_name: str) -> Path | None:
    matches = sorted(
        (p for p in RESULTS_DIR.iterdir()
         if p.is_dir() and p.name.startswith(experiment_name + "_")),
        key=lambda p: p.stat().st_mtime,
    )
    return matches[-1] if matches else None


def _summarize(experiment_name: str) -> str:
    run_dir = _latest_run_dir(experiment_name)
    if run_dir is None:
        return "  (no result dir found)"
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return f"  (no summary.json in {run_dir.name})"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    lines = [f"  → {run_dir.name}"]
    for ms in summary.get("mode_stats", []):
        lines.append(
            f"    {ms['mode']:<10} BRTR={ms['brtr']:.1%}  "
            f"({ms['successful_runs']}/{ms['total_runs']})  "
            f"95% CI=[{ms['brtr_ci_lower']:.1%}, {ms['brtr_ci_upper']:.1%}]  "
            f"avg_dur={ms['avg_duration_seconds']:.0f}s  "
            f"tok={int(ms['avg_prompt_tokens'])}/{int(ms['avg_completion_tokens'])}"
        )
    return "\n".join(lines)


def main() -> int:
    if not os.environ.get("CLAUDE_CODE_KEY"):
        os.environ["CLAUDE_CODE_KEY"] = "claude-code"
    if not os.environ.get("TOGETHER_API_KEY"):
        print("ERROR: TOGETHER_API_KEY env var is required.", file=sys.stderr)
        return 2

    results: list[tuple[str, str, float, int]] = []
    overall_start = time.perf_counter()

    for tag, yaml_name in BENCHMARKS:
        yaml_path = REPO_ROOT / yaml_name
        if not yaml_path.exists():
            print(f"[{tag}] MISSING YAML: {yaml_path}", file=sys.stderr)
            results.append((tag, "MISSING", 0.0, 1))
            continue

        print(f"\n{'#' * 70}\n# [{tag}] Running {yaml_name}\n{'#' * 70}", flush=True)
        t0 = time.perf_counter()
        rc = subprocess.run(
            [sys.executable, "-u", "-W", "ignore", "-m", "bugtest", str(yaml_path)],
            cwd=REPO_ROOT,
        ).returncode
        dur = time.perf_counter() - t0
        results.append((tag, yaml_name, dur, rc))
        print(f"[{tag}] exit={rc} ({dur/60:.1f} min)", flush=True)

    overall_dur = time.perf_counter() - overall_start

    print(f"\n{'#' * 70}\n# FULL DEEP BENCHMARK SUMMARY  "
          f"(total {overall_dur/60:.1f} min)\n{'#' * 70}")
    for tag, yaml_name, dur, rc in results:
        try:
            with (REPO_ROOT / yaml_name).open("r", encoding="utf-8") as f:
                exp_name = yaml.safe_load(f)["experiment"]["name"]
        except Exception:
            exp_name = "?"
        status = "OK" if rc == 0 else f"FAIL(rc={rc})"
        print(f"\n[{tag}] {status}  yaml={yaml_name}  shell={dur/60:.1f} min")
        print(_summarize(exp_name))

    return 0 if all(rc == 0 for _, _, _, rc in results) else 1


if __name__ == "__main__":
    sys.exit(main())
