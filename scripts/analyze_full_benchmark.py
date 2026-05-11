"""Post-hoc analysis of the 4-model × 31-task × 3-mode × 5-run benchmark.

Produces two tables:
  A) model × mode × difficulty BRTR (stratification — ceiling-effect kirilma kaniti)
  B) per-task agentic - baseline Delta-BRTR (which tasks the Analyzer hurts/helps)

Reads from results/<dir>/summary.json (referenced in full_benchmark_summary.json)
and metadata.json from each task. Writes the markdown tables to stdout
and to scripts/_analysis_output.md.

Usage:
    python scripts/analyze_full_benchmark.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FULL = REPO_ROOT / "full_benchmark_summary.json"
RESULTS = REPO_ROOT / "results"
TASKS_DIR = REPO_ROOT / "evaluation" / "tasks_v2"
OUTPUT_MD = REPO_ROOT / "scripts" / "_analysis_output.md"


def load_task_difficulty() -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(TASKS_DIR.glob("quixbugs_*")):
        meta = json.loads((p / "metadata.json").read_text(encoding="utf-8"))
        out[p.name] = meta.get("difficulty", "unknown")
    return out


def load_runs(results_dir_name: str) -> list[dict]:
    runs: list[dict] = []
    rd = RESULTS / results_dir_name / "runs"
    if not rd.exists():
        return runs
    for task_dir in sorted(rd.iterdir()):
        if not task_dir.is_dir():
            continue
        for f in sorted(task_dir.glob("*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            runs.append(r)
    return runs


def brtr(rs: list[dict]) -> tuple[float, int, int]:
    total = len(rs)
    succ = sum(1 for r in rs if r.get("success"))
    return (succ / total if total else 0.0, succ, total)


def main() -> int:
    diff = load_task_difficulty()
    agg = json.loads(FULL.read_text(encoding="utf-8"))

    # Load all run records per model
    model_runs: dict[str, list[dict]] = {}
    for m in agg["models"]:
        model_runs[m["model_id"]] = load_runs(m["results_dir"])

    lines: list[str] = []

    # ============ TABLE A: model x mode x difficulty ============
    lines.append("## A. Model × Mode × Difficulty BRTR\n")
    lines.append("Stratification covariate: difficulty (easy/medium/hard). "
                 "Difficulty labels are authors' attribution "
                 "(`scripts/convert_quixbugs.py:TASK_CATALOG`), assigned before "
                 "the full-benchmark run.\n")

    diff_count: dict[str, int] = defaultdict(int)
    for d in diff.values():
        diff_count[d] += 1
    lines.append(f"Task distribution: easy={diff_count.get('easy', 0)}, "
                 f"medium={diff_count.get('medium', 0)}, "
                 f"hard={diff_count.get('hard', 0)} "
                 f"(n={sum(diff_count.values())})\n")

    header = (
        "| Model | Mode | Easy | Medium | Hard |\n"
        "|---|---|---:|---:|---:|"
    )
    lines.append(header)

    for model_id, runs in model_runs.items():
        # Group by mode
        for mode in ("baseline", "agentic", "adaptive"):
            mode_runs = [r for r in runs if r.get("mode") == mode]
            if not mode_runs:
                lines.append(
                    f"| {model_id} | {mode} | — | — | — |"
                )
                continue
            row_cells = []
            for d in ("easy", "medium", "hard"):
                d_runs = [r for r in mode_runs if diff.get(r["task_id"]) == d]
                rate, succ, total = brtr(d_runs)
                if total == 0:
                    row_cells.append("—")
                else:
                    row_cells.append(f"{rate * 100:.0f}% ({succ}/{total})")
            lines.append(
                f"| {model_id} | {mode} | {row_cells[0]} | {row_cells[1]} | "
                f"{row_cells[2]} |"
            )

    # ============ TABLE B: per-task agentic Delta-BRTR ============
    lines.append("\n## B. Per-Task `agentic − baseline` Δ-BRTR\n")
    lines.append(
        "Per (task, model), Δ = BRTR(agentic) − BRTR(baseline). Negative Δ = "
        "Analyzer hurts. Sonnet column is highlighted because its agentic mode "
        "underperformed baseline by 50pp overall, and we want to localize the "
        "source.\n"
    )

    models = list(model_runs.keys())
    header_cells = ["Task", "Difficulty"] + [m.split("/")[-1][:24] for m in models]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("|" + "---|" * len(header_cells))

    task_ids = sorted({r["task_id"] for runs in model_runs.values() for r in runs})

    # Per-task per-model deltas; also accumulate worst tasks per model
    worst: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for tid in task_ids:
        row = [tid, diff.get(tid, "?")]
        for model_id in models:
            r_runs = model_runs[model_id]
            base = [r for r in r_runs if r["task_id"] == tid and r["mode"] == "baseline"]
            ag = [r for r in r_runs if r["task_id"] == tid and r["mode"] == "agentic"]
            if not base or not ag:
                row.append("—")
                continue
            b_rate, _, _ = brtr(base)
            a_rate, _, _ = brtr(ag)
            delta = a_rate - b_rate
            worst[model_id].append((tid, delta))
            sign = "+" if delta >= 0 else ""
            row.append(f"{sign}{delta * 100:.0f}pp ({b_rate * 100:.0f}→{a_rate * 100:.0f})")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n### Worst 5 tasks per model (most negative agentic Δ):\n")
    for m in models:
        deltas = sorted(worst[m], key=lambda x: x[1])[:5]
        lines.append(f"- **{m}**: " + ", ".join(
            f"{t.replace('quixbugs_', '')} ({d * 100:+.0f}pp)" for t, d in deltas
        ))

    # ============ SUMMARY: ceiling-effect break + Sonnet anomaly ============
    lines.append("\n## C. Quick observations\n")
    for model_id, runs in model_runs.items():
        hard_base = [r for r in runs if r["mode"] == "baseline" and diff.get(r["task_id"]) == "hard"]
        rate, succ, total = brtr(hard_base)
        if total > 0:
            broke = "✓ ceiling broken" if rate < 1.0 else "ceiling still 100%"
            lines.append(f"- **{model_id}** hard-baseline BRTR: "
                         f"{rate * 100:.0f}% ({succ}/{total}) — {broke}")

    out_text = "\n".join(lines) + "\n"
    OUTPUT_MD.write_text(out_text, encoding="utf-8")
    print(out_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
