
from __future__ import annotations
import json, uuid
from pathlib import Path
from arc_lang.core.db import connect
from arc_lang.core.models import ConflictReviewExportRequest, utcnow
from arc_lang.services.arbitration import resolve_effective_lineage


def export_conflict_review_bundle(req: ConflictReviewExportRequest) -> dict:
    """Export an arbitration conflict review bundle for specified languages to a JSON file."""
    with connect() as conn:
        if req.language_ids:
            langs = req.language_ids
        else:
            langs = [r['language_id'] for r in conn.execute("SELECT language_id FROM languages ORDER BY language_id").fetchall()]
    bundles = []
    conflicts = 0
    for language_id in langs:
        eff = resolve_effective_lineage(language_id)
        if not eff.get('ok'):
            continue
        current_conflicts = eff.get('conflicts', [])
        if req.include_unreviewed_only and not current_conflicts:
            continue
        bundles.append({'language_id': language_id, 'effective_truth': eff.get('effective_truth', {}), 'conflicts': current_conflicts})
        conflicts += len(current_conflicts)
    summary = {'languages_considered': len(langs), 'bundles': len(bundles), 'conflicts': conflicts}
    Path(req.output_path).write_text(json.dumps({'summary': summary, 'items': bundles}, ensure_ascii=False, indent=2), encoding='utf-8')
    export_id = f"conflict_export_{uuid.uuid4().hex[:10]}"
    with connect() as conn:
        conn.execute("INSERT INTO conflict_review_exports (export_id, output_path, language_ids_json, conflict_count, summary_json, created_at) VALUES (?, ?, ?, ?, ?, ?)", (export_id, req.output_path, json.dumps(req.language_ids, ensure_ascii=False), conflicts, json.dumps(summary, ensure_ascii=False), utcnow()))
        conn.commit()
    return {'ok': True, 'export_id': export_id, 'output_path': req.output_path, 'summary': summary}


def list_conflict_review_exports(limit: int = 20) -> dict:
    """List conflict review export records, most recent first."""
    with connect() as conn:
        items = [dict(r) for r in conn.execute("SELECT * FROM conflict_review_exports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]
    return {'ok': True, 'count': len(items), 'items': items}
