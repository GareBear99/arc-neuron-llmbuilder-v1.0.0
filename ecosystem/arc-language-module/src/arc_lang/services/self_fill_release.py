from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import uuid
import shutil
import zipfile
from pathlib import Path
from typing import Any

from arc_lang.core.config import ROOT, DB_PATH
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow
from arc_lang.services.self_fill import scan_self_fill_gaps
from arc_lang.services.self_fill_arbitration import promote_arbitrated_self_fill_winners
from arc_lang.services.self_fill_sources import run_approved_source_import_bootstrap

ARTIFACTS_DIR = ROOT / 'artifacts'
MANIFEST_DIR = ARTIFACTS_DIR / 'release_manifests'
LEDGER_DIR = ARTIFACTS_DIR / 'omnibinary'
ARCHIVE_DIR = ARTIFACTS_DIR / 'archives'
SNAPSHOT_DIR = ARTIFACTS_DIR / 'snapshots'
REPORT_DIR = ROOT / 'docs'
for d in (MANIFEST_DIR, LEDGER_DIR, ARCHIVE_DIR, SNAPSHOT_DIR, REPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sign_manifest(data: bytes, signing_key: str | None) -> dict[str, Any]:
    if signing_key:
        sig = hmac.new(signing_key.encode('utf-8'), data, hashlib.sha256).digest()
        return {
            'signature_type': 'hmac-sha256',
            'key_hint': 'operator-supplied',
            'signature_b64': base64.b64encode(sig).decode('ascii'),
        }
    digest = hashlib.sha256(data).digest()
    return {
        'signature_type': 'sha256-integrity-only',
        'key_hint': 'none',
        'signature_b64': base64.b64encode(digest).decode('ascii'),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _record_artifact(conn, release_run_id: str, artifact_kind: str, path: Path) -> None:
    conn.execute(
        'INSERT INTO self_fill_release_artifacts (artifact_id, release_run_id, artifact_kind, file_path, sha256, bytes_size, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (
            f'sfra_{uuid.uuid4().hex[:12]}',
            release_run_id,
            artifact_kind,
            str(path),
            _sha256_path(path),
            path.stat().st_size,
            utcnow(),
        ),
    )


def run_recurring_self_fill_release(
    *,
    mode: str = 'recurring_operator_pipeline',
    min_score: float = 0.35,
    reviewer: str = 'self_fill_release_pipeline',
    signing_key: str | None = None,
) -> dict[str, Any]:
    release_run_id = f'sfr_{uuid.uuid4().hex[:12]}'
    created_at = utcnow()

    gap_scan = scan_self_fill_gaps(stage_candidates=True)
    import_bootstrap = run_approved_source_import_bootstrap()
    promotion = promote_arbitrated_self_fill_winners(min_score=min_score, reviewer=reviewer)

    import_results = import_bootstrap.get('results', {})
    if isinstance(import_results, dict):
        import_items = list(import_results.values())
    else:
        import_items = list(import_results or [])

    manifest = {
        'release_run_id': release_run_id,
        'mode': mode,
        'created_at': created_at,
        'pipeline': {
            'gap_scan_run_ids': [r.get('scan_run_id') for r in gap_scan.get('results', [])],
            'import_run_ids': [r.get('import_run_id') for r in import_items],
            'arbitration_run_id': promotion.get('arbitration_run_id'),
        },
        'summary': {
            'gap_scan_languages': len(gap_scan.get('results', [])),
            'import_sources': len(import_items),
            'promoted_count': promotion.get('promoted_count', 0),
            'skipped_count': promotion.get('skipped_count', 0),
            'arbitration_summary': promotion.get('summary', {}),
        },
        'promotion_candidates': [
            {
                'decision_id': item['decision_id'],
                'candidate_id': item['candidate_id'],
                'result_ok': bool(item['result'].get('ok')),
            }
            for item in promotion.get('promoted', [])
        ],
    }
    manifest_bytes = _canonical_bytes(manifest)
    manifest['manifest_sha256'] = _sha256_bytes(manifest_bytes)
    signature_payload = _sign_manifest(_canonical_bytes(manifest), signing_key or os.getenv('ARC_LANG_SIGNING_KEY'))
    manifest['signature'] = signature_payload

    manifest_path = MANIFEST_DIR / f'{release_run_id}.manifest.json'
    signature_path = MANIFEST_DIR / f'{release_run_id}.manifest.sig.json'
    _write_json(manifest_path, manifest)
    _write_json(signature_path, signature_payload)

    ledger_payload = {
        'format': 'omnibinary-learning-ledger-v1',
        'release_run_id': release_run_id,
        'created_at': created_at,
        'manifest_sha256': manifest['manifest_sha256'],
        'promoted_candidate_ids': [item['candidate_id'] for item in promotion.get('promoted', [])],
        'source_import_run_ids': [r.get('import_run_id') for r in import_items],
        'scan_run_ids': [r.get('scan_run_id') for r in gap_scan.get('results', [])],
    }
    ledger_path = LEDGER_DIR / f'{release_run_id}.obin'
    ledger_path.write_bytes(_canonical_bytes(ledger_payload))

    snapshot_path = SNAPSHOT_DIR / f'{release_run_id}.arc_language.snapshot.db'
    shutil.copy2(DB_PATH, snapshot_path)

    archive_path = ARCHIVE_DIR / f'{release_run_id}.arcrar.zip'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_path, arcname=f'release/{manifest_path.name}')
        zf.write(signature_path, arcname=f'release/{signature_path.name}')
        zf.write(ledger_path, arcname=f'release/{ledger_path.name}')
        zf.write(snapshot_path, arcname=f'release/{snapshot_path.name}')
        # Include a human-readable report copy
        report_path = REPORT_DIR / f'{release_run_id}.release_report.json'
        _write_json(report_path, {
            'release_run_id': release_run_id,
            'mode': mode,
            'created_at': created_at,
            'summary': manifest['summary'],
            'manifest_path': str(manifest_path),
            'signature_path': str(signature_path),
            'ledger_path': str(ledger_path),
            'archive_path': str(archive_path),
            'snapshot_path': str(snapshot_path),
        })
        zf.write(report_path, arcname=f'release/{report_path.name}')

    summary = {
        'promoted_count': promotion.get('promoted_count', 0),
        'skipped_count': promotion.get('skipped_count', 0),
        'manifest_sha256': manifest['manifest_sha256'],
        'signature_type': signature_payload['signature_type'],
    }
    with connect() as conn:
        conn.execute(
            'INSERT INTO self_fill_release_runs (release_run_id, mode, manifest_path, signature_path, ledger_path, archive_path, summary_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (release_run_id, mode, str(manifest_path), str(signature_path), str(ledger_path), str(archive_path), json.dumps(summary, ensure_ascii=False, sort_keys=True), created_at),
        )
        for kind, path in [('manifest', manifest_path), ('signature', signature_path), ('ledger', ledger_path), ('snapshot', snapshot_path), ('archive', archive_path)]:
            _record_artifact(conn, release_run_id, kind, path)
        conn.commit()

    return {
        'ok': True,
        'release_run_id': release_run_id,
        'manifest_path': str(manifest_path),
        'signature_path': str(signature_path),
        'ledger_path': str(ledger_path),
        'archive_path': str(archive_path),
        'snapshot_path': str(snapshot_path),
        'summary': summary,
    }


def list_self_fill_release_runs(limit: int = 50) -> dict[str, Any]:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_release_runs ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['summary'] = json.loads(row.pop('summary_json') or '{}')
    return {'ok': True, 'results': rows}


def list_self_fill_release_artifacts(release_run_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    with connect() as conn:
        if release_run_id:
            rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_release_artifacts WHERE release_run_id = ? ORDER BY created_at DESC LIMIT ?', (release_run_id, limit)).fetchall()]
        else:
            rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_release_artifacts ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    return {'ok': True, 'results': rows}
