from __future__ import annotations

import json
from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def make_runtime(tmp_path: Path) -> LuciferRuntime:
    workspace = tmp_path / 'ws'
    workspace.mkdir()
    db_path = workspace / '.arc_lucifer' / 'events.sqlite3'
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=db_path), workspace_root=workspace)
    return runtime


def test_apply_patch_records_improvement_run_event(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    readme = runtime.workspace_root / 'README.md'
    readme.write_text('before\n', encoding='utf-8')

    scaffold = runtime.scaffold_improvement_run()
    run_id = scaffold['run']['run_id']
    payload = runtime.apply_improvement_patch(
        run_id,
        path='README.md',
        replacement_text='after\n',
        start_line=1,
        end_line=1,
        rationale='Update sandbox readme.',
    )
    assert payload['status'] == 'ok'
    artifact = Path(payload['artifact_path'])
    assert artifact.exists()
    state = runtime.kernel.state()
    assert any(item.get('kind') == 'self_improve_patch' for item in state.improvement_runs)
    runtime.kernel.close()


def test_execute_cycle_validates_and_quarantines_on_failure(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    src = runtime.workspace_root / 'src'
    src.mkdir()
    module = src / 'sample.py'
    module.write_text('def ok():\n    return 1\n', encoding='utf-8')

    scaffold = runtime.scaffold_improvement_run()
    run = scaffold['run']
    manifest_path = Path(run['manifest_path'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['recommended_commands'] = ['python -m py_compile src/sample.py']
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')

    payload = runtime.execute_improvement_cycle(
        run['run_id'],
        path='src/sample.py',
        replacement_text='def ok(:\n    return 1\n',
        start_line=1,
        end_line=2,
        validate=True,
        promote=True,
    )
    assert payload['patch']['success'] is False or payload['validation']['passed'] is False
    assert payload['status'] in {'ok', 'partial_fallback'}
    assert 'quarantine' in payload
    state = runtime.kernel.state()
    assert any(item.get('kind') == 'self_improve_cycle' for item in state.improvement_runs)
    runtime.kernel.close()
