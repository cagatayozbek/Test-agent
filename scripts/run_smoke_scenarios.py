"""Run the five broader-smoke scenarios in sequence and print a summary.

All five scenarios test the `deep` pipeline mode across different providers
and models — Claude CLI for tiers 1-2 and Together.ai for the OSS tiers 3-5.

Scenarios:
  sc1: Claude haiku   — deep — quixbugs_bitcount
  sc2: Claude sonnet  — deep — quixbugs_is_valid_parenthesization
  sc3: Together Llama-3.3-70B — deep — humanevalfix_026
  sc4: Together DeepSeek-V3   — deep — mbpp_mutation_001
  sc5: Together gpt-oss-120b  — deep — quixbugs_gcd

Required env: CLAUDE_CODE_KEY (any value triggers the Claude CLI provider),
              TOGETHER_API_KEY (any tgp_ key).
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

SCENARIOS = [
    ("sc1", "bugtest_smoke_sc1_haiku_deep.yaml"),
    ("sc2", "bugtest_smoke_sc2_sonnet_deep.yaml"),
    ("sc3", "bugtest_smoke_sc3_llama_deep.yaml"),
    ("sc4", "bugtest_smoke_sc4_deepseek_deep.yaml"),
    ("sc5", "bugtest_smoke_sc5_gptoss_deep.yaml"),
]


def _latest_run_dir(experiment_name: str) -> Path | None:
    matches = sorted(
        (p for p in RESULTS_DIR.iterdir() if p.is_dir() and p.name.startswith(experiment_name)),
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
            f"    {ms['mode']:<10} BRTR={ms['brtr']:.0%}  "
            f"({ms['successful_runs']}/{ms['total_runs']})  "
            f"avg_dur={ms['avg_duration_seconds']:.1f}s  "
            f"tok={int(ms['avg_prompt_tokens'])}/{int(ms['avg_completion_tokens'])}"
        )
    return "\n".join(lines)


def main() -> int:
    if not os.environ.get("CLAUDE_CODE_KEY"):
        os.environ["CLAUDE_CODE_KEY"] = "claude-code"
    if not os.environ.get("TOGETHER_API_KEY"):
        print("ERROR: TOGETHER_API_KEY env var is required for scenarios 3-5.",
              file=sys.stderr)
        return 2

    results: list[tuple[str, str, float, int]] = []
    overall_start = time.perf_counter()

    for tag, yaml_name in SCENARIOS:
        yaml_path = REPO_ROOT / yaml_name
        if not yaml_path.exists():
            print(f"[{tag}] MISSING YAML: {yaml_path}", file=sys.stderr)
            results.append((tag, "MISSING", 0.0, 1))
            continue

        print(f"\n{'=' * 70}\n[{tag}] Running {yaml_name}\n{'=' * 70}")
        t0 = time.perf_counter()
        rc = subprocess.run(
            [sys.executable, "-W", "ignore", "-m", "bugtest", str(yaml_path)],
            cwd=REPO_ROOT,
        ).returncode
        dur = time.perf_counter() - t0
        results.append((tag, yaml_name, dur, rc))
        print(f"[{tag}] exit={rc} ({dur:.1f}s)")

    overall_dur = time.perf_counter() - overall_start

    print(f"\n{'#' * 70}\n# BROADER SMOKE SUMMARY  (total {overall_dur/60:.1f} min)\n{'#' * 70}")
    for tag, yaml_name, dur, rc in results:
        try:
            with (REPO_ROOT / yaml_name).open("r", encoding="utf-8") as f:
                exp_name = yaml.safe_load(f)["experiment"]["name"]
        except Exception as e:
            exp_name = "?"
            print(f"  (could not read experiment.name from {yaml_name}: {e})")
        status = "OK" if rc == 0 else f"FAIL(rc={rc})"
        print(f"\n[{tag}] {status}  yaml={yaml_name}  shell_duration={dur:.1f}s")
        print(_summarize(exp_name))

    return 0 if all(rc == 0 for _, _, _, rc in results) else 1


if __name__ == "__main__":
    sys.exit(main())
