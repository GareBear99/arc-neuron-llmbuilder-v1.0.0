from __future__ import annotations
import json, uuid
from pathlib import Path
from arc_lang.core.db import connect
from arc_lang.core.models import BatchImportRequest, BatchExportRequest, utcnow, LanguageSubmissionRequest, ManualLineageRequest, AliasUpsertRequest, RelationshipAssertionRequest
from arc_lang.services.onboarding import submit_language
from arc_lang.services.manual_lineage import add_custom_lineage
from arc_lang.services.aliases import upsert_language_alias
from arc_lang.services.relationships import add_relationship_assertion


def _record(mode: str, object_type: str, path: str, dry_run: bool, count: int, status: str, notes: list[str]) -> str:
    run_id = f"batch_{mode}_{uuid.uuid4().hex[:10]}"
    with connect() as conn:
        conn.execute("INSERT INTO batch_io_runs (run_id, mode, object_type, path, dry_run, record_count, status, notes_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, mode, object_type, path, 1 if dry_run else 0, count, status, json.dumps(notes, ensure_ascii=False), utcnow()))
        conn.commit()
    return run_id


def batch_import(req: BatchImportRequest) -> dict:
    """Batch-import language submissions, aliases, lineage assertions, or relationships from a JSON file."""
    payload = json.loads(Path(req.input_path).read_text(encoding='utf-8'))
    items = payload.get('items', payload if isinstance(payload, list) else [])
    results = []
    for item in items:
        if req.object_type == 'language_submissions':
            res = {'ok': True, 'dry_run': True, 'preview': item} if req.dry_run else submit_language(LanguageSubmissionRequest(**item))
        elif req.object_type == 'custom_lineage':
            res = {'ok': True, 'dry_run': True, 'preview': item} if req.dry_run else add_custom_lineage(ManualLineageRequest(**item))
        elif req.object_type == 'aliases':
            res = {'ok': True, 'dry_run': True, 'preview': item} if req.dry_run else upsert_language_alias(AliasUpsertRequest(**item))
        elif req.object_type == 'relationships':
            res = {'ok': True, 'dry_run': True, 'preview': item} if req.dry_run else add_relationship_assertion(RelationshipAssertionRequest(**item))
        else:
            res = {'ok': False, 'error': 'unsupported_object_type'}
        results.append(res)
    run_id = _record('import', req.object_type, req.input_path, req.dry_run, len(items), 'completed', [])
    return {'ok': True, 'run_id': run_id, 'count': len(items), 'results': results}


def batch_export(req: BatchExportRequest) -> dict:
    """Batch-export languages, aliases, relationships, or a full lineage bundle to a JSON file."""
    out = {'object_type': req.object_type, 'items': []}
    with connect() as conn:
        if req.object_type == 'languages':
            q = "SELECT * FROM languages"
            params = []
            if req.language_ids:
                q += f" WHERE language_id IN ({','.join('?' for _ in req.language_ids)})"
                params = req.language_ids
            out['items'] = [dict(r) for r in conn.execute(q, params).fetchall()]
        elif req.object_type == 'aliases':
            q = "SELECT * FROM language_aliases"
            params = []
            if req.language_ids:
                q += f" WHERE language_id IN ({','.join('?' for _ in req.language_ids)})"
                params = req.language_ids
            out['items'] = [dict(r) for r in conn.execute(q, params).fetchall()]
        elif req.object_type == 'relationships':
            out['items'] = [dict(r) for r in conn.execute("SELECT * FROM relationship_assertions ORDER BY relation").fetchall()]
        elif req.object_type == 'lineage_bundle':
            q = "SELECT * FROM languages"
            params = []
            if req.language_ids:
                q += f" WHERE language_id IN ({','.join('?' for _ in req.language_ids)})"
                params = req.language_ids
            langs = [dict(r) for r in conn.execute(q, params).fetchall()]
            ids = [x['language_id'] for x in langs]
            aliases = [dict(r) for r in conn.execute(f"SELECT * FROM language_aliases WHERE language_id IN ({','.join('?' for _ in ids)})", ids).fetchall()] if ids else []
            out['items'] = {'languages': langs, 'aliases': aliases}
            if req.include_provenance:
                out['provenance'] = [dict(r) for r in conn.execute(f"SELECT * FROM provenance_records WHERE record_id IN ({','.join('?' for _ in ids)})", ids).fetchall()] if ids else []
    Path(req.output_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    record_count = len(out['items']) if isinstance(out['items'], list) else len(out['items'].get('languages', []))
    run_id = _record('export', req.object_type, req.output_path, False, record_count, 'completed', [])
    return {'ok': True, 'run_id': run_id, 'output_path': req.output_path, 'object_type': req.object_type}


def list_batch_runs(mode: str | None = None, object_type: str | None = None) -> dict:
    """List batch import/export run records, optionally filtered by mode and object_type."""
    q = "SELECT * FROM batch_io_runs"
    params = []
    clauses = []
    if mode:
        clauses.append('mode=?')
        params.append(mode)
    if object_type:
        clauses.append('object_type=?')
        params.append(object_type)
    if clauses:
        q += ' WHERE ' + ' AND '.join(clauses)
    q += ' ORDER BY created_at DESC'
    with connect() as conn:
        items = [dict(r) for r in conn.execute(q, params).fetchall()]
    return {'ok': True, 'count': len(items), 'items': items}
