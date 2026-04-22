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


def test_code_edit_index_verify_and_symbol_replace(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    target = runtime.workspace_root / 'sample.py'
    target.write_text('def greet():\n    return "hi"\n', encoding='utf-8')

    index_payload = runtime.code_index('sample.py')
    assert index_payload['symbols'][0]['name'] == 'greet'

    planned = runtime.code_plan('sample.py', 'Make the function louder', symbol_name='greet')
    assert planned['target_symbol']['name'] == 'greet'
    expected_hash = planned['content_hash']

    replace_payload = runtime.code_replace_symbol(
        'sample.py',
        'greet',
        'def greet():\n    return "HELLO"',
        expected_hash=expected_hash,
    )
    assert replace_payload['status'] == 'ok'
    assert 'HELLO' in target.read_text(encoding='utf-8')

    verify_payload = runtime.code_verify('sample.py')
    assert verify_payload['all_passed'] is True
    state = runtime.kernel.state()
    assert state.code_edits
    runtime.kernel.close()


def test_self_improve_validate_and_promote(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    readme = runtime.workspace_root / 'README.md'
    readme.write_text('before\n', encoding='utf-8')

    scaffold = runtime.scaffold_improvement_run()
    run = scaffold['run']
    manifest_path = Path(run['manifest_path'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['recommended_commands'] = ['python -c "print(123)"']
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')

    worktree_readme = Path(run['worktree_dir']) / 'README.md'
    worktree_readme.write_text('after\n', encoding='utf-8')

    validated = runtime.validate_improvement_run(run['run_id'], timeout=30)
    assert validated['passed'] is True

    promoted = runtime.promote_improvement_run(run['run_id'])
    assert promoted['status'] == 'ok'
    assert readme.read_text(encoding='utf-8') == 'after\n'
    state = runtime.kernel.state()
    assert any(item.get('kind') == 'self_improve_promotion' for item in state.improvement_runs)
    runtime.kernel.close()


def test_self_improve_validate_records_argv_without_shell(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    scaffold = runtime.scaffold_improvement_run()
    run = scaffold['run']
    manifest_path = Path(run['manifest_path'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['recommended_commands'] = ['python -c "print(123)"']
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')

    validated = runtime.validate_improvement_run(run['run_id'], timeout=30)
    assert validated['passed'] is True
    assert validated['command_results'][0]['argv'] == ['python', '-c', 'print(123)']
    runtime.kernel.close()


def test_self_improve_review_blocks_protected_core_paths(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    scaffold = runtime.scaffold_improvement_run()
    run = scaffold['run']
    manifest_path = Path(run['manifest_path'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['recommended_commands'] = ['python -c "print(123)"']
    manifest['applied_patches'] = [{
        'patch_id': f"{run['run_id']}:patch:001",
        'artifact_path': str((Path(run['worktree_dir']) / 'patch.json').resolve()),
        'success': True,
        'path': 'src/arc_kernel/engine.py',
        'kind': 'replace_range',
    }]
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')

    validated = runtime.validate_improvement_run(run['run_id'], timeout=30)
    assert validated['passed'] is True

    review = runtime.review_improvement_run(run['run_id'])
    assert review['status'] == 'error'
    assert review['checks']['baseline_allows_patches'] is False
    assert review['baseline_review']['patch_reviews'][0]['baseline']['requires_override'] is True
    runtime.kernel.close()
