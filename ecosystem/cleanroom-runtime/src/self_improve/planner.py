from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ImprovementTask:
    key: str
    priority: str
    title: str
    rationale: str
    suggested_files: list[str]
    validation_steps: list[str]
    action_hint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key,
            'priority': self.priority,
            'title': self.title,
            'rationale': self.rationale,
            'suggested_files': self.suggested_files,
            'validation_steps': self.validation_steps,
            'action_hint': self.action_hint,
        }


class ImprovementPlanner:
    """Turns improvement analysis into concrete repo-local execution plans."""

    DEFAULT_VALIDATION = [
        'python -m pytest -q',
        'python -m lucifer_runtime.cli bench',
        'python -m lucifer_runtime.cli doctor',
    ]

    FILE_HINTS = {
        'benchmarks_missing': ['src/self_improve/benchmarks.py', 'tests/test_bench_and_state_world_model.py'],
        'benchmark_failures': ['tests/', 'src/lucifer_runtime/runtime.py', 'src/self_improve/benchmarks.py'],
        'model_path_unvalidated': ['src/model_services/llamafile_backend.py', 'src/lucifer_runtime/cli.py', 'docs/llamafile_flow.md'],
        'pending_proposals': ['src/arc_kernel/policy.py', 'src/lucifer_runtime/cli.py'],
        'denied_proposals': ['src/arc_kernel/policy.py', 'src/lucifer_runtime/router.py'],
        'trace_missing': ['src/dashboards/trace_viewer.py', 'docs/'],
        'workspace_growth': ['src/memory_subsystem/manager.py', 'src/memory_subsystem/retention.py'],
        'memory_metadata_refresh': ['src/memory_subsystem/manager.py', 'src/memory_subsystem/records.py', 'docs/memory_retention.md'],
        'memory_guided_planning': ['src/self_improve/analyzer.py', 'src/self_improve/planner.py', 'src/arc_kernel/state.py'],
        'fallback_hotspots': ['src/resilience/', 'src/lucifer_runtime/runtime.py', 'tests/'],
        'stable_baseline': ['tests/', 'docs/benchmarks.md'],
    }

    def build_plan(self, analysis: dict[str, Any], workspace_root: str | Path, target_key: str | None = None) -> dict[str, Any]:
        workspace = Path(workspace_root)
        targets = list(analysis.get('targets', []))
        if target_key:
            targets = [t for t in targets if t.get('key') == target_key]
        tasks: list[ImprovementTask] = []
        for target in targets:
            key = str(target.get('key', 'unknown'))
            hints = self.FILE_HINTS.get(key, ['src/', 'tests/', 'docs/'])
            task = ImprovementTask(
                key=key,
                priority=str(target.get('priority', 'low')),
                title=str(target.get('title', key.replace('_', ' ').title())),
                rationale=str(target.get('rationale', 'No rationale provided.')),
                suggested_files=[str(Path(h)) for h in hints],
                validation_steps=list(self.DEFAULT_VALIDATION),
                action_hint=str(target.get('action_hint', 'Review state and implement the minimum safe change.')),
            )
            tasks.append(task)
        return {
            'status': 'ok',
            'workspace': str(workspace.resolve()),
            'target_key': target_key,
            'task_count': len(tasks),
            'tasks': [task.to_dict() for task in tasks],
        }
