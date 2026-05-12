"""v1.x ↔ v2.0 qwen benchmark karşılaştırma raporu.

Aynı 25 task × 3 run setinde v1.x ve v2.0 deep mode sonuçlarını alır,
per-task BRTR delta + global Spearman korelasyon + token/duration/
failure-mode özetlerini bastırır.

Usage:
    python3 -m scripts.compare_v1_v2_qwen \\
        --v1 results/benchmark_deep_qwen3coder_20260512_093505 \\
        --v2 results_v2/benchmark_v2_qwen3coder_<ts>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import correlation, mean


def load_runs(root: Path, task: str) -> list[dict]:
    p = root / "runs" / task
    if not p.exists():
        return []
    return [json.loads(f.read_text()) for f in sorted(p.glob("deep_run_*.json"))]


def per_task_brtr(root: Path, tasks: list[str]) -> dict[str, float]:
    out = {}
    for t in tasks:
        runs = load_runs(root, t)
        out[t] = sum(1 for r in runs if r["success"]) / len(runs) if runs else 0.0
    return out


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman ρ with average ranks for ties."""
    def rank(vs):
        order = sorted(range(len(vs)), key=lambda i: vs[i])
        ranks = [0.0] * len(vs)
        i = 0
        while i < len(vs):
            j = i
            while j + 1 < len(vs) and vs[order[j + 1]] == vs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        return ranks

    rx, ry = rank(xs), rank(ys)
    try:
        return correlation(rx, ry)
    except Exception:
        return float("nan")


def global_summary(root: Path) -> dict:
    s = json.loads((root / "summary.json").read_text())
    deep = next((m for m in s["mode_stats"] if m["mode"] == "deep"), {})
    return deep


def aggregate_failure_modes(root: Path, tasks: list[str]) -> dict[str, int]:
    """Sum tool_failure_mode_count across all runs (v2 only — v1 didn't log)."""
    agg: dict[str, int] = {}
    for t in tasks:
        for r in load_runs(root, t):
            for a in r.get("attempts", []):
                for k, v in (a.get("tool_failure_mode_count") or {}).items():
                    agg[k] = agg.get(k, 0) + v
    return agg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1", required=True, type=Path)
    parser.add_argument("--v2", required=True, type=Path)
    args = parser.parse_args()

    cfg = (args.v2 / "config.yaml").read_text() if (args.v2 / "config.yaml").exists() else ""
    # Extract task list from v2 config so we compare exactly the same set.
    tasks_v2 = sorted(p.name for p in (args.v2 / "runs").iterdir() if p.is_dir())
    tasks_v1 = sorted(p.name for p in (args.v1 / "runs").iterdir() if p.is_dir())
    tasks = sorted(set(tasks_v1) & set(tasks_v2))
    if set(tasks_v1) != set(tasks_v2):
        print(f"WARN: task sets differ. v1-only={set(tasks_v1)-set(tasks_v2)}  "
              f"v2-only={set(tasks_v2)-set(tasks_v1)}")
    print(f"Comparing {len(tasks)} tasks present in both roots.\n")

    pt1 = per_task_brtr(args.v1, tasks)
    pt2 = per_task_brtr(args.v2, tasks)

    print(f"{'task':<42}  {'v1.x':<8}  {'v2.0':<8}  delta")
    print("-" * 78)
    rows = []
    for t in tasks:
        d = pt2[t] - pt1[t]
        rows.append((t, pt1[t], pt2[t], d))
        arrow = "↑" if d > 0 else ("↓" if d < 0 else "=")
        print(f"{t:<42}  {pt1[t]*100:5.1f}%   {pt2[t]*100:5.1f}%   {d*100:+5.1f}%  {arrow}")

    v1_vec = [pt1[t] for t in tasks]
    v2_vec = [pt2[t] for t in tasks]
    rho = spearman(v1_vec, v2_vec)

    g1 = global_summary(args.v1)
    g2 = global_summary(args.v2)

    print(f"\n--- global ---")
    print(f"v1.x: BRTR = {g1.get('brtr', 0)*100:.1f}% ({g1.get('successful_runs', 0)}/{g1.get('total_runs', 0)})  "
          f"avg_dur = {g1.get('avg_duration_seconds', 0):.1f}s  "
          f"avg_compl = {g1.get('avg_completion_tokens', 0):.0f}")
    print(f"v2.0: BRTR = {g2.get('brtr', 0)*100:.1f}% ({g2.get('successful_runs', 0)}/{g2.get('total_runs', 0)})  "
          f"avg_dur = {g2.get('avg_duration_seconds', 0):.1f}s  "
          f"avg_compl = {g2.get('avg_completion_tokens', 0):.0f}")
    print(f"\nSpearman ρ (per-task BRTR, n={len(tasks)}): {rho:.3f}")
    print(f"  (plan §9.C.2 threshold for 'ranking preserved': ρ >= 0.7)")

    print(f"\n--- v2.0 tool failure-mode aggregate ---")
    fm = aggregate_failure_modes(args.v2, tasks)
    if fm:
        for k, v in sorted(fm.items(), key=lambda kv: -kv[1]):
            print(f"  {k:<22} {v}")
    else:
        print("  (no tool failure-mode counts logged)")

    # Movement summary
    improved = [(t, d) for (t, _, _, d) in rows if d > 0]
    degraded = [(t, d) for (t, _, _, d) in rows if d < 0]
    print(f"\n--- movement ---")
    print(f"  improved (v2 > v1): {len(improved)} tasks  total ΔBRTR = +{sum(d for _, d in improved)*100:.1f}pp")
    print(f"  degraded (v2 < v1): {len(degraded)} tasks  total ΔBRTR = {sum(d for _, d in degraded)*100:.1f}pp")
    print(f"  unchanged: {len(rows) - len(improved) - len(degraded)} tasks")
    if degraded:
        print(f"\n  ⚠ degraded tasks (regression candidates):")
        for t, d in sorted(degraded, key=lambda kv: kv[1]):
            print(f"    {t}  Δ = {d*100:+.1f}pp")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
