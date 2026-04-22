from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_train_functioning_model_artifact_exists(tmp_path: Path) -> None:
    candidate = 'pytest_functional'
    proc = subprocess.run([sys.executable, 'scripts/training/train_exemplar_candidate.py', '--candidate', candidate], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    artifact = ROOT / 'exports' / 'candidates' / candidate / 'exemplar_train' / 'exemplar_model.json'
    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding='utf-8'))
    assert payload['model_type'] == 'local_exemplar'
    assert payload['record_count'] > 0


def test_exemplar_adapter_benchmark_run(tmp_path: Path) -> None:
    candidate = 'pytest_functional_run'
    proc = subprocess.run([sys.executable, 'scripts/execution/run_functioning_candidate.py', '--candidate', candidate], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    scored = ROOT / 'results' / f'{candidate}_scored_outputs.json'
    assert scored.exists()
    payload = json.loads(scored.read_text(encoding='utf-8'))
    assert len(payload.get('results', [])) > 0
    assert payload.get('overall_weighted_score', 0) >= 0
