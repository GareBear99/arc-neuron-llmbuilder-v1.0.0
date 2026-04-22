from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fixnet.models import utcnow_iso


class CurriculumMemory:
    def __init__(self, runtime_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.dir = self.runtime_root / '.arc_lucifer' / 'curriculum'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / 'memory.json'
        if not self.path.exists():
            self.path.write_text(json.dumps({'themes': {}, 'skills': {}, 'failure_clusters': {}}, indent=2, sort_keys=True), encoding='utf-8')

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding='utf-8'))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')

    def record(self, *, theme: str, skill: str | None = None, failure_cluster: str | None = None, outcome: str = 'observed', notes: str = '') -> dict[str, Any]:
        data = self._load()
        now = utcnow_iso()
        themes = data.setdefault('themes', {})
        theme_row = themes.setdefault(theme, {'count': 0, 'last_outcome': 'unknown', 'last_seen_at': None, 'notes': ''})
        theme_row['count'] += 1
        theme_row['last_outcome'] = outcome
        theme_row['last_seen_at'] = now
        if notes:
            theme_row['notes'] = notes
        if skill:
            skills = data.setdefault('skills', {})
            row = skills.setdefault(skill, {'count': 0, 'last_outcome': 'unknown', 'last_seen_at': None})
            row['count'] += 1
            row['last_outcome'] = outcome
            row['last_seen_at'] = now
        if failure_cluster:
            clusters = data.setdefault('failure_clusters', {})
            row = clusters.setdefault(failure_cluster, {'count': 0, 'last_outcome': 'unknown', 'last_seen_at': None})
            row['count'] += 1
            row['last_outcome'] = outcome
            row['last_seen_at'] = now
        self._save(data)
        return data

    def stats(self) -> dict[str, Any]:
        data = self._load()
        def _top(section: str) -> list[dict[str, Any]]:
            rows = [dict(name=name, **payload) for name, payload in data.get(section, {}).items()]
            rows.sort(key=lambda row: (-int(row.get('count', 0)), row.get('name', '')))
            return rows[:10]
        return {
            'theme_count': len(data.get('themes', {})),
            'skill_count': len(data.get('skills', {})),
            'failure_cluster_count': len(data.get('failure_clusters', {})),
            'top_themes': _top('themes'),
            'top_skills': _top('skills'),
            'top_failure_clusters': _top('failure_clusters'),
        }
