"""Run adaptive mode for ALL models (with test_hint context)."""

import os
import subprocess
import sys
from pathlib import Path

import yaml

# (model_id, api_key_env)
MODELS = [
    # NVIDIA models only (Claude already completed)
    ("meta/llama-3.3-70b-instruct", "NVIDIA_API_KEY"),
    ("meta/llama-4-maverick-17b-128e-instruct", "NVIDIA_API_KEY"),
    ("mistralai/mistral-medium-3.5-128b", "NVIDIA_API_KEY"),
    ("openai/gpt-oss-120b", "NVIDIA_API_KEY"),
    ("meta/llama-3.1-8b-instruct", "NVIDIA_API_KEY"),
]

config_path = Path("bugtest_config.yaml")

for model_id, api_key_env in MODELS:
    print(f"\n{'='*60}")
    print(f"MODEL: {model_id}")
    print(f"{'='*60}")

    with config_path.open("r") as f:
        config = yaml.safe_load(f)
    config["model"]["model_id"] = model_id
    config["model"]["api_key_env"] = api_key_env
    config["experiment"]["modes"] = ["adaptive"]
    with config_path.open("w") as f:
        yaml.dump(config, f, default_flow_style=False)

    env = os.environ.copy()
    env["CLAUDE_CODE_KEY"] = "claude-code"
    env["NVIDIA_API_KEY"] = "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"

    result = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "bugtest", str(config_path)],
        env=env,
    )

    status = "OK" if result.returncode == 0 else "FAILED"
    print(f"\n>>> {model_id}: {status}")

print("\n\nALL MODELS COMPLETE")
