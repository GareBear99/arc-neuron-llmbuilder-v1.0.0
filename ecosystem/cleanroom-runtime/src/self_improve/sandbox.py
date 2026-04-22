from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utcnow_compact() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


@dataclass(slots=True)
class ImprovementRun:
    run_id: str
    run_dir: str
    worktree_dir: str
    manifest_path: str
    task_count: int
    target_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            'run_id': self.run_id,
            'run_dir': self.run_dir,
            'worktree_dir': self.worktree_dir,
            'manifest_path': self.manifest_path,
            'task_count': self.task_count,
            'target_key': self.target_key,
        }


class SandboxManager:
    COPY_PATHS = ['src', 'tests', 'docs', 'README.md', 'pyproject.toml']

    def scaffold(self, workspace_root: str | Path, plan: dict[str, Any]) -> ImprovementRun:
        workspace = Path(workspace_root)
        runtime_dir = workspace / '.arc_lucifer' / 'self_improve_runs'
        runtime_dir.mkdir(parents=True, exist_ok=True)
        run_id = f"run_{utcnow_compact()}_{uuid4().hex[:8]}"
        run_dir = runtime_dir / run_id
        worktree_dir = run_dir / 'worktree'
        worktree_dir.mkdir(parents=True, exist_ok=True)
        for rel in self.COPY_PATHS:
            src = workspace / rel
            dst = worktree_dir / rel
            if not src.exists():
                continue
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', '*.pyc'))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        manifest_path = run_dir / 'manifest.json'
        manifest = {
            'kind': 'self_improve_run',
            'run_id': run_id,
            'created_at': utcnow_compact(),
            'workspace': str(workspace.resolve()),
            'target_key': plan.get('target_key'),
            'task_count': plan.get('task_count', 0),
            'tasks': plan.get('tasks', []),
            'worktree_dir': str(worktree_dir.resolve()),
            'recommended_commands': [
                'python -m pytest -q',
                'PYTHONPATH=src python -m lucifer_runtime.cli bench',
                'PYTHONPATH=src python -m lucifer_runtime.cli doctor',
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')
        return ImprovementRun(
            run_id=run_id,
            run_dir=str(run_dir.resolve()),
            worktree_dir=str(worktree_dir.resolve()),
            manifest_path=str(manifest_path.resolve()),
            task_count=int(plan.get('task_count', 0)),
            target_key=plan.get('target_key'),
        )
