from __future__ import annotations
import json
import uuid
from pathlib import Path
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow
from arc_lang.services.stats import get_graph_stats
from arc_lang.services.manifests import list_backend_manifests, list_corpus_manifests


def build_implementation_matrix(output_path: str | None = None) -> dict:
    """Generate an implementation matrix report separating package-owned from external dependencies."""
    stats = get_graph_stats().get('counts', {})
    backends = list_backend_manifests().get('results', [])
    corpora = list_corpus_manifests().get('results', [])
    summary = {
        'implemented_in_package': {
            'language_graph': True,
            'lineage_graph': True,
            'runtime_routing': True,
            'provider_health': True,
            'transliteration_profiles': stats.get('transliteration_profiles', 0),
            'pronunciation_profiles': stats.get('pronunciation_profiles', 0),
            'phonology_profiles': stats.get('phonology_profiles', 0),
            'semantic_concepts': stats.get('semantic_concepts', 0),
            'variants': stats.get('language_variants', 0)
        },
        'seeded_or_partial': {
            'phrase_translation': stats.get('phrase_translations', 0),
            'phonology_hint_only': True,
            'morphology_assist_only': True,
            'bridge_backends_declared': [b['provider_name'] for b in backends if b.get('execution_mode') not in {'local', 'optional_local'}]
        },
        'external_data_required': [c['corpus_name'] for c in corpora if c.get('acquisition_status') != 'installed'],
        'external_runtime_required': [b['provider_name'] for b in backends if b.get('execution_mode') in {'external_bridge', 'optional_external'}]
    }
    report_id = f"imatrix_{uuid.uuid4().hex[:16]}"
    now = utcnow()
    with connect() as conn:
        conn.execute('INSERT INTO implementation_matrix_reports (report_id, output_path, summary_json, created_at) VALUES (?, ?, ?, ?)', (report_id, output_path, json.dumps(summary, ensure_ascii=False), now))
        conn.commit()
    if output_path:
        Path(output_path).write_text(json.dumps({'ok': True, 'report_id': report_id, 'summary': summary}, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'ok': True, 'report_id': report_id, 'summary': summary}


def list_implementation_matrix_reports(limit: int = 20) -> dict:
    """List implementation matrix report records, most recent first."""
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM implementation_matrix_reports ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['summary'] = json.loads(row.pop('summary_json') or '{}')
    return {'ok': True, 'results': rows}
