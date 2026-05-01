"""Run adaptive mode for remaining models (skip 8B)."""

import subprocess
import sys
from pathlib import Path

import yaml

MODELS = [
    "mistralai/mistral-medium-3.5-128b",
    "meta/llama-4-maverick-17b-128e-instruct",
    "openai/gpt-oss-120b",
]

config_path = Path("bugtest_config.yaml")

for model in MODELS:
    print(f"\n{'='*60}")
    print(f"MODEL: {model}")
    print(f"{'='*60}")

    with config_path.open("r") as f:
        config = yaml.safe_load(f)
    config["model"]["model_id"] = model
    with config_path.open("w") as f:
        yaml.dump(config, f, default_flow_style=False)

    result = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "bugtest", str(config_path)],
        env={"NVIDIA_API_KEY": "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",
             "PATH": "/usr/bin:/usr/local/bin:/Applications/Xcode.app/Contents/Developer/usr/bin"},
    )

    status = "OK" if result.returncode == 0 else "FAILED"
    print(f"\n>>> {model}: {status}")

print("\n\nALL MODELS COMPLETE")
