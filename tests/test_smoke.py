from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str) -> dict:
    out = subprocess.check_output([sys.executable, script], cwd=ROOT)
    return json.loads(out.decode("utf-8"))


def test_validate_repo_ok() -> None:
    data = run(str(ROOT / "scripts" / "validate_repo.py"))
    assert data["ok"] is True


def test_dataset_counter_has_records() -> None:
    data = run(str(ROOT / "scripts" / "build_dataset.py"))
    counts = data["dataset_counts"]
    assert counts
    assert sum(counts.values()) >= 120


def test_benchmark_counter_has_tasks() -> None:
    data = run(str(ROOT / "scripts" / "run_benchmarks.py"))
    counts = data["benchmark_task_counts"]
    assert counts
    assert sum(counts.values()) >= 80
