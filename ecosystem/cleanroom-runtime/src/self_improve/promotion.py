from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cognition_services.immutable_baseline import ImmutableBaseline


@dataclass(slots=True)
class ValidationResult:
    run_id: str
    passed: bool
    command_results: list[dict[str, Any]]
    manifest_path: str
    worktree_dir: str
    validation_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'run_id': self.run_id,
            'passed': self.passed,
            'command_results': self.command_results,
            'manifest_path': self.manifest_path,
            'worktree_dir': self.worktree_dir,
            'validation_path': self.validation_path,
        }


def _normalize_validation_command(command: str | list[str] | tuple[str, ...]) -> list[str]:
    """Return an argv-style validation command without invoking a shell."""
    if isinstance(command, str):
        parsed = shlex.split(command)
        if not parsed:
            raise ValueError('Validation command cannot be empty.')
        return parsed
    parsed = [str(part) for part in command]
    if not parsed:
        raise ValueError('Validation command cannot be empty.')
    return parsed


class PromotionGate:
    def _run_root(self, workspace_root: str | Path) -> Path:
        return Path(workspace_root) / '.arc_lucifer' / 'self_improve_runs'

    def _find_run_dir(self, workspace_root: str | Path, run_id: str) -> Path:
        run_dir = self._run_root(workspace_root) / run_id
        if not run_dir.exists():
            raise FileNotFoundError(f'Unknown improvement run: {run_id}')
        return run_dir

    def load_manifest(self, workspace_root: str | Path, run_id: str) -> dict[str, Any]:
        run_dir = self._find_run_dir(workspace_root, run_id)
        manifest_path = run_dir / 'manifest.json'
        return json.loads(manifest_path.read_text(encoding='utf-8'))

    def validate_run(self, workspace_root: str | Path, run_id: str, timeout: int = 120) -> ValidationResult:
        run_dir = self._find_run_dir(workspace_root, run_id)
        manifest = self.load_manifest(workspace_root, run_id)
        worktree_dir = Path(manifest['worktree_dir'])
        command_results: list[dict[str, Any]] = []
        all_passed = True
        for command in manifest.get('recommended_commands', []):
            argv = _normalize_validation_command(command)
            proc = subprocess.run(
                argv,
                cwd=worktree_dir,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
            result = {
                'command': command,
                'argv': argv,
                'returncode': proc.returncode,
                'stdout': proc.stdout[-4000:],
                'stderr': proc.stderr[-4000:],
                'passed': proc.returncode == 0,
            }
            command_results.append(result)
            all_passed = all_passed and result['passed']
        payload = {
            'run_id': run_id,
            'passed': all_passed,
            'command_results': command_results,
        }
        validation_path = run_dir / 'validation.json'
        validation_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
        return ValidationResult(
            run_id=run_id,
            passed=all_passed,
            command_results=command_results,
            manifest_path=str((run_dir / 'manifest.json').resolve()),
            worktree_dir=str(worktree_dir.resolve()),
            validation_path=str(validation_path.resolve()),
        )

    def _baseline_review(self, workspace_root: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
        baseline = ImmutableBaseline(workspace_root)
        patch_reviews: list[dict[str, Any]] = []
        all_allowed = True
        for patch in manifest.get('applied_patches', []):
            path = str(patch.get('path', ''))
            decision = baseline.check(path)
            patch_review = {
                'patch_id': patch.get('patch_id'),
                'path': path,
                'success': bool(patch.get('success')),
                'baseline': decision.to_dict(),
            }
            patch_reviews.append(patch_review)
            all_allowed = all_allowed and bool(decision.allowed)
        return {
            'all_allowed': all_allowed,
            'patch_reviews': patch_reviews,
        }

    def review_run(self, workspace_root: str | Path, run_id: str) -> dict[str, Any]:
        run_dir = self._find_run_dir(workspace_root, run_id)
        manifest = self.load_manifest(workspace_root, run_id)
        validation_path = run_dir / 'validation.json'
        if not validation_path.exists():
            return {
                'run_id': run_id,
                'approved': False,
                'reason': 'missing_validation',
                'checks': {'validation_exists': False},
            }
        validation = json.loads(validation_path.read_text(encoding='utf-8'))
        command_results = list(validation.get('command_results', []))
        applied_patches = list(manifest.get('applied_patches', []))
        all_patch_success = all(p.get('success') for p in applied_patches) if applied_patches else True
        baseline_review = self._baseline_review(workspace_root, manifest)
        checks = {
            'validation_exists': True,
            'validation_passed': bool(validation.get('passed')),
            'command_count': len(command_results),
            'has_evidence_bundle': bool(command_results),
            'all_patch_success': all_patch_success,
            'baseline_allows_patches': baseline_review['all_allowed'],
        }
        approved = all([
            checks['validation_exists'],
            checks['validation_passed'],
            checks['has_evidence_bundle'],
            checks['all_patch_success'],
            checks['baseline_allows_patches'],
        ])
        reason = 'approved' if approved else 'promotion_court_denied'
        payload = {
            'run_id': run_id,
            'approved': approved,
            'reason': reason,
            'checks': checks,
            'command_results': command_results,
            'applied_patches': applied_patches,
            'baseline_review': baseline_review,
        }
        (run_dir / 'promotion_review.json').write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
        return payload

    def promote_run(self, workspace_root: str | Path, run_id: str, *, force: bool = False) -> dict[str, Any]:
        run_dir = self._find_run_dir(workspace_root, run_id)
        manifest = self.load_manifest(workspace_root, run_id)
        review = self.review_run(workspace_root, run_id)
        if not force and not review.get('approved'):
            raise ValueError(f"Promotion review denied: {review.get('reason')}")
        worktree_dir = Path(manifest['worktree_dir'])
        workspace = Path(workspace_root).resolve()
        promoted: list[str] = []
        for rel in ['src', 'tests', 'docs', 'README.md', 'pyproject.toml']:
            src = worktree_dir / rel
            dst = workspace / rel
            if not src.exists():
                continue
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', '*.pyc'))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            promoted.append(rel)
        payload = {
            'run_id': run_id,
            'promoted_paths': promoted,
            'forced': force,
            'workspace': str(workspace),
            'review': review,
        }
        (run_dir / 'promotion.json').write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
        return payload
