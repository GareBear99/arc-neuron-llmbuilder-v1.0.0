from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_local_prompt_script_with_exemplar() -> None:
    env = os.environ.copy()
    env['COGNITION_RUNTIME_ADAPTER'] = 'exemplar'
    env['COGNITION_EXEMPLAR_ARTIFACT'] = str(ROOT / 'exports' / 'candidates' / 'darpa_functional' / 'exemplar_train' / 'artifact_manifest.json')
    proc = subprocess.run(
        ['bash', str(ROOT / 'scripts' / 'operator' / 'run_local_prompt.sh'), 'hello exemplar'],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert 'Receipt written to:' in proc.stdout


def test_benchmark_local_help_path_requires_command_template() -> None:
    env = os.environ.copy()
    env['COGNITION_RUNTIME_ADAPTER'] = 'command'
    proc = subprocess.run(
        ['bash', str(ROOT / 'scripts' / 'operator' / 'benchmark_local_model.sh')],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0
    assert 'COGNITION_COMMAND_TEMPLATE is required' in proc.stderr
