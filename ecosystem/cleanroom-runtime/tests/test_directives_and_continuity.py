from __future__ import annotations

from lucifer_runtime.runtime import LuciferRuntime


def test_directive_ledger_roundtrip(tmp_path):
    runtime = LuciferRuntime(workspace_root=tmp_path)
    created = runtime.register_directive(
        title='Preserve continuity',
        instruction='Keep running under fallback if primary cognition is unavailable.',
        priority=95,
        constraints=['no silent failure'],
        success_conditions=['fallback state preserved'],
        abort_conditions=['operator stop'],
    )
    assert created['status'] == 'ok'
    stats = runtime.directive_stats()
    assert stats['active_directive_count'] == 1
    assert stats['active_directives'][0]['title'] == 'Preserve continuity'
    completed = runtime.complete_directive(created['directive_id'])
    assert completed['status'] == 'ok'
    assert runtime.directive_stats()['active_directive_count'] == 0


def test_continuity_boot_and_heartbeat(tmp_path):
    runtime = LuciferRuntime(workspace_root=tmp_path)
    runtime.register_directive(title='Run forever', instruction='Maintain continuity.')
    booted = runtime.boot_continuity(fallback_available=True, notes='initial boot')
    assert booted['status'] == 'ok'
    assert booted['mode'] in {'primary', 'fallback'}
    heartbeat = runtime.continuity_heartbeat(mode='fallback', notes='degraded but alive')
    assert heartbeat['status'] == 'ok'
    status = runtime.continuity_status()
    assert status['watchdog']['healthy'] is True
    assert status['last_mode'] == 'fallback'


def test_state_projection_includes_directives_and_continuity(tmp_path):
    runtime = LuciferRuntime(workspace_root=tmp_path)
    runtime.register_directive(title='Archive important learning', instruction='Mirror critical learning to archive.')
    runtime.boot_continuity(fallback_available=True)
    runtime.continuity_heartbeat(notes='heartbeat')
    state = runtime.kernel.state()
    assert state.world_model['directive_count'] >= 1
    assert state.world_model['continuity_event_count'] >= 2
    assert state.world_model['active_directive_count'] >= 1
