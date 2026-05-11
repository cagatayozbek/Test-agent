"""Merge DeepSeek-V3 run results into the existing full_benchmark_summary.json.

The first Together full run produced summary entries for Llama-3.3-70B-Turbo,
gpt-oss-120b, and a broken Qwen-Coder-32B (non-serverless, all 400 errors).
This script:
  1. Loads the backup full_benchmark_summary_with_qwen_failed.json
  2. Loads the DeepSeek-V3-only run's full_benchmark_summary.json
  3. Drops the Qwen entry from the backup
  4. Appends the DeepSeek-V3 entry
  5. Writes the merged result back to full_benchmark_summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP = REPO_ROOT / "full_benchmark_summary_with_qwen_failed.json"
CURRENT = REPO_ROOT / "full_benchmark_summary.json"


def main() -> int:
    backup = json.loads(BACKUP.read_text())
    current = json.loads(CURRENT.read_text())

    deepseek_entries = [m for m in current["models"] if "DeepSeek" in m["model_id"]]
    if not deepseek_entries:
        raise SystemExit("DeepSeek entry not found in current full_benchmark_summary.json")
    if len(deepseek_entries) != 1:
        raise SystemExit(f"Expected 1 DeepSeek entry, got {len(deepseek_entries)}")
    deepseek = deepseek_entries[0]

    # Keep Llama-70B and gpt-oss-120b from backup; drop Qwen failed entry.
    kept = [m for m in backup["models"] if "Qwen" not in m["model_id"]]
    kept.append(deepseek)

    merged = dict(backup)
    merged["models"] = kept
    merged["started_at"] = backup["started_at"]
    merged["finished_at"] = current.get("finished_at", backup.get("finished_at"))
    merged["notes"] = (
        "Original Qwen/Qwen2.5-Coder-32B-Instruct entry dropped — that model is "
        "not serverless on Together.ai and all 465 calls returned HTTP 400. "
        "Replaced with deepseek-ai/DeepSeek-V3 in a separate run."
    )

    CURRENT.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    print(f"Merged: {len(kept)} models in full_benchmark_summary.json")
    for m in kept:
        ms = m["mode_stats"]
        def pct(mode):
            if mode in ms and ms[mode]["total"] > 0:
                return f"{ms[mode]['brtr'] * 100:.0f}%"
            return "—"
        print(f"  {m['model_id'][:45]:<45} B={pct('baseline')} A={pct('agentic')} Ad={pct('adaptive')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
