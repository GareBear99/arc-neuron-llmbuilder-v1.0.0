from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime


def test_fixnet_register_records_fix_and_novelty(tmp_path: Path):
    kernel = KernelEngine()
    runtime = LuciferRuntime(kernel=kernel, workspace_root=tmp_path)

    result = runtime.fixnet_register(
        title='Validator disagreement',
        error_type='validation',
        error_signature='validator_pass_rate<1.0',
        solution='tighten validator gate and add regression test',
        summary='Consensus repair record for repeated validation misses.',
        keywords=['fixnet','validation'],
        evidence={'run':'run-1'},
        linked_run_ids=['run-1'],
        linked_proposal_ids=['proposal-1'],
    )
    assert result['status'] == 'ok'
    assert result['fix']['fix_id']
    assert result['novelty']['decision'] in {'novel','duplicate','variant'}
    state = kernel.state()
    assert state.world_model['fixnet_case_count'] == 1


def test_fixnet_embed_emits_memory_update(tmp_path: Path):
    kernel = KernelEngine()
    runtime = LuciferRuntime(kernel=kernel, workspace_root=tmp_path)
    result = runtime.fixnet_register(
        title='Promotion failure dossier',
        error_type='promotion',
        error_signature='promotion_denied',
        solution='strengthen evidence bundle before promote',
        auto_embed=True,
    )
    fix_id = result['fix']['fix_id']
    embedded = runtime.fixnet_embed(fix_id)
    assert embedded['status'] == 'ok'
    state = kernel.state()
    assert state.world_model['fixnet_archive_count'] >= 1
    assert any(u.get('kind') == 'fixnet_embedded_archive' for u in state.memory_updates)
