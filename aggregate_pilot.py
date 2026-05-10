"""Aggregate per-model bugsinpy pilot summaries into a single CSV/markdown report.

Reads results/bugsinpy_pilot_*/summary.json and produces:
  - results/aggregate_<timestamp>.csv     (one row per model×mode)
  - results/aggregate_<timestamp>.md      (human-readable comparison table)
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"


def load_summaries() -> list[dict]:
    rows = []
    for run_dir in sorted(RESULTS.glob("bugsinpy_pilot_*")):
        summary_file = run_dir / "summary.json"
        if not summary_file.exists():
            continue
        data = json.loads(summary_file.read_text(encoding="utf-8"))
        model = data.get("model_id", run_dir.name)
        for ms in data.get("mode_stats", []):
            rows.append({
                "model": model,
                "mode": ms["mode"],
                "total_runs": ms["total_runs"],
                "successful_runs": ms["successful_runs"],
                "brtr": ms["brtr"],
                "ci_lower": ms.get("brtr_ci_lower", 0),
                "ci_upper": ms.get("brtr_ci_upper", 0),
                "avg_attempts_to_success": ms.get("avg_attempts_to_success") or 0,
                "avg_prompt_tokens": ms.get("avg_prompt_tokens", 0),
                "avg_completion_tokens": ms.get("avg_completion_tokens", 0),
                "avg_duration_seconds": ms.get("avg_duration_seconds", 0),
                "total_prompt_tokens": ms.get("total_prompt_tokens", 0),
                "total_completion_tokens": ms.get("total_completion_tokens", 0),
                "total_duration_seconds": ms.get("total_duration_seconds", 0),
                "total_cost_usd": ms.get("total_cost_usd", 0),
                "avg_cost_per_run_usd": ms.get("avg_cost_per_run_usd", 0),
                "avg_cost_per_success_usd": ms.get("avg_cost_per_success_usd") or 0,
                "run_dir": run_dir.name,
            })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        path.write_text("# no data\n", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_markdown(rows: list[dict], path: Path) -> None:
    if not rows:
        path.write_text("# no data\n", encoding="utf-8")
        return
    lines = [
        "# BugsInPy Pilot — Aggregate",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "| Model | Mode | BRTR | 95% CI | OK/Total | Avg Attempts | Avg Tokens | Avg Dur | Total Tokens | Total Dur | Total $ | $/run | $/OK |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        ci = f"[{r['ci_lower']:.0%}, {r['ci_upper']:.0%}]"
        toks_avg = f"{r['avg_prompt_tokens']:.0f}+{r['avg_completion_tokens']:.0f}"
        toks_tot = f"{r['total_prompt_tokens']:,}+{r['total_completion_tokens']:,}"
        cost_per_ok = f"${r['avg_cost_per_success_usd']:.4f}" if r['avg_cost_per_success_usd'] else "—"
        lines.append(
            f"| {r['model']} | {r['mode']} | {r['brtr']:.1%} | {ci} | "
            f"{r['successful_runs']}/{r['total_runs']} | "
            f"{r['avg_attempts_to_success']:.1f} | {toks_avg} | {r['avg_duration_seconds']:.1f}s | "
            f"{toks_tot} | {r['total_duration_seconds']:.0f}s | "
            f"${r['total_cost_usd']:.4f} | ${r['avg_cost_per_run_usd']:.4f} | {cost_per_ok} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    rows = load_summaries()
    if not rows:
        print("No bugsinpy_pilot_* summaries found in results/")
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = RESULTS / f"aggregate_{ts}.csv"
    md_path = RESULTS / f"aggregate_{ts}.md"
    write_csv(rows, csv_path)
    write_markdown(rows, md_path)
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print()
    print(md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
