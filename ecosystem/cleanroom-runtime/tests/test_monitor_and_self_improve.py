from lucifer_runtime.cli import main


def test_monitor_command_outputs_panel(tmp_path, capsys):
    assert main(['--workspace', str(tmp_path), 'write', 'notes.txt', 'hello']) == 0
    capsys.readouterr()
    assert main(['--workspace', str(tmp_path), 'monitor']) == 0
    out = capsys.readouterr().out
    assert 'ARC Lucifer Monitor' in out
    assert 'known_files' in out
    assert 'notes.txt' in out


def test_self_improve_analyze_outputs_targets(tmp_path, capsys):
    assert main(['--workspace', str(tmp_path), 'self-improve', 'analyze']) == 0
    out = capsys.readouterr().out
    assert 'targets' in out
    assert 'benchmarks_missing' in out
    assert 'model_path_unvalidated' in out
