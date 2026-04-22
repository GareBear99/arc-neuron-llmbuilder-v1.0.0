"""Adversarial and fault-injection helpers for self-improvement runs.

This module gives the runtime a deterministic way to stress the self-improvement lane:
- inject common failure conditions into a scaffolded run worktree
- execute validation/promotion flows under those conditions
- quarantine failing runs and preserve a forensic receipt

The goal is not to fake autonomous robustness. The goal is to make failure modes explicit,
repeatable, and inspectable so the operator can prove the loop degrades safely.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .executor import ImprovementExecutor
from .promotion import PromotionGate


@dataclass(slots=True)
class FaultInjectionResult:
    run_id: str
    fault_kind: str
    status: str
    detail: str
    artifact_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'run_id': self.run_id,
            'fault_kind': self.fault_kind,
            'status': self.status,
            'detail': self.detail,
            'artifact_path': self.artifact_path,
        }


class AdversarialManager:
    """Inject deterministic run faults and execute validation under stress."""

    SUPPORTED_FAULTS = {
        'delete_target_file',
        'python_syntax_break',
        'force_validation_failure',
        'corrupt_candidate_tree',
    }

    def __init__(self) -> None:
        self.promotions = PromotionGate()
        self.executor = ImprovementExecutor()

    def _run_dir(self, workspace_root: str | Path, run_id: str) -> Path:
        return Path(workspace_root) / '.arc_lucifer' / 'self_improve_runs' / run_id

    def _manifest_path(self, workspace_root: str | Path, run_id: str) -> Path:
        return self._run_dir(workspace_root, run_id) / 'manifest.json'

    def _adversarial_root(self, workspace_root: str | Path, run_id: str) -> Path:
        root = self._run_dir(workspace_root, run_id) / 'adversarial'
        root.mkdir(parents=True, exist_ok=True)
        return root

    def load_manifest(self, workspace_root: str | Path, run_id: str) -> dict[str, Any]:
        path = self._manifest_path(workspace_root, run_id)
        if not path.exists():
            raise FileNotFoundError(f'Unknown improvement run: {run_id}')
        return json.loads(path.read_text(encoding='utf-8'))

    def save_manifest(self, workspace_root: str | Path, run_id: str, manifest: dict[str, Any]) -> None:
        self._manifest_path(workspace_root, run_id).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')

    def inject_fault(
        self,
        workspace_root: str | Path,
        run_id: str,
        *,
        kind: str,
        path: str | None = None,
        note: str = '',
    ) -> FaultInjectionResult:
        if kind not in self.SUPPORTED_FAULTS:
            raise ValueError(f'Unsupported fault kind: {kind}')
        manifest = self.load_manifest(workspace_root, run_id)
        worktree = Path(manifest['worktree_dir'])
        target_path = worktree / path if path else None
        detail = ''
        status = 'ok'
        if kind == 'delete_target_file':
            if not target_path or not target_path.exists():
                raise FileNotFoundError('Target path is required and must exist for delete_target_file.')
            target_path.unlink()
            detail = f'Deleted worktree target: {target_path.relative_to(worktree)}'
        elif kind == 'python_syntax_break':
            if not target_path or not target_path.exists():
                raise FileNotFoundError('Target path is required and must exist for python_syntax_break.')
            with target_path.open('a', encoding='utf-8') as handle:
                handle.write('\n__arc_fault__ = (\n')
            detail = f'Appended deterministic syntax error to: {target_path.relative_to(worktree)}'
        elif kind == 'force_validation_failure':
            manifest.setdefault('recommended_commands', [])
            manifest['recommended_commands'] = ['python -c "import sys; sys.exit(7)"']
            self.save_manifest(workspace_root, run_id, manifest)
            detail = 'Overrode recommended_commands with a deterministic failing validation command.'
        elif kind == 'corrupt_candidate_tree':
            candidate_root = self._run_dir(workspace_root, run_id) / 'candidate_worktrees'
            if candidate_root.exists():
                shutil.rmtree(candidate_root)
            candidate_root.mkdir(parents=True, exist_ok=True)
            (candidate_root / 'CORRUPTED.txt').write_text('candidate worktrees intentionally cleared\n', encoding='utf-8')
            detail = 'Reset candidate_worktrees to simulate corruption/loss.'
        artifact = {
            'run_id': run_id,
            'fault_kind': kind,
            'note': note,
            'detail': detail,
            'status': status,
        }
        root = self._adversarial_root(workspace_root, run_id)
        count = len(list(root.glob('fault_*.json'))) + 1
        artifact_path = root / f'fault_{count:03d}_{kind}.json'
        artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding='utf-8')
        manifest.setdefault('fault_injections', []).append({
            'fault_kind': kind,
            'detail': detail,
            'artifact_path': str(artifact_path.resolve()),
        })
        self.save_manifest(workspace_root, run_id, manifest)
        return FaultInjectionResult(run_id=run_id, fault_kind=kind, status=status, detail=detail, artifact_path=str(artifact_path.resolve()))

    def adversarial_cycle(
        self,
        workspace_root: str | Path,
        run_id: str,
        *,
        kind: str,
        path: str,
        replacement_text: str,
        symbol_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        expected_hash: str | None = None,
        rationale: str = '',
        timeout: int = 120,
    ) -> dict[str, Any]:
        fault = self.inject_fault(workspace_root, run_id, kind=kind, path=path, note=rationale)
        payload = {
            'status': 'ok',
            'fault': fault.to_dict(),
        }
        cycle = self.executor.execute_cycle(
            workspace_root,
            run_id,
            path=path,
            replacement_text=replacement_text,
            symbol_name=symbol_name,
            start_line=start_line,
            end_line=end_line,
            expected_hash=expected_hash,
            rationale=rationale or f'adversarial cycle under {kind}',
            validate=True,
            timeout=timeout,
            promote=False,
            quarantine_on_failure=True,
        )
        payload['cycle'] = cycle
        if cycle.get('status') == 'partial_fallback' or cycle.get('quarantine'):
            payload['status'] = 'completed_fallback'
        elif cycle.get('validation', {}).get('passed') is False:
            payload['status'] = 'partial_fallback'
        return payload
