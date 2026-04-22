from __future__ import annotations

"""Archive pack helpers for immutable .arcpack bundles."""

import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Mapping, Any

from .records import MemoryRecord


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ArchivePack:
    archive_path: Path
    manifest: dict

    @classmethod
    def create(
        cls,
        archive_dir: Path,
        records: Iterable[MemoryRecord],
        pack_name: str | None = None,
        *,
        manifest_extras: Mapping[str, Any] | None = None,
    ) -> "ArchivePack":
        archive_dir.mkdir(parents=True, exist_ok=True)
        rows: List[dict] = [record.to_dict() for record in records]
        if not rows:
            raise ValueError('cannot create an archive pack with no records')
        payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows).encode('utf-8')
        payload_sha256 = hashlib.sha256(payload).hexdigest()
        first_created = min(row['created_at'] for row in rows)
        last_created = max(row['created_at'] for row in rows)
        archive_name = pack_name or f"archive_{first_created[:10]}_{last_created[:10]}.arcpack"
        archive_path = archive_dir / archive_name
        manifest = {
            'version': 2,
            'created_at': utcnow_iso(),
            'record_count': len(rows),
            'first_created_at': first_created,
            'last_created_at': last_created,
            'event_ids': [row['event_id'] for row in rows],
            'payload_sha256': payload_sha256,
        }
        if manifest_extras:
            manifest.update(dict(manifest_extras))
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', json.dumps(manifest, indent=2, sort_keys=True))
            zf.writestr('events.jsonl', payload)
        return cls(archive_path=archive_path, manifest=manifest)

    @classmethod
    def open(cls, archive_path: Path) -> "ArchivePack":
        with zipfile.ZipFile(archive_path, 'r') as zf:
            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        return cls(archive_path=archive_path, manifest=manifest)

    def load_records(self) -> List[dict]:
        with zipfile.ZipFile(self.archive_path, 'r') as zf:
            rows = zf.read('events.jsonl').decode('utf-8').splitlines()
        return [json.loads(row) for row in rows if row.strip()]
