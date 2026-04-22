"""Python symbol indexing for exact line-grounded code edits."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .line_map import FileSnapshot, load_snapshot


@dataclass(slots=True)
class SymbolMatch:
    name: str
    kind: str
    start_line: int
    end_line: int
    parent: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            'name': self.name,
            'kind': self.kind,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'parent': self.parent,
        }


class PythonSymbolIndex:
    """Indexes Python top-level classes/functions and class methods by exact line ranges."""

    def index_snapshot(self, snapshot: FileSnapshot) -> list[SymbolMatch]:
        tree = ast.parse(snapshot.content)
        matches: list[SymbolMatch] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                matches.append(SymbolMatch(node.name, 'function', node.lineno, node.end_lineno or node.lineno))
            elif isinstance(node, ast.ClassDef):
                matches.append(SymbolMatch(node.name, 'class', node.lineno, node.end_lineno or node.lineno))
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        matches.append(SymbolMatch(f'{node.name}.{child.name}', 'method', child.lineno, child.end_lineno or child.lineno, parent=node.name))
        return matches

    def index_path(self, path: str | Path) -> list[SymbolMatch]:
        return self.index_snapshot(load_snapshot(path))

    def find_symbol(self, path: str | Path, symbol_name: str, *, allow_suffix: bool = False) -> SymbolMatch | None:
        """Find an exact symbol, or optionally a unique suffix match such as method name only."""
        matches = self.index_path(path)
        for match in matches:
            if match.name == symbol_name:
                return match
        if allow_suffix:
            suffix_matches = [match for match in matches if match.name.split('.')[-1] == symbol_name]
            if len(suffix_matches) == 1:
                return suffix_matches[0]
        return None
