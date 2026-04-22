"""Deterministic patch engine for exact line and symbol-grounded edits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .line_map import compute_hash, load_snapshot
from .patch_schema import PatchKind, PatchOperation
from .symbol_index import PythonSymbolIndex
from .verifier import CodeVerifier


@dataclass(slots=True)
class PatchApplicationResult:
    path: str
    success: bool
    patch: dict[str, object]
    old_hash: str
    new_hash: str
    changed_start_line: int
    changed_end_line: int
    undo: dict[str, object]
    verification: dict[str, object]
    message: str = ''

    def to_dict(self) -> dict[str, object]:
        return {
            'path': self.path,
            'success': self.success,
            'patch': self.patch,
            'old_hash': self.old_hash,
            'new_hash': self.new_hash,
            'changed_start_line': self.changed_start_line,
            'changed_end_line': self.changed_end_line,
            'undo': self.undo,
            'verification': self.verification,
            'message': self.message,
        }


class PatchEngine:
    def __init__(self) -> None:
        self.symbols = PythonSymbolIndex()
        self.verifier = CodeVerifier()

    def apply(self, workspace_root: str | Path, operation: PatchOperation) -> PatchApplicationResult:
        root = Path(workspace_root).resolve()
        target = (root / operation.path).resolve()
        if root not in target.parents and target != root:
            raise ValueError('Target path escapes workspace root.')
        snapshot = load_snapshot(target)
        if operation.expected_hash and operation.expected_hash != snapshot.content_hash:
            raise ValueError('File hash mismatch; reload file before applying patch.')
        start_line, end_line = self._resolve_lines(target, operation)
        before_block = snapshot.slice_lines(start_line, end_line)
        replacement_lines = operation.replacement_text.splitlines()
        new_lines = snapshot.lines[: start_line - 1] + replacement_lines + snapshot.lines[end_line:]
        new_content = '\n'.join(new_lines)
        if snapshot.content.endswith('\n'):
            new_content += '\n'
        target.write_text(new_content, encoding='utf-8')
        verification = self.verifier.verify_file(target)
        return PatchApplicationResult(
            path=str(Path(operation.path)),
            success=bool(verification['all_passed']),
            patch=operation.to_dict(),
            old_hash=snapshot.content_hash,
            new_hash=compute_hash(new_content),
            changed_start_line=start_line,
            changed_end_line=max(start_line, start_line + max(len(replacement_lines), 1) - 1),
            undo={
                'action': 'replace_range',
                'path': str(Path(operation.path)),
                'start_line': start_line,
                'end_line': max(start_line, start_line + max(len(replacement_lines), 1) - 1),
                'replacement_text': '\n'.join(before_block),
                'expected_hash': compute_hash(new_content),
            },
            verification=verification,
            message='Patch applied and verified.' if verification['all_passed'] else 'Patch applied but verification failed.',
        )

    def _resolve_lines(self, target: Path, operation: PatchOperation) -> tuple[int, int]:
        if operation.kind == PatchKind.REPLACE_RANGE:
            if operation.start_line is None or operation.end_line is None:
                raise ValueError('replace_range requires start_line and end_line.')
            return operation.start_line, operation.end_line
        if operation.kind == PatchKind.REPLACE_SYMBOL:
            if not operation.symbol_name:
                raise ValueError('replace_symbol requires symbol_name.')
            # First try exact symbol lookup; then allow a unique suffix fallback for methods/functions.
            match = self.symbols.find_symbol(target, operation.symbol_name, allow_suffix=True)
            if not match:
                raise ValueError(f'Symbol not found: {operation.symbol_name}')
            return match.start_line, match.end_line
        raise ValueError(f'Unsupported patch kind: {operation.kind}')
