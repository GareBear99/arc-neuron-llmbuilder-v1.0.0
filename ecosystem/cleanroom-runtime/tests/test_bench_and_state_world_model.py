from lucifer_runtime.cli import main


def test_bench_command_runs(tmp_path, capsys):
    rc = main(['--workspace', str(tmp_path), 'bench'])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"suite": "smoke"' in out
    assert '"pass_rate"' in out


def test_state_contains_world_model(tmp_path, capsys):
    assert main(['--workspace', str(tmp_path), 'write', 'notes.txt', 'hello']) == 0
    capsys.readouterr()
    assert main(['--workspace', str(tmp_path), 'state']) == 0
    out = capsys.readouterr().out
    assert '"world_model"' in out
    assert '"known_files"' in out
    assert 'notes.txt' in out
