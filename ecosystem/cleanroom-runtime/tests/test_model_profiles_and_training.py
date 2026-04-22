from __future__ import annotations

import json
from pathlib import Path

from lucifer_runtime import cli


def test_model_profile_register_activate_and_compare(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main([
        '--workspace', str(tmp_path),
        'model', 'register-profile', 'local-dev',
        '--backend-type', 'gguf_local',
        '--binary-path', '/tmp/llamafile',
        '--model-path', '/tmp/model.gguf',
        '--notes', 'dev profile',
        '--training-ready',
        '--activate',
    ]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['active_profile'] == 'local-dev'

    assert cli.main(['--workspace', str(tmp_path), 'model', 'profiles']) == 0
    profiles = json.loads(capsys.readouterr().out)
    assert profiles['profiles'][0]['name'] == 'local-dev'

    assert cli.main(['--workspace', str(tmp_path), 'model', 'compare-profiles', 'local-dev']) == 0
    compare = json.loads(capsys.readouterr().out)
    assert compare['profiles'][0]['backend_type'] == 'gguf_local'


def test_training_exports_jsonl(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(['--workspace', str(tmp_path), 'write', 'notes.txt', 'hello']) == 0
    _ = capsys.readouterr()

    supervised = tmp_path / 'corpus.jsonl'
    prefs = tmp_path / 'prefs.jsonl'
    assert cli.main(['--workspace', str(tmp_path), 'train', 'export-supervised', '--output', str(supervised)]) == 0
    sup = json.loads(capsys.readouterr().out)
    assert Path(sup['output_path']).exists()
    assert supervised.read_text(encoding='utf-8').strip() != ''

    assert cli.main(['--workspace', str(tmp_path), 'train', 'export-preferences', '--output', str(prefs)]) == 0
    pref = json.loads(capsys.readouterr().out)
    assert Path(pref['output_path']).exists()
