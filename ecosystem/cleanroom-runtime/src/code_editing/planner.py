from __future__ import annotations

from pathlib import Path

from .line_map import load_snapshot
from .symbol_index import PythonSymbolIndex


class CodeEditPlanner:
    def __init__(self) -> None:
        self.symbols = PythonSymbolIndex()

    def plan_for_path(self, workspace_root: str | Path, path: str, instruction: str, symbol_name: str | None = None) -> dict[str, object]:
        target = (Path(workspace_root) / path).resolve()
        snapshot = load_snapshot(target)
        symbol_matches = [match.to_dict() for match in self.symbols.index_snapshot(snapshot)] if str(target).endswith('.py') else []
        selected = None
        if symbol_name:
            selected = next((match for match in symbol_matches if match['name'] == symbol_name), None)
        return {
            'status': 'ok',
            'path': str(Path(path)),
            'instruction': instruction,
            'content_hash': snapshot.content_hash,
            'line_count': snapshot.line_count,
            'target_symbol': selected,
            'symbols': symbol_matches,
            'recommended_operations': [
                'replace_symbol' if selected else 'replace_range',
                'verify_file',
                'run_pytest',
            ],
        }
