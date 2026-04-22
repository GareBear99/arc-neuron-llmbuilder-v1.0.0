from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from fixnet.models import utcnow_iso


@dataclass(slots=True)
class Directive:
    title: str
    instruction: str
    priority: int = 50
    scope: str = 'global'
    constraints: list[str] = field(default_factory=list)
    success_conditions: list[str] = field(default_factory=list)
    abort_conditions: list[str] = field(default_factory=list)
    persistence_mode: str = 'forever'
    issuer: str = 'operator'
    status: str = 'active'
    directive_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    supersedes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DirectiveLedger:
    def __init__(self, runtime_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.dir = self.runtime_root / '.arc_lucifer' / 'directives'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / 'ledger.json'
        if not self.path.exists():
            self.path.write_text(json.dumps({'directives': []}, indent=2, sort_keys=True), encoding='utf-8')

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding='utf-8'))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')

    def register(
        self,
        *,
        title: str,
        instruction: str,
        priority: int = 50,
        scope: str = 'global',
        constraints: list[str] | None = None,
        success_conditions: list[str] | None = None,
        abort_conditions: list[str] | None = None,
        persistence_mode: str = 'forever',
        issuer: str = 'operator',
        supersedes: str | None = None,
    ) -> dict[str, Any]:
        data = self._load()
        now = utcnow_iso()
        directive = Directive(
            title=title,
            instruction=instruction,
            priority=priority,
            scope=scope,
            constraints=list(constraints or []),
            success_conditions=list(success_conditions or []),
            abort_conditions=list(abort_conditions or []),
            persistence_mode=persistence_mode,
            issuer=issuer,
            supersedes=supersedes,
            created_at=now,
            updated_at=now,
        )
        if supersedes:
            for row in data.get('directives', []):
                if row.get('directive_id') == supersedes and row.get('status') == 'active':
                    row['status'] = 'superseded'
                    row['updated_at'] = now
        data.setdefault('directives', []).append(directive.to_dict())
        data['directives'].sort(key=lambda row: (-int(row.get('priority', 0)), row.get('created_at', '')))
        self._save(data)
        return directive.to_dict()

    def complete(self, directive_id: str, *, status: str = 'complete') -> dict[str, Any] | None:
        data = self._load()
        now = utcnow_iso()
        target = None
        for row in data.get('directives', []):
            if row.get('directive_id') == directive_id:
                row['status'] = status
                row['updated_at'] = now
                target = row
                break
        if target is not None:
            self._save(data)
        return target

    def get(self, directive_id: str) -> dict[str, Any] | None:
        for row in self._load().get('directives', []):
            if row.get('directive_id') == directive_id:
                return row
        return None

    def active(self) -> list[dict[str, Any]]:
        rows = [row for row in self._load().get('directives', []) if row.get('status') == 'active']
        rows.sort(key=lambda row: (-int(row.get('priority', 0)), row.get('created_at', '')))
        return rows

    def stats(self) -> dict[str, Any]:
        directives = self._load().get('directives', [])
        counts: dict[str, int] = {}
        for row in directives:
            counts[row.get('status', 'unknown')] = counts.get(row.get('status', 'unknown'), 0) + 1
        active = [row for row in directives if row.get('status') == 'active']
        active.sort(key=lambda row: (-int(row.get('priority', 0)), row.get('created_at', '')))
        return {
            'directive_count': len(directives),
            'status_counts': dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            'active_directive_count': len(active),
            'active_directives': active[:20],
        }
