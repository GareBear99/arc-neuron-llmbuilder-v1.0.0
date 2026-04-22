from __future__ import annotations

import hashlib
import json
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

from arc_lang.core.config import ROOT, DB_PATH
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow

ARTIFACTS_DIR = ROOT / 'artifacts'
REPLAY_DIR = ARTIFACTS_DIR / 'replay_manifests'
COMPACT_DIR = ARTIFACTS_DIR / 'compact_archives'
BACKUP_DIR = ARTIFACTS_DIR / 'db_backups'
for d in (REPLAY_DIR, COMPACT_DIR, BACKUP_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_release_run(release_run_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute('SELECT * FROM self_fill_release_runs WHERE release_run_id = ?', (release_run_id,)).fetchone()
        if not row:
            raise ValueError(f'Unknown release_run_id: {release_run_id}')
        data = dict(row)
        snap = conn.execute("SELECT file_path FROM self_fill_release_artifacts WHERE release_run_id = ? AND artifact_kind = 'snapshot' ORDER BY created_at DESC LIMIT 1", (release_run_id,)).fetchone()
    data['summary'] = json.loads(data.pop('summary_json') or '{}')
    if snap:
        data['snapshot_path'] = snap['file_path']
    return data


def _load_rollback_entry(rollback_id: str | None = None, release_run_id: str | None = None) -> dict[str, Any]:
    if not rollback_id and not release_run_id:
        raise ValueError('rollback_id or release_run_id is required')
    with connect() as conn:
        if rollback_id:
            row = conn.execute('SELECT * FROM self_fill_rollback_index WHERE rollback_id = ?', (rollback_id,)).fetchone()
        else:
            row = conn.execute('SELECT * FROM self_fill_rollback_index WHERE release_run_id = ? ORDER BY created_at DESC LIMIT 1', (release_run_id,)).fetchone()
    if not row:
        raise ValueError('No rollback index entry found')
    return dict(row)


def build_self_fill_replay_manifest(*, rollback_id: str | None = None, release_run_id: str | None = None, verify_hashes: bool = True) -> dict[str, Any]:
    rollback = _load_rollback_entry(rollback_id=rollback_id, release_run_id=release_run_id)
    release = _load_release_run(rollback['release_run_id'])
    snapshot_raw = release.get('snapshot_path') or ''
    paths = {
        'manifest_path': Path(rollback['manifest_path']),
        'archive_path': Path(rollback['archive_path']),
        'ledger_path': Path(rollback['ledger_path']),
        'snapshot_path': Path(snapshot_raw) if snapshot_raw else None,
    }
    verification = {}
    for key, path in paths.items():
        exists = bool(path and path.exists() and path.is_file())
        verification[key] = {'exists': exists, 'path': str(path) if path else ''}
        if exists and verify_hashes:
            verification[key]['sha256'] = _sha256_path(path)
    replay_run_id = f'sfrr_{uuid.uuid4().hex[:12]}'
    payload = {
        'replay_run_id': replay_run_id,
        'rollback_id': rollback['rollback_id'],
        'release_run_id': rollback['release_run_id'],
        'retention_class': rollback['retention_class'],
        'replay_priority': rollback['replay_priority'],
        'created_at': utcnow(),
        'verification': verification,
        'summary': release['summary'],
    }
    out = REPLAY_DIR / f'{replay_run_id}.replay_manifest.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    with connect() as conn:
        conn.execute(
            'INSERT INTO self_fill_replay_runs (replay_run_id, release_run_id, rollback_id, replay_manifest_path, replay_status, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (replay_run_id, rollback['release_run_id'], rollback['rollback_id'], str(out), 'prepared', json.dumps(payload, ensure_ascii=False, sort_keys=True), payload['created_at']),
        )
        conn.commit()
    return {'ok': True, **payload, 'replay_manifest_path': str(out)}


def restore_self_fill_snapshot(*, rollback_id: str | None = None, release_run_id: str | None = None, create_backup: bool = True) -> dict[str, Any]:
    rollback = _load_rollback_entry(rollback_id=rollback_id, release_run_id=release_run_id)
    release = _load_release_run(rollback['release_run_id'])
    snapshot_raw = release.get('snapshot_path') or ''
    snapshot_path = Path(snapshot_raw) if snapshot_raw else None
    if not snapshot_path or not snapshot_path.exists():
        raise FileNotFoundError(f'Snapshot not found for release {rollback["release_run_id"]}: {snapshot_raw}')
    backup_path = None
    if create_backup and DB_PATH.exists():
        backup_path = BACKUP_DIR / f'{rollback["release_run_id"]}.{utcnow().replace(":", "-")}.pre_restore.db'
        shutil.copy2(DB_PATH, backup_path)
    shutil.copy2(snapshot_path, DB_PATH)
    result = {
        'ok': True,
        'release_run_id': rollback['release_run_id'],
        'rollback_id': rollback['rollback_id'],
        'restored_snapshot_path': str(snapshot_path),
        'db_path': str(DB_PATH),
        'backup_path': str(backup_path) if backup_path else None,
        'restored_at': utcnow(),
    }
    return result


def compact_self_fill_release(*, rollback_id: str | None = None, release_run_id: str | None = None) -> dict[str, Any]:
    rollback = _load_rollback_entry(rollback_id=rollback_id, release_run_id=release_run_id)
    release = _load_release_run(rollback['release_run_id'])
    manifest_path = Path(rollback['manifest_path'])
    ledger_path = Path(rollback['ledger_path'])
    archive_path = Path(rollback['archive_path'])
    snapshot_raw = release.get('snapshot_path') or ''
    snapshot_path = Path(snapshot_raw) if snapshot_raw else None
    compaction_id = f'sfrc_{uuid.uuid4().hex[:12]}'
    compact_bundle = COMPACT_DIR / f'{compaction_id}.{rollback["release_run_id"]}.compact.arcrar.zip'
    details = {
        'release_run_id': rollback['release_run_id'],
        'rollback_id': rollback['rollback_id'],
        'retention_class': rollback['retention_class'],
        'created_at': utcnow(),
        'included': [],
        'source_archive_path': str(archive_path),
    }
    with zipfile.ZipFile(compact_bundle, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for label, path in [('manifest', manifest_path), ('ledger', ledger_path), ('snapshot', snapshot_path)]:
            if path and path.exists() and path.is_file():
                zf.write(path, arcname=f'compact/{path.name}')
                details['included'].append({'kind': label, 'path': str(path), 'sha256': _sha256_path(path)})
        compact_report = COMPACT_DIR / f'{compaction_id}.report.json'
        compact_report.write_text(json.dumps(details, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        zf.write(compact_report, arcname=f'compact/{compact_report.name}')
    compact_sha256 = _sha256_path(compact_bundle)
    with connect() as conn:
        conn.execute(
            'INSERT INTO self_fill_compaction_actions (compaction_id, release_run_id, retention_class, compact_bundle_path, compact_sha256, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (compaction_id, rollback['release_run_id'], rollback['retention_class'], str(compact_bundle), compact_sha256, json.dumps(details, ensure_ascii=False, sort_keys=True), details['created_at']),
        )
        policy = conn.execute('SELECT policy_id FROM self_fill_retention_policies WHERE retention_class = ? AND enabled = 1 ORDER BY keep_days ASC LIMIT 1', (rollback['retention_class'],)).fetchone()
        policy_id = policy['policy_id'] if policy else 'unknown_policy'
        conn.execute(
            'INSERT INTO self_fill_retention_actions (action_id, release_run_id, policy_id, retention_class, action_kind, action_status, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (f'sfra_{uuid.uuid4().hex[:12]}', rollback['release_run_id'], policy_id, rollback['retention_class'], 'compact_bundle', 'applied', json.dumps({'compaction_id': compaction_id, 'compact_bundle_path': str(compact_bundle), 'compact_sha256': compact_sha256}, ensure_ascii=False, sort_keys=True), utcnow()),
        )
        conn.commit()
    return {'ok': True, 'compaction_id': compaction_id, 'compact_bundle_path': str(compact_bundle), 'compact_sha256': compact_sha256}


def list_self_fill_replay_runs(limit: int = 100) -> dict[str, Any]:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_replay_runs ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['details'] = json.loads(row.pop('details_json') or '{}')
    return {'ok': True, 'results': rows}


def list_self_fill_compaction_actions(limit: int = 100) -> dict[str, Any]:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_compaction_actions ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['details'] = json.loads(row.pop('details_json') or '{}')
    return {'ok': True, 'results': rows}
