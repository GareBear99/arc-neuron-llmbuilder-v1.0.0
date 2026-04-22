from __future__ import annotations

"""Candidate generation and scoring for deterministic self-improvement cycles.

This layer expands a single grounded patch intent into a small set of deterministic
candidate variants, then validates each variant inside its own copied worktree. The
system can then choose the best-scoring candidate and execute it in the primary run.
"""

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

from code_editing import PatchEngine, PatchKind, PatchOperation


@dataclass(slots=True)
class CandidateSpec:
    candidate_id: str
    label: str
    replacement_text: str
    symbol_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    expected_hash: str | None = None
    rationale: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'candidate_id': self.candidate_id,
            'label': self.label,
            'replacement_text': self.replacement_text,
            'symbol_name': self.symbol_name,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'expected_hash': self.expected_hash,
            'rationale': self.rationale,
        }


def _normalize_validation_command(command: str | Sequence[str]) -> list[str]:
    """Return an argv-style command for subprocess execution without invoking a shell.

    Candidate manifests may store commands as either shell-like strings or explicit argv
    sequences. Strings are parsed with ``shlex.split`` so validation stays deterministic
    without opening a shell injection surface.
    """
    if isinstance(command, str):
        parsed = shlex.split(command)
        if not parsed:
            raise ValueError('Validation command cannot be empty.')
        return parsed
    parsed = [str(part) for part in command]
    if not parsed:
        raise ValueError('Validation command cannot be empty.')
    return parsed


class CandidateCycleManager:
    """Generate, score, and select deterministic patch candidates for a run."""

    def __init__(self) -> None:
        self.patch_engine = PatchEngine()

    def _run_dir(self, workspace_root: str | Path, run_id: str) -> Path:
        return Path(workspace_root) / '.arc_lucifer' / 'self_improve_runs' / run_id

    def _manifest_path(self, workspace_root: str | Path, run_id: str) -> Path:
        return self._run_dir(workspace_root, run_id) / 'manifest.json'

    def load_manifest(self, workspace_root: str | Path, run_id: str) -> dict[str, Any]:
        path = self._manifest_path(workspace_root, run_id)
        if not path.exists():
            raise FileNotFoundError(f'Unknown improvement run: {run_id}')
        return json.loads(path.read_text(encoding='utf-8'))

    def save_manifest(self, workspace_root: str | Path, run_id: str, manifest: dict[str, Any]) -> None:
        self._manifest_path(workspace_root, run_id).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')

    def _candidates_root(self, workspace_root: str | Path, run_id: str) -> Path:
        path = self._run_dir(workspace_root, run_id) / 'candidates'
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _score_root(self, workspace_root: str | Path, run_id: str) -> Path:
        path = self._run_dir(workspace_root, run_id) / 'candidate_scores'
        path.mkdir(parents=True, exist_ok=True)
        return path

    def generate_candidates(
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
    ) -> dict[str, Any]:
        """Create a small set of deterministic candidate variants.

        The first variant is always the exact replacement text. Additional variants normalize
        common patch-edge conditions so the system can compare candidates without inventing
        unrelated content.
        """
        manifest = self.load_manifest(workspace_root, run_id)
        root = self._candidates_root(workspace_root, run_id)
        variants: list[tuple[str, str]] = []
        text = replacement_text
        normalized_newline = replacement_text if replacement_text.endswith('\n') else replacement_text + '\n'
        trimmed = '\n'.join(line.rstrip() for line in replacement_text.splitlines())
        if replacement_text.endswith('\n'):
            trimmed += '\n'
        variants.append(('exact', text))
        if normalized_newline != text:
            variants.append(('normalized_newline', normalized_newline))
        if trimmed != text and trimmed != normalized_newline:
            variants.append(('trim_trailing_ws', trimmed))
        if len(variants) == 1:
            variants.append(('duplicate_guard', text))

        existing = list(manifest.get('candidates', []))
        candidate_specs: list[dict[str, Any]] = []
        for idx, (label, candidate_text) in enumerate(variants, start=len(existing) + 1):
            candidate_id = f'{run_id}:cand:{idx:03d}:{uuid4().hex[:6]}'
            spec = CandidateSpec(
                candidate_id=candidate_id,
                label=label,
                replacement_text=candidate_text,
                symbol_name=symbol_name,
                start_line=start_line,
                end_line=end_line,
                expected_hash=expected_hash,
                rationale=rationale or f'Auto-generated candidate ({label})',
            )
            payload = {'path': path, **spec.to_dict()}
            (root / f'{idx:03d}_{label}.json').write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
            candidate_specs.append(payload)
        manifest.setdefault('candidates', []).extend(candidate_specs)
        manifest['last_candidate_generation_count'] = len(candidate_specs)
        self.save_manifest(workspace_root, run_id, manifest)
        return {'status': 'ok', 'run_id': run_id, 'path': path, 'candidate_count': len(candidate_specs), 'candidates': candidate_specs}

    def score_candidates(self, workspace_root: str | Path, run_id: str, *, timeout: int = 120) -> dict[str, Any]:
        """Apply and validate every candidate inside an isolated candidate worktree."""
        manifest = self.load_manifest(workspace_root, run_id)
        run_dir = self._run_dir(workspace_root, run_id)
        score_root = self._score_root(workspace_root, run_id)
        worktree_dir = Path(manifest['worktree_dir'])
        commands = list(manifest.get('recommended_commands', []))
        results: list[dict[str, Any]] = []
        for idx, candidate in enumerate(manifest.get('candidates', []), start=1):
            candidate_dir = run_dir / 'candidate_worktrees' / candidate['candidate_id']
            if candidate_dir.exists():
                shutil.rmtree(candidate_dir)
            shutil.copytree(worktree_dir, candidate_dir, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', '*.pyc'))
            kind = PatchKind.REPLACE_SYMBOL if candidate.get('symbol_name') else PatchKind.REPLACE_RANGE
            operation = PatchOperation(
                kind=kind,
                path=candidate['path'],
                replacement_text=candidate['replacement_text'],
                symbol_name=candidate.get('symbol_name'),
                start_line=candidate.get('start_line'),
                end_line=candidate.get('end_line'),
                expected_hash=candidate.get('expected_hash'),
                reason=candidate.get('rationale', ''),
            )
            try:
                patch_result = self.patch_engine.apply(candidate_dir, operation).to_dict()
            except Exception as exc:
                patch_result = {
                    'success': False,
                    'message': str(exc),
                    'verification': {'all_passed': False, 'checks': [{'validator': 'patch_exception', 'passed': False}]},
                    'changed_start_line': 0,
                    'changed_end_line': 0,
                }
            validation_results: list[dict[str, Any]] = []
            validation_passed = bool(patch_result.get('success'))
            if validation_passed:
                for command in commands:
                    argv = _normalize_validation_command(command)
                    proc = subprocess.run(argv, cwd=candidate_dir, text=True, capture_output=True, timeout=timeout)
                    item = {
                        'command': command,
                        'argv': argv,
                        'returncode': proc.returncode,
                        'passed': proc.returncode == 0,
                        'stdout': proc.stdout[-2000:],
                        'stderr': proc.stderr[-2000:],
                    }
                    validation_results.append(item)
                    validation_passed = validation_passed and item['passed']
            score = 0.0
            if patch_result.get('success'):
                score += 0.5
            if patch_result.get('verification', {}).get('all_passed'):
                score += 0.25
            if validation_passed:
                score += 0.25
            changed = max(0, int(patch_result.get('changed_end_line', 0)) - int(patch_result.get('changed_start_line', 0)) + 1)
            score -= min(changed / 1000.0, 0.05)
            payload = {
                'candidate_id': candidate['candidate_id'],
                'label': candidate['label'],
                'path': candidate['path'],
                'score': round(max(score, 0.0), 4),
                'patch_success': bool(patch_result.get('success')),
                'verification_passed': bool(patch_result.get('verification', {}).get('all_passed')),
                'validation_passed': bool(validation_passed),
                'patch_result': patch_result,
                'validation_results': validation_results,
                'candidate_dir': str(candidate_dir.resolve()),
            }
            (score_root / f'{idx:03d}_{candidate["label"]}.json').write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
            results.append(payload)
        results.sort(key=lambda item: (-item['score'], item['candidate_id']))
        manifest['candidate_scores'] = results
        if results:
            manifest['best_candidate_id'] = results[0]['candidate_id']
        self.save_manifest(workspace_root, run_id, manifest)
        return {'status': 'ok', 'run_id': run_id, 'candidate_count': len(results), 'best_candidate_id': manifest.get('best_candidate_id'), 'scores': results}

    def choose_best_candidate(self, workspace_root: str | Path, run_id: str) -> dict[str, Any]:
        manifest = self.load_manifest(workspace_root, run_id)
        scores = list(manifest.get('candidate_scores', []))
        if not scores:
            return {'status': 'not_found', 'run_id': run_id, 'reason': 'No candidate scores recorded.'}
        best = sorted(scores, key=lambda item: (-item['score'], item['candidate_id']))[0]
        return {'status': 'ok', 'run_id': run_id, 'best_candidate': best}
