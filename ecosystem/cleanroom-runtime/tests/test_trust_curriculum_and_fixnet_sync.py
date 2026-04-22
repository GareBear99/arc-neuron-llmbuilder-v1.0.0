from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime
from lucifer_runtime.cli import main


def test_shadow_updates_trust_and_curriculum(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / 'events.db'), workspace_root=tmp_path)
    runtime.shadow_handle('list the current files', predicted_status='approve')
    trust = runtime.tool_trust_stats()
    curriculum = runtime.curriculum_stats()
    assert trust['profile_count'] >= 1
    assert any(p['tool_name'] == 'shadow_execution' for p in trust['profiles'])
    assert curriculum['theme_count'] >= 1
    state = runtime.kernel.state()
    assert state.world_model['tool_trust_profile_count'] >= 1
    assert state.world_model['curriculum_update_count'] >= 1


def test_fixnet_sync_archive_updates_live_link_metadata(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / 'events.db'), workspace_root=tmp_path)
    created = runtime.fixnet_register(
        title='Archive sync fix',
        error_type='archive',
        error_signature='archive-sync-needed',
        solution='sync metadata into embedded archive',
        auto_embed=True,
    )
    fix_id = created['fix']['fix_id']
    synced = runtime.fixnet_sync_archive(fix_id, status='retired', retirement_at='2030-01-01T00:00:00+00:00')
    assert synced['status'] == 'ok'
    assert synced['source_status'] == 'retired'
    assert synced['retirement_at'] == '2030-01-01T00:00:00+00:00'


def test_cli_trust_curriculum_and_fixnet_sync_commands(tmp_path: Path, capsys):
    assert main(['--workspace', str(tmp_path), 'trust', 'record', 'shadow_execution', '--status', 'success']) == 0
    out = capsys.readouterr().out
    assert 'shadow_execution' in out

    assert main(['--workspace', str(tmp_path), 'curriculum', 'record', '--theme', 'self_improve', '--skill', 'validation']) == 0
    out = capsys.readouterr().out
    assert 'theme_count' in out

    # seed a fix first
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / 'events2.db'), workspace_root=tmp_path)
    created = runtime.fixnet_register(title='CLI sync', error_type='archive', error_signature='cli-sync', solution='sync', auto_embed=True)
    fix_id = created['fix']['fix_id']
    assert main(['--workspace', str(tmp_path), 'fixnet', 'sync-archive', fix_id, '--status', 'retired', '--retirement-at', '2031-01-01T00:00:00+00:00']) == 0
    out = capsys.readouterr().out
    assert 'retirement_at' in out
