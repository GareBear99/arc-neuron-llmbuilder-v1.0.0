from __future__ import annotations

import json
from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_inject_fault_and_adversarial_cycle(tmp_path: Path) -> None:
    _write_file(tmp_path / 'src' / 'module.py', 'def hello():\n    return 1\n')
    _write_file(tmp_path / 'README.md', 'demo\n')
    _write_file(tmp_path / 'pyproject.toml', '[build-system]\nrequires=[]\n')
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.sqlite3'), workspace_root=tmp_path)
    run = runtime.scaffold_improvement_run()
    run_id = run['run']['run_id']
    injected = runtime.inject_improvement_fault(run_id, kind='python_syntax_break', path='src/module.py', note='test fault')
    assert injected['status'] == 'ok'
    assert injected['fault_kind'] == 'python_syntax_break'
    payload = runtime.run_improvement_adversarial_cycle(
        run_id,
        kind='force_validation_failure',
        path='src/module.py',
        replacement_text='def hello():\n    return 2\n',
        start_line=1,
        end_line=2,
        rationale='exercise quarantine',
        timeout=30,
    )
    assert payload['status'] in {'completed_fallback', 'partial_fallback', 'ok'}
    state = runtime.kernel.state()
    kinds = [item.get('kind') for item in state.improvement_runs]
    assert 'self_improve_fault' in kinds
    assert 'self_improve_adversarial_cycle' in kinds
    assert state.world_model['adversarial_event_count'] >= 2


def test_fault_injection_updates_manifest(tmp_path: Path) -> None:
    _write_file(tmp_path / 'src' / 'module.py', 'def hi():\n    return 1\n')
    _write_file(tmp_path / 'README.md', 'demo\n')
    _write_file(tmp_path / 'pyproject.toml', '[build-system]\nrequires=[]\n')
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=tmp_path / 'events.sqlite3'), workspace_root=tmp_path)
    run = runtime.scaffold_improvement_run()
    run_id = run['run']['run_id']
    result = runtime.inject_improvement_fault(run_id, kind='delete_target_file', path='src/module.py')
    assert result['status'] == 'ok'
    manifest_path = tmp_path / '.arc_lucifer' / 'self_improve_runs' / run_id / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert manifest['fault_injections'][0]['fault_kind'] == 'delete_target_file'
    assert not (Path(manifest['worktree_dir']) / 'src' / 'module.py').exists()
