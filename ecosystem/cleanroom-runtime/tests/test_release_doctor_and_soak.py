from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from lucifer_runtime import cli


def _load_soak_module():
    script_path = Path(__file__).resolve().parents[1] / 'scripts' / 'soak.py'
    spec = importlib.util.spec_from_file_location('soak', script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_doctor_release_gate_detects_repo_files(tmp_path, monkeypatch, capsys):
    repo = tmp_path / 'repo'
    (repo / 'src').mkdir(parents=True)
    (repo / 'docs').mkdir(parents=True)
    (repo / 'scripts').mkdir(parents=True)
    (repo / '.github' / 'workflows').mkdir(parents=True)
    (repo / 'pyproject.toml').write_text('[project]\nname = "demo"\n', encoding='utf-8')
    (repo / 'README.md').write_text('# demo\n', encoding='utf-8')
    (repo / 'docs' / 'production_readiness.md').write_text('ok\n', encoding='utf-8')
    (repo / 'scripts' / 'smoke.sh').write_text('#!/usr/bin/env bash\n', encoding='utf-8')
    (repo / 'scripts' / 'release_check.sh').write_text('#!/usr/bin/env bash\n', encoding='utf-8')
    (repo / 'scripts' / 'version_audit.py').write_text('print("ok")\n', encoding='utf-8')
    (repo / '.github' / 'workflows' / 'ci.yml').write_text('name: ci\n', encoding='utf-8')
    (repo / '.github' / 'workflows' / 'release-gate.yml').write_text('name: release\n', encoding='utf-8')

    monkeypatch.chdir(repo)
    assert cli.main(['--workspace', str(repo), 'doctor', '--release-gate']) == 0
    payload = json.loads(capsys.readouterr().out)
    checks = {item['name']: item for item in payload['checks']}
    assert checks['repo_root_detected']['ok'] is True
    assert checks['ci_workflow_present']['ok'] is True
    assert checks['release_workflow_present']['ok'] is True


def test_doctor_strict_fails_on_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    exit_code = cli.main(['--workspace', str(tmp_path), 'doctor', '--strict'])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload['status'] == 'error'
    assert payload['summary']['strict'] is True
    assert any(item['level'] == 'warn' and not item['ok'] for item in payload['checks'])


def test_soak_harness_emits_receipts(tmp_path):
    soak = _load_soak_module()
    result = soak.run_soak(tmp_path, iterations=3, sleep_seconds=0.0)
    assert result['status'] == 'ok'
    assert result['iterations'] == 3
    assert len(result['receipts']) == 3
    assert Path(result['db_path']).exists()
