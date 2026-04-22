from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PatchKind(str, Enum):
    REPLACE_RANGE = 'replace_range'
    REPLACE_SYMBOL = 'replace_symbol'


@dataclass(slots=True)
class PatchOperation:
    kind: PatchKind
    path: str
    replacement_text: str
    start_line: int | None = None
    end_line: int | None = None
    symbol_name: str | None = None
    expected_hash: str | None = None
    reason: str = ''

    def to_dict(self) -> dict[str, object]:
        return {
            'kind': self.kind.value,
            'path': self.path,
            'replacement_text': self.replacement_text,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'symbol_name': self.symbol_name,
            'expected_hash': self.expected_hash,
            'reason': self.reason,
        }
