from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from fixnet.models import utcnow_iso


@dataclass(slots=True)
class ToolTrustProfile:
    tool_name: str
    trust_level: str = "unknown"
    success_count: int = 0
    failure_count: int = 0
    last_outcome: str = "unknown"
    notes: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ToolTrustRegistry:
    def __init__(self, runtime_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.dir = self.runtime_root / '.arc_lucifer' / 'trust'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / 'profiles.json'
        if not self.path.exists():
            self.path.write_text(json.dumps({}, indent=2, sort_keys=True), encoding='utf-8')

    def _load(self) -> dict[str, dict[str, Any]]:
        return json.loads(self.path.read_text(encoding='utf-8'))

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')

    def get(self, tool_name: str) -> dict[str, Any] | None:
        return self._load().get(tool_name)

    def upsert(self, tool_name: str, *, notes: str = '', evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        data = self._load()
        current = data.get(tool_name, {})
        profile = ToolTrustProfile(
            tool_name=tool_name,
            trust_level=current.get('trust_level', 'unknown'),
            success_count=int(current.get('success_count', 0)),
            failure_count=int(current.get('failure_count', 0)),
            last_outcome=current.get('last_outcome', 'unknown'),
            notes=notes or current.get('notes', ''),
            evidence=dict(evidence or current.get('evidence', {})),
        )
        data[tool_name] = profile.to_dict()
        self._save(data)
        return data[tool_name]

    def record_outcome(self, tool_name: str, *, succeeded: bool, notes: str = '', evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        data = self._load()
        current = data.get(tool_name, {})
        success_count = int(current.get('success_count', 0)) + (1 if succeeded else 0)
        failure_count = int(current.get('failure_count', 0)) + (0 if succeeded else 1)
        total = success_count + failure_count
        success_rate = success_count / total if total else 0.0
        if success_rate >= 0.9 and total >= 5:
            trust_level = 'high'
        elif success_rate >= 0.6 and total >= 3:
            trust_level = 'medium'
        elif failure_count >= 3 and success_rate < 0.4:
            trust_level = 'degraded'
        else:
            trust_level = 'experimental'
        profile = ToolTrustProfile(
            tool_name=tool_name,
            trust_level=trust_level,
            success_count=success_count,
            failure_count=failure_count,
            last_outcome='success' if succeeded else 'failure',
            notes=notes or current.get('notes', ''),
            evidence=dict(evidence or current.get('evidence', {})),
        )
        data[tool_name] = profile.to_dict()
        self._save(data)
        return data[tool_name]

    def stats(self) -> dict[str, Any]:
        data = self._load()
        tiers: dict[str, int] = {}
        for row in data.values():
            tiers[row.get('trust_level', 'unknown')] = tiers.get(row.get('trust_level', 'unknown'), 0) + 1
        return {
            'profile_count': len(data),
            'tiers': dict(sorted(tiers.items(), key=lambda kv: (-kv[1], kv[0]))),
            'profiles': list(sorted(data.values(), key=lambda row: row.get('tool_name', ''))),
        }
