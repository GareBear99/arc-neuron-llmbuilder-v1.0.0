from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EmbeddedArchiveRef, utcnow_iso


class EmbeddedFixArchive:
    """Archive-visible mirror of selected FixNet dossiers.

    This stores immutable fixpack json artifacts and tracks last-sync metadata.
    While a fix remains live in front memory, sync_metadata() can update the index
    with last_sync_at and optional retirement information without rewriting the pack.
    """

    def __init__(self, runtime_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.fixnet_dir = self.runtime_root / '.arc_lucifer' / 'fixnet'
        self.embedded_dir = self.fixnet_dir / 'embedded_archive'
        self.embedded_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.fixnet_dir / 'embedded_index.json'
        if not self.index_path.exists():
            self.index_path.write_text(json.dumps({}, indent=2, sort_keys=True), encoding='utf-8')

    def _load_index(self) -> dict[str, Any]:
        return json.loads(self.index_path.read_text(encoding='utf-8'))

    def _save_index(self, index: dict[str, Any]) -> None:
        self.index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding='utf-8')

    def embed(self, *, fix_id: str, payload: dict[str, Any], archive_branch_id: str = 'archive_branch_main') -> dict[str, Any]:
        now = utcnow_iso()
        pack_id = f'fixpack_{fix_id[:8]}_{now.replace(":", "-")}.json'
        out = self.embedded_dir / pack_id
        envelope = {
            'kind': 'fixnet_embedded_archive',
            'fix_id': fix_id,
            'archive_branch_id': archive_branch_id,
            'embedded_at': now,
            'payload': payload,
        }
        out.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding='utf-8')
        ref = EmbeddedArchiveRef(
            fix_id=fix_id,
            archive_branch_id=archive_branch_id,
            archive_pack_id=pack_id,
            early_merge_at=now,
            last_sync_at=now,
        )
        index = self._load_index()
        index[fix_id] = {**ref.to_dict(), 'path': str(out)}
        self._save_index(index)
        return {'archive_ref': ref.to_dict(), 'path': str(out)}


    def sync_metadata(self, fix_id: str, *, status: str = 'live', retirement_at: str | None = None, remote_ref: dict[str, Any] | None = None) -> dict[str, Any]:
        index = self._load_index()
        if fix_id not in index:
            raise ValueError(f'unknown embedded fix_id: {fix_id}')
        now = utcnow_iso()
        row = dict(index[fix_id])
        row['last_sync_at'] = now
        row['source_status'] = status
        if retirement_at:
            row['retirement_at'] = retirement_at
        if remote_ref is not None:
            row['remote_ref'] = remote_ref
        index[fix_id] = row
        self._save_index(index)
        return row

    def retire(self, fix_id: str, *, retirement_at: str | None = None) -> dict[str, Any]:
        return self.sync_metadata(fix_id, status='retired', retirement_at=retirement_at or utcnow_iso())

    def index(self) -> dict[str, Any]:
        return self._load_index()
