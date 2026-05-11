"""Multi-model smoke test runner.

Her model icin: 3 gorev x 3 mod x 1 run.
Cikti: model bazinda sure + hata + BRTR.

Sonuc: smoke_summary.json + konsol tablosu.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "bugtest_config.yaml"
ADAPTIVE_RUNNER = REPO_ROOT / "run_adaptive_all.py"
RESULTS_DIR = REPO_ROOT / "results"
SMOKE_OUTPUT = REPO_ROOT / "smoke_summary.json"

TASKS = ["quixbugs_bitcount", "quixbugs_gcd", "quixbugs_flatten"]

TOGETHER_BASE_URL = "https://api.together.xyz/v1"

# (model_id, api_key_env, base_url_or_None)
MODELS: list[tuple[str, str, str | None]] = [
    # Together.ai
    ("meta-llama/Llama-3.3-70B-Instruct-Turbo", "TOGETHER_API_KEY", TOGETHER_BASE_URL),
    ("openai/gpt-oss-120b", "TOGETHER_API_KEY", TOGETHER_BASE_URL),
    ("deepseek-ai/DeepSeek-V3", "TOGETHER_API_KEY", TOGETHER_BASE_URL),
    # Claude Code CLI
    ("sonnet", "CLAUDE_CODE_KEY", None),
]


def get_nvidia_key() -> str | None:
    if k := os.environ.get("NVIDIA_API_KEY"):
        return k
    if not ADAPTIVE_RUNNER.exists():
        return None
    text = ADAPTIVE_RUNNER.read_text(encoding="utf-8")
    match = re.search(r'NVIDIA_API_KEY"\]\s*=\s*"(nvapi-[A-Za-z0-9_\-]+)"', text)
    return match.group(1) if match else None


def get_together_key() -> str | None:
    return os.environ.get("TOGETHER_API_KEY") or None


def write_config_for(model_id: str, api_key_env: str, base_url: str | None) -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text())
    config["model"]["model_id"] = model_id
    config["model"]["api_key_env"] = api_key_env
    config["model"]["base_url"] = base_url
    config["experiment"]["runs_per_task"] = 1
    config["experiment"]["modes"] = ["baseline", "agentic", "adaptive"]
    config["tasks"]["include"] = list(TASKS)
    config["tasks"]["exclude"] = []
    CONFIG_PATH.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))


def restore_config() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text())
    config["model"]["model_id"] = "sonnet"
    config["model"]["api_key_env"] = "CLAUDE_CODE_KEY"
    config["model"]["base_url"] = None
    config["experiment"]["runs_per_task"] = 3
    config["experiment"]["modes"] = ["baseline", "agentic", "adaptive"]
    config["tasks"]["include"] = []
    config["tasks"]["exclude"] = []
    CONFIG_PATH.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))


def parse_errors(combined: str) -> list[str]:
    """Cikti satirlarindan hata/exception izlerini cikar."""
    out: list[str] = []
    for line in combined.splitlines():
        s = line.strip()
        if not s:
            continue
        if (
            "ERROR:" in s
            or "Traceback" in s
            or s.startswith("Exception")
            or "validation error" in s
            or "FAIL" in s and "attempts" in s
        ):
            out.append(s[:300])
    return out


def run_model(model_id: str, api_key_env: str, base_url: str | None, env: dict) -> dict:
    write_config_for(model_id, api_key_env, base_url)

    print(f"\n{'=' * 70}")
    print(f"  MODEL: {model_id}")
    print(f"{'=' * 70}")

    pre_dirs = (
        {d.name for d in RESULTS_DIR.iterdir()} if RESULTS_DIR.exists() else set()
    )

    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "bugtest", str(CONFIG_PATH)],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    duration = time.time() - t0

    if proc.stdout:
        print(proc.stdout[-1500:])
    if proc.stderr:
        print("STDERR:", proc.stderr[-300:])

    errors = parse_errors((proc.stdout or "") + "\n" + (proc.stderr or ""))

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
                "avg_duration_s": ms.get("avg_duration_seconds"),
            }

    return {
        "model_id": model_id,
        "api_key_env": api_key_env,
        "base_url": base_url,
        "duration_seconds": round(duration, 1),
        "exit_code": proc.returncode,
        "error_count": len(errors),
        "errors": errors[:15],
        "mode_stats": mode_stats,
        "results_dir": new_dir_name,
        "succeeded": proc.returncode == 0 and bool(summary_data),
    }


def main() -> int:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Config bulunamadi: {CONFIG_PATH}")

    env = os.environ.copy()
    env["CLAUDE_CODE_KEY"] = "claude-code"
    if nv := get_nvidia_key():
        env["NVIDIA_API_KEY"] = nv
    if tg := get_together_key():
        env["TOGETHER_API_KEY"] = tg

    available_envs = {k for k in ("NVIDIA_API_KEY", "TOGETHER_API_KEY", "CLAUDE_CODE_KEY") if env.get(k)}
    models_to_run = [(m, e, b) for m, e, b in MODELS if e in available_envs]
    skipped = [(m, e) for m, e, _ in MODELS if e not in available_envs]
    if skipped:
        print("Skipping (no API key):")
        for m, e in skipped:
            print(f"  - {m} (needs {e})")
    if not models_to_run:
        raise SystemExit("Hicbir modelin API key'i bulunamadi")

    aggregate: dict = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "tasks": TASKS,
        "runs_per_task": 1,
        "modes": ["baseline", "agentic", "adaptive"],
        "models": [],
    }

    try:
        for model_id, api_key_env, base_url in models_to_run:
            result = run_model(model_id, api_key_env, base_url, env)
            aggregate["models"].append(result)
            SMOKE_OUTPUT.write_text(
                json.dumps(aggregate, indent=2, ensure_ascii=False)
            )
    finally:
        restore_config()

    aggregate["finished_at"] = datetime.now().isoformat(timespec="seconds")
    SMOKE_OUTPUT.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False))

    print(f"\n\n{'=' * 90}")
    print("  SMOKE TEST FINAL RAPOR")
    print(f"{'=' * 90}")
    header = f"{'Model':<48}{'Sure':>9}{'Errs':>6}{'BRTR (B/A/Ad)':>22}"
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
        print(
            f"{name:<48}{r['duration_seconds']:>7.1f}s{r['error_count']:>6}{brtr:>22}"
        )

    print(f"\nTam rapor: {SMOKE_OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
