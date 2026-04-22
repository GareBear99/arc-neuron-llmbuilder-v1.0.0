from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .goal_engine import GoalEngine
from .world_model import WorldModel


@dataclass
class LoopTickResult:
    goal: str | None
    action: dict[str, Any]
    world_state: dict[str, Any]


class PersistentLoop:
    def __init__(self, goal_engine: GoalEngine | None = None, world_model: WorldModel | None = None) -> None:
        self.goal_engine = goal_engine or GoalEngine()
        self.world_model = world_model or WorldModel()

    def tick(self, runtime: Any, confirm: bool = False) -> LoopTickResult:
        goal = self.goal_engine.current_goal()
        if goal is None:
            return LoopTickResult(goal=None, action={"status": "idle"}, world_state=self.world_model.snapshot())
        action = runtime.handle(goal.title, confirm=confirm)
        self.world_model.update_fact("last_goal", goal.title)
        self.world_model.update_fact("last_action_status", action.get("status"))
        if action.get("branches"):
            self.world_model.update_fact("last_branch_count", len(action["branches"]))
        if action.get("status") in {"approve", "confirmed", "require_confirmation"}:
            if action.get("status") in {"approve", "confirmed"}:
                self.goal_engine.complete_goal(goal.goal_id)
        return LoopTickResult(goal=goal.title, action=action, world_state=self.world_model.snapshot())
