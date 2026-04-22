
from __future__ import annotations
import csv
import hashlib
import json
import os
import uuid
import zipfile
from pathlib import Path
from arc_lang.core.db import connect
from arc_lang.core.models import AcquisitionJobRequest, StagedAssetRequest, ValidationReportRequest, IngestionWorkspaceExportRequest, utcnow
from arc_lang.core.config import INGESTION_WORKSPACE_DIR


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def plan_acquisition_job(req: AcquisitionJobRequest) -> dict:
    """Create a new acquisition job for a named corpus manifest entry."""
    with connect() as conn:
        row = conn.execute('SELECT * FROM corpus_manifests WHERE corpus_name=?', (req.corpus_name,)).fetchone()
        if not row:
            return {'ok': False, 'error': 'corpus_manifest_not_found', 'corpus_name': req.corpus_name}
        manifest = dict(row)
        outdir = Path(req.output_dir) if req.output_dir else INGESTION_WORKSPACE_DIR / req.corpus_name.replace(' ', '_')
        outdir.mkdir(parents=True, exist_ok=True)
        now = utcnow()
        job_id = f"acq_{uuid.uuid4().hex[:10]}"
        conn.execute(
            'INSERT INTO acquisition_jobs (job_id, corpus_name, corpus_kind, stage_name, output_dir, acquisition_status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (job_id, manifest['corpus_name'], manifest.get('corpus_kind'), req.stage_name, str(outdir), manifest.get('acquisition_status', 'external_required'), req.notes, now, now),
        )
        conn.commit()
    return {'ok': True, 'job_id': job_id, 'corpus_name': req.corpus_name, 'output_dir': str(outdir), 'manifest': manifest}


def record_staged_asset(req: StagedAssetRequest) -> dict:
    """Record a staged file asset for an existing acquisition job, computing SHA-256 and file size."""
    path = Path(req.file_path)
    if not path.exists():
        return {'ok': False, 'error': 'file_not_found', 'file_path': req.file_path}
    size = path.stat().st_size
    digest = _sha256(path)
    now = utcnow()
    asset_id = f"asset_{uuid.uuid4().hex[:10]}"
    with connect() as conn:
        job = conn.execute('SELECT * FROM acquisition_jobs WHERE job_id=?', (req.job_id,)).fetchone()
        if not job:
            return {'ok': False, 'error': 'acquisition_job_not_found', 'job_id': req.job_id}
        conn.execute(
            'INSERT INTO staged_assets (asset_id, job_id, file_path, asset_kind, file_size_bytes, sha256, status, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (asset_id, req.job_id, str(path), req.asset_kind, size, digest, 'recorded', req.notes, now),
        )
        conn.commit()
    return {'ok': True, 'asset_id': asset_id, 'job_id': req.job_id, 'file_path': str(path), 'file_size_bytes': size, 'sha256': digest}


def validate_staged_asset(req: ValidationReportRequest) -> dict:
    """Validate a staged asset file: detect its kind and compare against the expected kind."""
    path = Path(req.file_path)
    if not path.exists():
        return {'ok': False, 'error': 'file_not_found', 'file_path': req.file_path}
    suffix = path.suffix.lower().lstrip('.') or 'unknown'
    detected_kind = 'zip' if zipfile.is_zipfile(path) else suffix
    status = 'passed'
    notes = []
    summary = {'bytes': path.stat().st_size, 'lines': None, 'top_level_keys': None, 'zip_entries': None}
    try:
        if detected_kind == 'json':
            payload = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(payload, dict):
                summary['top_level_keys'] = sorted(payload.keys())[:25]
            elif isinstance(payload, list):
                summary['top_level_keys'] = ['<list>']
        elif detected_kind == 'csv':
            with path.open('r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)
            summary['lines'] = len(rows)
            if rows:
                summary['top_level_keys'] = rows[0]
        elif detected_kind == 'zip':
            with zipfile.ZipFile(path, 'r') as zf:
                summary['zip_entries'] = zf.namelist()[:50]
        else:
            notes.append('no_deep_validator_for_detected_kind')
    except (UnicodeDecodeError, json.JSONDecodeError, csv.Error, zipfile.BadZipFile, OSError) as e:
        status = 'failed'
        notes.append(f'parse_error:{type(e).__name__}')
    if req.expected_kind != 'any' and detected_kind != req.expected_kind:
        status = 'failed'
        notes.append('expected_kind_mismatch')
    report_id = f"val_{uuid.uuid4().hex[:10]}"
    with connect() as conn:
        conn.execute(
            'INSERT INTO validation_reports (report_id, file_path, expected_kind, expected_source_name, detected_kind, status, summary_json, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (report_id, str(path), req.expected_kind, req.expected_source_name, detected_kind, status, json.dumps(summary, ensure_ascii=False), ';'.join(notes + ([req.notes] if req.notes else [])), utcnow()),
        )
        conn.commit()
    return {'ok': status == 'passed', 'report_id': report_id, 'status': status, 'detected_kind': detected_kind, 'summary': summary, 'notes': notes}


def list_acquisition_jobs(corpus_name: str | None = None) -> dict:
    """List acquisition jobs, optionally filtered by corpus_name."""
    q = 'SELECT * FROM acquisition_jobs'
    params = []
    if corpus_name:
        q += ' WHERE corpus_name=?'
        params.append(corpus_name)
    q += ' ORDER BY created_at DESC'
    with connect() as conn:
        items = [dict(r) for r in conn.execute(q, params).fetchall()]
    return {'ok': True, 'count': len(items), 'items': items}


def list_validation_reports(limit: int = 50) -> dict:
    """List staged-asset validation reports, most recent first."""
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM validation_reports ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['summary'] = json.loads(row.pop('summary_json') or '{}')
    return {'ok': True, 'count': len(rows), 'items': rows}


def export_ingestion_workspace(req: IngestionWorkspaceExportRequest) -> dict:
    """Export the full ingestion workspace bundle (manifests, runs, validation reports, jobs) to JSON."""
    bundle = {'ok': True, 'workspace': {}}
    with connect() as conn:
        if req.include_corpus_manifests:
            bundle['workspace']['corpus_manifests'] = [dict(r) for r in conn.execute('SELECT * FROM corpus_manifests ORDER BY corpus_name').fetchall()]
        if req.include_import_runs:
            bundle['workspace']['import_runs'] = [dict(r) for r in conn.execute('SELECT * FROM import_runs ORDER BY created_at DESC').fetchall()]
        if req.include_batch_runs:
            bundle['workspace']['batch_runs'] = [dict(r) for r in conn.execute('SELECT * FROM batch_io_runs ORDER BY created_at DESC').fetchall()]
        if req.include_validation_reports:
            vals = [dict(r) for r in conn.execute('SELECT * FROM validation_reports ORDER BY created_at DESC').fetchall()]
            for v in vals:
                v['summary'] = json.loads(v.pop('summary_json') or '{}')
            bundle['workspace']['validation_reports'] = vals
        if req.include_jobs:
            bundle['workspace']['acquisition_jobs'] = [dict(r) for r in conn.execute('SELECT * FROM acquisition_jobs ORDER BY created_at DESC').fetchall()]
            bundle['workspace']['staged_assets'] = [dict(r) for r in conn.execute('SELECT * FROM staged_assets ORDER BY created_at DESC').fetchall()]
    summary = {
        'corpus_manifests': len(bundle['workspace'].get('corpus_manifests', [])),
        'import_runs': len(bundle['workspace'].get('import_runs', [])),
        'batch_runs': len(bundle['workspace'].get('batch_runs', [])),
        'validation_reports': len(bundle['workspace'].get('validation_reports', [])),
        'acquisition_jobs': len(bundle['workspace'].get('acquisition_jobs', [])),
        'staged_assets': len(bundle['workspace'].get('staged_assets', [])),
    }
    bundle['summary'] = summary
    out = Path(req.output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
    export_id = f"iwx_{uuid.uuid4().hex[:10]}"
    with connect() as conn:
        conn.execute('INSERT INTO ingestion_workspace_exports (export_id, output_path, summary_json, created_at) VALUES (?, ?, ?, ?)', (export_id, str(out), json.dumps(summary, ensure_ascii=False), utcnow()))
        conn.commit()
    return {'ok': True, 'export_id': export_id, 'output_path': str(out), 'summary': summary}
