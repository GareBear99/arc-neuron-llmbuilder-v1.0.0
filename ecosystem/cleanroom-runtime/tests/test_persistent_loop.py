from pathlib import Path

from arc_kernel.engine import KernelEngine
from lucifer_runtime.runtime import LuciferRuntime
from cognition_services.goal_engine import GoalEngine
from cognition_services.persistent_loop import PersistentLoop


def test_persistent_loop_completes_goal_and_updates_world_state(tmp_path: Path):
    runtime = LuciferRuntime(KernelEngine(db_path=tmp_path / "events.db"), workspace_root=tmp_path)
    goals = GoalEngine()
    goals.add_goal("list the current files", priority=100)
    loop = PersistentLoop(goal_engine=goals)

    tick = loop.tick(runtime)

    assert tick.goal == "list the current files"
    assert tick.action["status"] == "approve"
    assert tick.world_state["facts"]["last_goal"] == "list the current files"
    assert tick.world_state["facts"]["last_branch_count"] == 2
    assert goals.current_goal() is None
