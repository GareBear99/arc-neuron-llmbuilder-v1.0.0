from __future__ import annotations

import json
from pathlib import Path

from lucifer_runtime import cli


def test_config_init_and_show(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(['--workspace', str(tmp_path), 'config', 'init']) == 0
    out = json.loads(capsys.readouterr().out)
    config_path = Path(out['config_path'])
    assert config_path.exists()
    assert cli.main(['--workspace', str(tmp_path), 'config', 'show', '--resolved']) == 0
    show = json.loads(capsys.readouterr().out)
    assert show['config']['model']['host'] == '127.0.0.1'
    assert show['resolved']['workspace'] == str(tmp_path)


def test_doctor_and_export(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(['--workspace', str(tmp_path), 'write', 'notes.txt', 'hello']) == 0
    _ = capsys.readouterr()
    assert cli.main(['--workspace', str(tmp_path), 'doctor']) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert 'checks' in doctor
    jsonl_path = tmp_path / 'events.jsonl'
    sqlite_path = tmp_path / 'backup.sqlite3'
    assert cli.main(['--workspace', str(tmp_path), 'export', '--jsonl', str(jsonl_path), '--sqlite-backup', str(sqlite_path)]) == 0
    export = json.loads(capsys.readouterr().out)
    assert Path(export['jsonl_path']).exists()
    assert Path(export['sqlite_backup_path']).exists()
    lines = jsonl_path.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) >= 1
