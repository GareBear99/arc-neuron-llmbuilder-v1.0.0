from __future__ import annotations

import ast
from pathlib import Path

from .line_map import load_snapshot


class CodeVerifier:
    def verify_file(self, path: str | Path) -> dict[str, object]:
        snapshot = load_snapshot(path)
        checks: list[dict[str, object]] = [
            {'validator': 'file_exists', 'passed': True},
            {'validator': 'utf8_readable', 'passed': True},
        ]
        parse_ok = True
        parse_error = ''
        if str(path).endswith('.py'):
            try:
                ast.parse(snapshot.content)
            except SyntaxError as exc:
                parse_ok = False
                parse_error = str(exc)
            checks.append({'validator': 'python_parse', 'passed': parse_ok, 'error': parse_error or None})
        return {
            'path': str(Path(path)),
            'content_hash': snapshot.content_hash,
            'line_count': snapshot.line_count,
            'all_passed': all(bool(check['passed']) for check in checks),
            'checks': checks,
        }
