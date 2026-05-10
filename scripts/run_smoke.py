"""Run bugtest pipeline with NVIDIA_API_KEY pulled from run_adaptive_all.py.

This avoids re-hardcoding the key in this script while still allowing
unattended smoke-test runs. The key already exists in run_adaptive_all.py.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTIVE_RUNNER = REPO_ROOT / "run_adaptive_all.py"
CONFIG_PATH = REPO_ROOT / "bugtest_config.yaml"


def get_nvidia_key() -> str:
    if env_key := os.environ.get("NVIDIA_API_KEY"):
        return env_key
    text = ADAPTIVE_RUNNER.read_text(encoding="utf-8")
    match = re.search(r'NVIDIA_API_KEY"\]\s*=\s*"(nvapi-[A-Za-z0-9_\-]+)"', text)
    if not match:
        raise SystemExit(
            "NVIDIA_API_KEY ortamda yok ve run_adaptive_all.py icinden de okunamadi"
        )
    return match.group(1)


def main() -> int:
    env = os.environ.copy()
    env["NVIDIA_API_KEY"] = get_nvidia_key()
    env["CLAUDE_CODE_KEY"] = "claude-code"

    cmd = [sys.executable, "-W", "ignore", "-m", "bugtest", str(CONFIG_PATH)]
    print(f"Calistiriliyor: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, cwd=REPO_ROOT)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
