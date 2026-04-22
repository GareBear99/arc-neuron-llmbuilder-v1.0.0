from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List
from uuid import uuid4


@dataclass
class Goal:
    title: str
    priority: int = 50
    status: str = "pending"
    completion_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    abort_conditions: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    archive_mode: str = "mirror_then_retire"
    source_text: str = ""
    goal_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            'goal_id': self.goal_id,
            'title': self.title,
            'priority': self.priority,
            'status': self.status,
            'completion_criteria': list(self.completion_criteria),
            'constraints': list(self.constraints),
            'invariants': list(self.invariants),
            'success_metrics': list(self.success_metrics),
            'abort_conditions': list(self.abort_conditions),
            'evidence_requirements': list(self.evidence_requirements),
            'archive_mode': self.archive_mode,
            'source_text': self.source_text,
        }


class GoalEngine:
    def __init__(self) -> None:
        self._goals: List[Goal] = []

    def compile_goal(self, text: str, *, priority: int = 50) -> Goal:
        lowered = text.lower()
        constraints = ['stay deterministic', 'preserve rollback and replay', 'do not mutate production without validation']
        invariants = ['no silent failure paths', 'record receipts for meaningful actions', 'retain branch lineage metadata']
        completion_criteria = ['requested action executed or denied with reason', 'result recorded into runtime state']
        success_metrics = ['final action status is approve or confirmed', 'validation receipts exist for code-changing work']
        abort_conditions = ['policy denial', 'validator failure', 'missing required evidence']
        evidence_requirements = ['receipt trail', 'planner summary']
        archive_mode = 'mirror_then_retire'

        if any(token in lowered for token in ['fix', 'repair', 'bug', 'error', 'failure']):
            evidence_requirements.append('similar-fix lookup')
            success_metrics.append('failure condition no longer reproduces')
        if any(token in lowered for token in ['release', 'production', 'publish', 'ship']):
            constraints.append('require promotion evidence bundle')
            evidence_requirements.extend(['validation result', 'promotion review'])
        if any(token in lowered for token in ['archive', 'memory']):
            archive_mode = 'early_mirror_then_retire'
            evidence_requirements.append('archive lineage metadata')
        if any(token in lowered for token in ['benchmark', 'faster', 'performance']):
            success_metrics.append('benchmark delta recorded')
            evidence_requirements.append('benchmark receipt')

        return Goal(
            title=text,
            priority=priority,
            completion_criteria=completion_criteria,
            constraints=constraints,
            invariants=invariants,
            success_metrics=success_metrics,
            abort_conditions=abort_conditions,
            evidence_requirements=evidence_requirements,
            archive_mode=archive_mode,
            source_text=text,
        )

    def add_goal(
        self,
        title: str,
        priority: int = 50,
        completion_criteria: list[str] | None = None,
        constraints: list[str] | None = None,
        invariants: list[str] | None = None,
        success_metrics: list[str] | None = None,
        abort_conditions: list[str] | None = None,
        evidence_requirements: list[str] | None = None,
        archive_mode: str | None = None,
        compile: bool = False,
    ) -> Goal:
        goal = self.compile_goal(title, priority=priority) if compile else Goal(title=title, priority=priority)
        if completion_criteria is not None:
            goal.completion_criteria = completion_criteria
        if constraints is not None:
            goal.constraints = constraints
        if invariants is not None:
            goal.invariants = invariants
        if success_metrics is not None:
            goal.success_metrics = success_metrics
        if abort_conditions is not None:
            goal.abort_conditions = abort_conditions
        if evidence_requirements is not None:
            goal.evidence_requirements = evidence_requirements
        if archive_mode is not None:
            goal.archive_mode = archive_mode
        self._goals.append(goal)
        self._goals.sort(key=lambda g: g.priority, reverse=True)
        return goal

    def current_goal(self) -> Goal | None:
        return next((g for g in self._goals if g.status == "pending"), None)

    def complete_goal(self, goal_id: str) -> None:
        for goal in self._goals:
            if goal.goal_id == goal_id:
                goal.status = "complete"
                break

    def all_goals(self) -> list[Goal]:
        return list(self._goals)
