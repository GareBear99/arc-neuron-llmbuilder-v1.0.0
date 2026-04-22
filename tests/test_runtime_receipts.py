from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_direct_candidate_writes_receipt(tmp_path: Path) -> None:
    receipt = tmp_path / 'receipt.json'
    artifact = ROOT / 'exports' / 'candidates' / 'darpa_functional' / 'exemplar_train' / 'exemplar_model.json'
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'execution' / 'run_direct_candidate.py'), '--adapter', 'exemplar', '--artifact', str(artifact), '--prompt', 'repair the runtime lane', '--receipt-path', str(receipt)], check=True, cwd=ROOT)
    payload = json.loads(receipt.read_text(encoding='utf-8'))
    assert payload['ok'] is True
    assert payload['adapter'] == 'exemplar'
    assert payload['prompt_hash']
    assert payload['output_preview']
