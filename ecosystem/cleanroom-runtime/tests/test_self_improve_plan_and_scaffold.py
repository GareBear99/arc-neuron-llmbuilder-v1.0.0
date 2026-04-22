from __future__ import annotations

import json
from pathlib import Path

from lucifer_runtime.cli import main


def test_self_improve_plan_outputs_tasks(tmp_path, capsys):
    assert main(['--workspace', str(tmp_path), 'self-improve', 'plan']) == 0
    out = capsys.readouterr().out
    assert 'task_count' in out
    assert 'benchmarks_missing' in out
    assert 'validation_steps' in out


def test_self_improve_scaffold_creates_manifest_and_worktree(tmp_path, capsys):
    # create some repo-like content to copy
    src_dir = tmp_path / 'src' / 'demo'
    src_dir.mkdir(parents=True)
    (src_dir / 'module.py').write_text('value = 1\n', encoding='utf-8')
    (tmp_path / 'README.md').write_text('# demo\n', encoding='utf-8')
    (tmp_path / 'pyproject.toml').write_text('version = "0.0.0"\n', encoding='utf-8')

    assert main(['--workspace', str(tmp_path), 'self-improve', 'scaffold']) == 0
    payload = json.loads(capsys.readouterr().out)
    run = payload['run']
    manifest_path = Path(run['manifest_path'])
    worktree_dir = Path(run['worktree_dir'])
    assert manifest_path.exists()
    assert worktree_dir.exists()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert manifest['kind'] == 'self_improve_run'
    assert manifest['task_count'] >= 1
    assert (worktree_dir / 'src' / 'demo' / 'module.py').exists()
    assert (worktree_dir / 'README.md').exists()

    assert main(['--workspace', str(tmp_path), 'state']) == 0
    state = json.loads(capsys.readouterr().out)
    assert state['state']['improvement_runs']
