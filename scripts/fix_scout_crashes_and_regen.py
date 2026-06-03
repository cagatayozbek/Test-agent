"""Re-run timeout-crash scout runs (raised CLI timeout) and regenerate summaries.

A "timeout crash" is a synthesized failed RunRecord (total_attempts==0,
success==False, or a TimeoutExpired error) caused by the `claude -p` subprocess
hitting its wall-clock cap — an infrastructure failure, not a model failure.
Run with DEEPTEST_CLAUDE_TIMEOUT=300 so genuinely-slow-but-valid runs complete.

Loops until no crashes remain (max passes), then rewrites each summary.json's
mode_stats from the on-disk run files so the artefact matches the fixed runs.
"""

import glob
import json
import re
from pathlib import Path

from bugtest.experiment import _compute_mode_stats, load_tasks
from bugtest.llm import create_client
from bugtest.pipeline import run_pipeline
from bugtest.models import RunRecord
from bugtest.validator import Validator

MODELS = ["haiku", "sonnet"]
MAX_PASSES = 4
val = Validator(timeout_seconds=30)
_clients = {}


def client(model):
    if model not in _clients:
        _clients[model] = create_client(model_id=model, api_key="claude-code", base_url=None)
    return _clients[model]


def is_crash(path):
    r = json.load(open(path))
    return (r.get("total_attempts") == 0 and not r["success"]) or "Timeout" in (r.get("error") or "")


def latest_dir(model):
    ds = sorted(glob.glob(f"results/benchmark_v2_{model}_100_scout_*"))
    return ds[-1] if ds else None


for model in MODELS:
    d = latest_dir(model)
    if not d:
        print(f"{model}: dir yok")
        continue
    for p in range(1, MAX_PASSES + 1):
        crashes = [f for f in glob.glob(f"{d}/runs/*/scout_run_*.json") if is_crash(f)]
        print(f"{model} pass {p}: {len(crashes)} crash", flush=True)
        if not crashes:
            break
        for f in crashes:
            tid = Path(f).parent.name
            rn = int(re.search(r"run_(\d+)", Path(f).name).group(1))
            try:
                t = load_tasks(Path("evaluation/tasks_v2"), [tid], [])[0]
                rec = run_pipeline(task=t, mode="scout", run_number=rn,
                                   llm=client(model), validator=val,
                                   max_attempts=3, model_id=model)
                Path(f).write_text(rec.model_dump_json(indent=2))
                print(f"  {model}/{tid} run{rn}: success={rec.success} dur={rec.duration_seconds}s", flush=True)
            except Exception as e:
                print(f"  RETRY-FAIL {model}/{tid} run{rn}: {str(e)[:80]}", flush=True)

    # Regenerate summary.json mode_stats from the on-disk run files.
    runs = [RunRecord.model_validate_json(Path(f).read_text())
            for f in glob.glob(f"{d}/runs/*/scout_run_*.json")]
    scout_runs = [r for r in runs if r.mode == "scout"]
    ms = _compute_mode_stats("scout", scout_runs)
    sp = Path(d) / "summary.json"
    summary = json.load(open(sp)) if sp.exists() else {}
    summary["mode_stats"] = [ms.model_dump()]
    sp.write_text(json.dumps(summary, indent=2))
    ok = sum(1 for r in scout_runs if r.success)
    print(f"{model} REGEN: BRTR {ms.brtr} ({ok}/{len(scout_runs)}) "
          f"CI[{ms.brtr_ci_lower},{ms.brtr_ci_upper}]", flush=True)

print("DONE", flush=True)
