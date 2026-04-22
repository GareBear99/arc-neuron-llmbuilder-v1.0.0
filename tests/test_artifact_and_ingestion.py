from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_candidate_artifact_chain_runs(tmp_path):
    result = subprocess.run(
        [sys.executable, 'scripts/training/run_candidate_artifact_chain.py', '--candidate', 'testcand', '--base-model', 'base/test'],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    manifest = ROOT / 'exports' / 'candidates' / 'testcand' / 'gguf_export' / 'artifact_manifest.json'
    assert manifest.exists()
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    assert payload['candidate'] == 'testcand'
    assert payload['stage'] == 'gguf_export'


def test_supporting_repo_ingestion_from_zip(tmp_path):
    source = tmp_path / 'mini.zip'
    with zipfile.ZipFile(source, 'w') as z:
        z.writestr('mini/README.md', '# Runtime Doctrine\n\nPreserve narrow change boundaries and validate with evidence.')
        z.writestr('mini/docs/architecture.md', '# Architecture\n\nInspect before acting and surface blockers honestly.')
    result = subprocess.run(
        [sys.executable, 'scripts/build_supporting_repo_corpus.py', '--source', str(source), '--package', 'cleanroom', '--limit', '2'],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    out = ROOT / 'datasets' / 'runtime_mindshape' / 'cleanroom_seed_records.jsonl'
    assert out.exists()
    lines = [json.loads(line) for line in out.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert lines
    assert lines[0]['source_repo'] == 'cleanroom'


def test_external_lora_command_wiring(tmp_path):
    env = os.environ.copy()
    env['COGNITION_LORA_TRAIN_MODE'] = 'external'
    env['COGNITION_LORA_TRAIN_COMMAND'] = (
        f"{sys.executable} -c \"from pathlib import Path; Path(r'{tmp_path / 'ok.txt'}').write_text('done', encoding='utf-8')\""
    )
    result = subprocess.run(
        [sys.executable, 'scripts/training/train_lora_candidate.py', '--candidate', 'extcand', '--base-model', 'base/test'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    manifest = ROOT / 'exports' / 'candidates' / 'extcand' / 'lora_train' / 'artifact_manifest.json'
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    assert payload['status'] == 'external_completed'
    assert (tmp_path / 'ok.txt').exists()


def test_quantization_retention_direct_compare(tmp_path):
    fp = tmp_path / 'fp.json'
    q = tmp_path / 'q.json'
    fp.write_text(json.dumps({'overall_weighted_score': 0.9, 'results': [{'task_id': 'a', 'normalized_score': 1.0}]}), encoding='utf-8')
    q.write_text(json.dumps({'overall_weighted_score': 0.87, 'results': [{'task_id': 'a', 'normalized_score': 0.8}]}), encoding='utf-8')
    out = tmp_path / 'retention.json'
    result = subprocess.run(
        [sys.executable, 'scripts/execution/run_quantization_retention.py', '--full-precision', str(fp), '--quantized', str(q), '--threshold', '0.95', '--output', str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding='utf-8'))
    assert payload['mode'] == 'direct_compare'
    assert payload['retention_ratio'] == 0.9667
