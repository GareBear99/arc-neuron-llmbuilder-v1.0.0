from __future__ import annotations
import json
import uuid
from pathlib import Path
from arc_lang.core.db import connect
from arc_lang.core.config import BACKEND_MANIFEST_PATH, CORPUS_MANIFEST_PATH
from arc_lang.core.models import utcnow


def seed_manifests(backend_path: str | Path | None = None, corpus_path: str | Path | None = None) -> dict:
    """Seed default backend and corpus manifests from config files."""
    backend_payload = json.loads(Path(backend_path or BACKEND_MANIFEST_PATH).read_text(encoding='utf-8'))
    corpus_payload = json.loads(Path(corpus_path or CORPUS_MANIFEST_PATH).read_text(encoding='utf-8'))
    now = utcnow()
    backend_count = 0
    corpus_count = 0
    with connect() as conn:
        for item in backend_payload.get('manifests', []):
            manifest_id = f"bman_{uuid.uuid5(uuid.NAMESPACE_URL, item['provider_name'] + ':' + item['backend_kind']).hex[:18]}"
            conn.execute(
                """
                INSERT INTO backend_manifests (manifest_id, provider_name, backend_kind, execution_mode, supported_pairs_json, dependency_json, health_policy_json, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(manifest_id) DO UPDATE SET execution_mode=excluded.execution_mode, supported_pairs_json=excluded.supported_pairs_json, dependency_json=excluded.dependency_json, health_policy_json=excluded.health_policy_json, notes=excluded.notes, updated_at=excluded.updated_at
                """,
                (manifest_id, item['provider_name'], item['backend_kind'], item['execution_mode'], json.dumps(item.get('supported_pairs', []), ensure_ascii=False), json.dumps(item.get('dependencies', []), ensure_ascii=False), json.dumps(item.get('health_policy', {}), ensure_ascii=False), item.get('notes', ''), now, now),
            )
            backend_count += 1
        for item in corpus_payload.get('manifests', []):
            manifest_id = f"cman_{uuid.uuid5(uuid.NAMESPACE_URL, item['corpus_name'] + ':' + item['corpus_kind']).hex[:18]}"
            conn.execute(
                """
                INSERT INTO corpus_manifests (manifest_id, corpus_name, corpus_kind, coverage_scope, languages_json, source_name, license_ref, acquisition_status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(manifest_id) DO UPDATE SET coverage_scope=excluded.coverage_scope, languages_json=excluded.languages_json, source_name=excluded.source_name, license_ref=excluded.license_ref, acquisition_status=excluded.acquisition_status, notes=excluded.notes, updated_at=excluded.updated_at
                """,
                (manifest_id, item['corpus_name'], item['corpus_kind'], item['coverage_scope'], json.dumps(item.get('languages', []), ensure_ascii=False), item.get('source_name', 'local'), item.get('license_ref'), item.get('acquisition_status', 'external_required'), item.get('notes', ''), now, now),
            )
            corpus_count += 1
        conn.commit()
    return {'ok': True, 'backend_manifests': backend_count, 'corpus_manifests': corpus_count}


def list_backend_manifests(provider_name: str | None = None) -> dict:
    """List backend manifests, optionally filtered by provider_name."""
    q = 'SELECT * FROM backend_manifests'
    params = []
    if provider_name:
        q += ' WHERE provider_name = ?'
        params.append(provider_name)
    q += ' ORDER BY provider_name'
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(q, tuple(params)).fetchall()]
    for row in rows:
        row['supported_pairs'] = json.loads(row.pop('supported_pairs_json') or '[]')
        row['dependencies'] = json.loads(row.pop('dependency_json') or '[]')
        row['health_policy'] = json.loads(row.pop('health_policy_json') or '{}')
    return {'ok': True, 'results': rows}


def list_corpus_manifests(corpus_kind: str | None = None) -> dict:
    """List corpus manifests, optionally filtered by corpus_kind."""
    q = 'SELECT * FROM corpus_manifests'
    params = []
    if corpus_kind:
        q += ' WHERE corpus_kind = ?'
        params.append(corpus_kind)
    q += ' ORDER BY corpus_name'
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(q, tuple(params)).fetchall()]
    for row in rows:
        row['languages'] = json.loads(row.pop('languages_json') or '[]')
    return {'ok': True, 'results': rows}
