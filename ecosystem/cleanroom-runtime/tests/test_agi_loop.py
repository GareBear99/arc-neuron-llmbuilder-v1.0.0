from __future__ import annotations

from pathlib import Path

from arc_kernel.engine import KernelEngine
from cognition_services.agi_loop import AGILoop
from cognition_services.cognition_runtime_extension import build_cognition_core, patch_runtime
from cognition_services.world_model import WorldModel
from lucifer_runtime.runtime import LuciferRuntime


def make_runtime(tmp_path: Path) -> LuciferRuntime:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    db_path = workspace / '.arc_lucifer' / 'events.sqlite3'
    runtime = LuciferRuntime(kernel=KernelEngine(db_path=db_path), workspace_root=workspace)
    build_cognition_core(runtime)
    patch_runtime(runtime)
    return runtime


def test_agi_loop_tick_once_updates_world_and_report(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.goals.add_goal('echo hello from agi loop', compile=True)
    world = WorldModel()
    loop = AGILoop(runtime=runtime, world_model=world, max_ticks=1)

    report = loop.tick_once()

    assert report.tick == 1
    assert report.goal == 'echo hello from agi loop'
    assert report.action_status in {'approve', 'confirmed', 'idle', 'require_confirmation'}
    snap = world.snapshot()
    assert snap['facts']['agi_loop_tick'] == 1
    assert 'agi_loop_last_action' in snap['facts']
    runtime.kernel.close()


def test_agi_loop_freeze_and_thaw_respects_drift_detector(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    loop = AGILoop(runtime=runtime, world_model=WorldModel(), max_ticks=1)

    loop.freeze('operator requested pause')
    assert loop.is_frozen is True

    loop.drift_detector._drift_detected = True
    assert loop.thaw() is False
    assert loop.is_frozen is True

    loop.drift_detector._drift_detected = False
    assert loop.thaw() is True
    assert loop.is_frozen is False
    runtime.kernel.close()
