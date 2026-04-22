from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*parts: str, expect_ok: bool = True) -> dict:
    proc = subprocess.run([sys.executable, *parts], cwd=ROOT, capture_output=True, text=True)
    if expect_ok and proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


def test_backend_check_runs_for_heuristic_smoke() -> None:
    data = run("scripts/execution/check_local_backend.py", "--adapter", "heuristic")
    assert data["health"]["ok"] is True
    assert data["smoke"]["ok"] is True


def test_backend_check_rejects_heuristic_when_live_backend_required() -> None:
    data = run("scripts/execution/check_local_backend.py", "--adapter", "heuristic", "--require-live-backend", expect_ok=False)
    assert data["ok"] is False


def test_release_bundle_builds() -> None:
    data = run("scripts/execution/generate_release_bundle.py")
    assert data["ok"] is True
    assert (ROOT / data["bundle"]).exists()


def test_model_card_generation_runs() -> None:
    data = run("scripts/execution/generate_model_card.py", "--model-name", "heuristic_ci", "--adapter", "heuristic")
    assert data["ok"] is True
    assert (ROOT / data["model_card"]).exists()
