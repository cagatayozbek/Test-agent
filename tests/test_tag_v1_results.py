"""Verify the v1.x retro-tagger is idempotent and only touches record dicts."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.tag_v1_results import _is_recordlike, _tag_in_place, V1_TAG


def test_runrecord_shape_is_recordlike():
    assert _is_recordlike({"task_id": "t", "mode": "deep", "attempts": []}) is True


def test_summary_shape_is_recordlike():
    assert _is_recordlike(
        {"experiment_name": "x", "mode_stats": []}
    ) is True


def test_random_dict_is_not_recordlike():
    assert _is_recordlike({"hello": "world"}) is False
    assert _is_recordlike(["task_id", "mode", "attempts"]) is False


def test_tagging_is_idempotent():
    data = {"task_id": "t", "mode": "deep", "attempts": [], "prompt_version": "v1.x"}
    patched = _tag_in_place(data)
    assert patched == 0
    assert data["prompt_version"] == "v1.x"


def test_nested_records_are_tagged():
    data = {
        "experiment_name": "x",
        "mode_stats": [],
        "raw_records": [
            {"task_id": "a", "mode": "deep", "attempts": []},
            {"task_id": "b", "mode": "baseline", "attempts": []},
        ],
    }
    patched = _tag_in_place(data)
    # 1 outer summary + 2 inner runs
    assert patched == 3
    assert data["prompt_version"] == V1_TAG
    assert data["raw_records"][0]["prompt_version"] == V1_TAG
    assert data["raw_records"][1]["prompt_version"] == V1_TAG


def test_non_record_keys_left_alone():
    data = {
        "task_id": "t", "mode": "deep", "attempts": [],
        "config": {"model": "sonnet", "temperature": 0.7},
    }
    _tag_in_place(data)
    # Config sub-dict must not gain a prompt_version
    assert "prompt_version" not in data["config"]


def test_dry_run_does_not_write(tmp_path: Path):
    """End-to-end smoke: writing a synthetic v1 results tree and running
    the script in dry mode must leave bytes untouched."""
    target = tmp_path / "results" / "x" / "summary.json"
    target.parent.mkdir(parents=True)
    body = json.dumps({
        "experiment_name": "x", "model_id": "m", "timestamp": "t",
        "total_tasks": 0, "runs_per_task": 0, "max_attempts": 0,
        "mode_stats": [], "task_stats": [],
    }, indent=2)
    target.write_text(body, encoding="utf-8")

    import subprocess
    import sys
    proj_root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.tag_v1_results", "--root", str(tmp_path / "results")],
        capture_output=True, text=True, cwd=str(proj_root),
    )
    assert proc.returncode == 0
    assert "WOULD-PATCH" in proc.stdout
    # File contents unchanged in dry mode
    assert target.read_text(encoding="utf-8") == body
