from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from .models import FixRecord, FixEdge, RelationshipType, utcnow_iso


class FixLedger:
    """Durable fix storage and semantic lineage graph.

    ARC-side equivalent of LuciferAI's RelevanceDictionary.

    Storage layout (workspace-root relative):
      .arc_lucifer/fixnet/
        fixes.json           (fix_id -> FixRecord)
        edges.json           (list[FixEdge])
        remote_refs.json     (cached remote metadata)
    """

    def __init__(self, runtime_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.fixnet_dir = self.runtime_root / '.arc_lucifer' / 'fixnet'
        self.fixnet_dir.mkdir(parents=True, exist_ok=True)
        self.fixes_path = self.fixnet_dir / 'fixes.json'
        self.edges_path = self.fixnet_dir / 'edges.json'
        self.remote_refs_path = self.fixnet_dir / 'remote_refs.json'
        if not self.fixes_path.exists():
            self.fixes_path.write_text(json.dumps({}, indent=2, sort_keys=True), encoding='utf-8')
        if not self.edges_path.exists():
            self.edges_path.write_text(json.dumps([], indent=2, sort_keys=True), encoding='utf-8')
        if not self.remote_refs_path.exists():
            self.remote_refs_path.write_text(json.dumps({}, indent=2, sort_keys=True), encoding='utf-8')

    def _load_fixes(self) -> dict[str, dict[str, Any]]:
        return json.loads(self.fixes_path.read_text(encoding='utf-8'))

    def _save_fixes(self, fixes: dict[str, dict[str, Any]]) -> None:
        self.fixes_path.write_text(json.dumps(fixes, indent=2, sort_keys=True), encoding='utf-8')

    def _load_edges(self) -> list[dict[str, Any]]:
        return json.loads(self.edges_path.read_text(encoding='utf-8'))

    def _save_edges(self, edges: list[dict[str, Any]]) -> None:
        self.edges_path.write_text(json.dumps(edges, indent=2, sort_keys=True), encoding='utf-8')

    def upsert_fix(self, record: FixRecord) -> FixRecord:
        fixes = self._load_fixes()
        existing = fixes.get(record.fix_id)
        if existing:
            record.created_at = existing.get('created_at', record.created_at)
        record.updated_at = utcnow_iso()
        fixes[record.fix_id] = record.to_dict()
        self._save_fixes(fixes)
        return record

    def get_fix(self, fix_id: str) -> dict[str, Any] | None:
        return self._load_fixes().get(fix_id)

    def list_fixes(self) -> list[dict[str, Any]]:
        fixes = self._load_fixes()
        rows = list(fixes.values())
        rows.sort(key=lambda r: (r.get('updated_at', ''), r.get('created_at', '')), reverse=True)
        return rows

    def add_edge(self, parent_fix_id: str, child_fix_id: str, relationship: RelationshipType) -> FixEdge:
        edge = FixEdge(parent_fix_id=parent_fix_id, child_fix_id=child_fix_id, relationship=relationship)
        edges = self._load_edges()
        # prevent exact duplicates
        for row in edges:
            if row.get('parent_fix_id') == parent_fix_id and row.get('child_fix_id') == child_fix_id and row.get('relationship') == relationship:
                return FixEdge(**row)
        edges.append(edge.to_dict())
        self._save_edges(edges)
        return edge

    def list_edges(self) -> list[dict[str, Any]]:
        edges = self._load_edges()
        edges.sort(key=lambda r: r.get('created_at', ''), reverse=True)
        return edges

    def related_fixes(self, fix_id: str) -> list[dict[str, Any]]:
        fixes = self._load_fixes()
        edges = self._load_edges()
        related_ids = set()
        for e in edges:
            if e.get('parent_fix_id') == fix_id:
                related_ids.add(e.get('child_fix_id'))
            if e.get('child_fix_id') == fix_id:
                related_ids.add(e.get('parent_fix_id'))
        return [fixes[rid] for rid in related_ids if rid in fixes]

    def cache_remote_ref(self, fix_id: str, ref: dict[str, Any]) -> None:
        data = json.loads(self.remote_refs_path.read_text(encoding='utf-8'))
        data[fix_id] = dict(ref)
        self.remote_refs_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')

    def remote_refs(self) -> dict[str, Any]:
        return json.loads(self.remote_refs_path.read_text(encoding='utf-8'))
