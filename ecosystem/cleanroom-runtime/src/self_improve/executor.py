"""Self-improvement execution helpers for applying grounded patches inside sandbox runs.

This module turns a scaffolded self-improvement run into an executable change cycle:
- load a run manifest
- apply an exact line/symbol-grounded patch inside the run worktree
- record a durable patch artifact
- optionally validate and promote the run

The design stays deterministic: the caller supplies the exact patch content, while the
patch engine handles file hashing, symbol/line lookup, parser verification, and undo data.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from code_editing import PatchEngine, PatchKind, PatchOperation
from .promotion import PromotionGate


@dataclass(slots=True)
class ImprovementPatchResult:
    """Result of applying a grounded patch inside a self-improvement worktree."""

    run_id: str
    patch_id: str
    path: str
    success: bool
    patch_result: dict[str, Any]
    artifact_path: str
    validation_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            'run_id': self.run_id,
            'patch_id': self.patch_id,
            'path': self.path,
            'success': self.success,
            'patch_result': self.patch_result,
            'artifact_path': self.artifact_path,
            'validation_requested': self.validation_requested,
        }


class ImprovementExecutor:
    """Executes deterministic patch cycles inside scaffolded self-improvement runs."""

    def __init__(self) -> None:
        self.promotions = PromotionGate()
        self.patch_engine = PatchEngine()

    def _run_dir(self, workspace_root: str | Path, run_id: str) -> Path:
        return Path(workspace_root) / '.arc_lucifer' / 'self_improve_runs' / run_id

    def _manifest_path(self, workspace_root: str | Path, run_id: str) -> Path:
        return self._run_dir(workspace_root, run_id) / 'manifest.json'

    def _patch_root(self, workspace_root: str | Path, run_id: str) -> Path:
        root = self._run_dir(workspace_root, run_id) / 'patches'
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _quarantine_root(self, workspace_root: str | Path, run_id: str) -> Path:
        root = Path(workspace_root) / '.arc_lucifer' / 'quarantine' / run_id
        root.mkdir(parents=True, exist_ok=True)
        return root

    def load_manifest(self, workspace_root: str | Path, run_id: str) -> dict[str, Any]:
        path = self._manifest_path(workspace_root, run_id)
        if not path.exists():
            raise FileNotFoundError(f'Unknown improvement run: {run_id}')
        return json.loads(path.read_text(encoding='utf-8'))

    def save_manifest(self, workspace_root: str | Path, run_id: str, manifest: dict[str, Any]) -> Path:
        path = self._manifest_path(workspace_root, run_id)
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')
        return path

    def apply_patch(
        self,
        workspace_root: str | Path,
        run_id: str,
        *,
        path: str,
        replacement_text: str,
        symbol_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        expected_hash: str | None = None,
        validation_requested: bool = False,
        rationale: str = '',
    ) -> ImprovementPatchResult:
        manifest = self.load_manifest(workspace_root, run_id)
        worktree_root = Path(manifest['worktree_dir'])
        patch_kind = PatchKind.REPLACE_SYMBOL if symbol_name else PatchKind.REPLACE_RANGE
        patch_count = len(manifest.get('applied_patches', [])) + 1
        patch_id = f'{run_id}:patch:{patch_count:03d}'
        operation = PatchOperation(
            kind=patch_kind,
            path=path,
            replacement_text=replacement_text,
            symbol_name=symbol_name,
            start_line=start_line,
            end_line=end_line,
            expected_hash=expected_hash,
            reason=rationale,
        )
        result = self.patch_engine.apply(worktree_root, operation)
        artifact = {
            'run_id': run_id,
            'patch_id': patch_id,
            'path': path,
            'kind': operation.kind.value,
            'symbol_name': symbol_name,
            'start_line': start_line,
            'end_line': end_line,
            'rationale': rationale,
            'validation_requested': validation_requested,
            'result': result.to_dict(),
        }
        artifact_path = self._patch_root(workspace_root, run_id) / f'{patch_count:03d}_{Path(path).name}.json'
        artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding='utf-8')
        manifest.setdefault('applied_patches', []).append({
            'patch_id': patch_id,
            'artifact_path': str(artifact_path.resolve()),
            'success': result.success,
            'path': path,
            'kind': operation.kind.value,
        })
        manifest['last_patch_id'] = patch_id
        manifest['last_patch_success'] = result.success
        self.save_manifest(workspace_root, run_id, manifest)
        return ImprovementPatchResult(
            run_id=run_id,
            patch_id=patch_id,
            path=path,
            success=result.success,
            patch_result=result.to_dict(),
            artifact_path=str(artifact_path.resolve()),
            validation_requested=validation_requested,
        )

    def execute_cycle(
        self,
        workspace_root: str | Path,
        run_id: str,
        *,
        path: str,
        replacement_text: str,
        symbol_name: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        expected_hash: str | None = None,
        rationale: str = '',
        validate: bool = True,
        timeout: int = 120,
        promote: bool = False,
        force_promote: bool = False,
        quarantine_on_failure: bool = True,
    ) -> dict[str, Any]:
        patch = self.apply_patch(
            workspace_root,
            run_id,
            path=path,
            replacement_text=replacement_text,
            symbol_name=symbol_name,
            start_line=start_line,
            end_line=end_line,
            expected_hash=expected_hash,
            validation_requested=validate,
            rationale=rationale,
        )
        payload: dict[str, Any] = {'status': 'ok', 'patch': patch.to_dict()}
        validation_payload: dict[str, Any] | None = None
        if validate:
            validation_payload = self.promotions.validate_run(workspace_root, run_id, timeout=timeout).to_dict()
            payload['validation'] = validation_payload
        if promote and validation_payload and validation_payload.get('passed'):
            promotion = self.promotions.promote_run(workspace_root, run_id, force=force_promote)
            payload['promotion'] = {'status': 'ok', **promotion}
        elif promote and validation_payload and not validation_payload.get('passed') and quarantine_on_failure:
            payload['quarantine'] = self.quarantine_run(workspace_root, run_id, reason='validation_failed')
            payload['status'] = 'partial_fallback'
        return payload

    def quarantine_run(self, workspace_root: str | Path, run_id: str, *, reason: str) -> dict[str, Any]:
        run_dir = self._run_dir(workspace_root, run_id)
        if not run_dir.exists():
            raise FileNotFoundError(f'Unknown improvement run: {run_id}')
        quarantine_root = self._quarantine_root(workspace_root, run_id)
        target = quarantine_root / 'run_snapshot'
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(run_dir, target)
        payload = {'run_id': run_id, 'reason': reason, 'quarantine_path': str(target.resolve())}
        (quarantine_root / 'quarantine.json').write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
        return payload
