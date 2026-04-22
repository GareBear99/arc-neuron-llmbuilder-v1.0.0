from __future__ import annotations

import json
from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def make_runtime(tmp_path: Path) -> LuciferRuntime:
    workspace = tmp_path / 'ws'
    workspace.mkdir()
    db_path = workspace / '.arc_lucifer' / 'events.sqlite3'
    return LuciferRuntime(kernel=KernelEngine(db_path=db_path), workspace_root=workspace)


def test_generate_and_score_candidates(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    target = runtime.workspace_root / 'README.md'
    target.write_text('before\n', encoding='utf-8')
    scaffold = runtime.scaffold_improvement_run()
    run_id = scaffold['run']['run_id']
    generated = runtime.generate_improvement_candidates(run_id, path='README.md', replacement_text='after')
    assert generated['candidate_count'] >= 2
    scored = runtime.score_improvement_candidates(run_id, timeout=30)
    assert scored['status'] == 'ok'
    assert scored['scores']
    best = runtime.choose_best_improvement_candidate(run_id)
    assert best['status'] == 'ok'
    runtime.kernel.close()


def test_execute_best_candidate_can_promote(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    readme = runtime.workspace_root / 'README.md'
    readme.write_text('before\n', encoding='utf-8')
    scaffold = runtime.scaffold_improvement_run()
    run = scaffold['run']
    manifest_path = Path(run['manifest_path'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['recommended_commands'] = ['python -c "print(123)"']
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')
    runtime.generate_improvement_candidates(run['run_id'], path='README.md', replacement_text='after\n', start_line=1, end_line=1)
    runtime.score_improvement_candidates(run['run_id'], timeout=30)
    payload = runtime.execute_best_improvement_candidate(run['run_id'], timeout=30, promote=True)
    assert payload['status'] in {'ok', 'partial_fallback'}
    assert readme.read_text(encoding='utf-8') == 'after\n'
    runtime.kernel.close()
