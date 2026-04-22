
from __future__ import annotations
import json, uuid
from pathlib import Path
from arc_lang.core.db import connect
from arc_lang.core.models import CoverageReportRequest, utcnow
from arc_lang.services.governance import get_language_readiness


def build_coverage_report(req: CoverageReportRequest) -> dict:
    """Build a per-language coverage report with gap flags, profile counts, and capability summary."""
    with connect() as conn:
        if req.language_ids:
            q = f"SELECT * FROM languages WHERE language_id IN ({','.join('?' for _ in req.language_ids)}) ORDER BY language_id"
            langs = [dict(r) for r in conn.execute(q, req.language_ids).fetchall()]
        else:
            langs = [dict(r) for r in conn.execute("SELECT * FROM languages ORDER BY language_id").fetchall()]
        items = []
        for lang in langs:
            lid = lang['language_id']

            alias_count = conn.execute("SELECT COUNT(*) AS c FROM language_aliases WHERE language_id=?", (lid,)).fetchone()['c']

            # Alias breakdown by type
            alias_rows = conn.execute(
                "SELECT alias_type, COUNT(*) AS c FROM language_aliases WHERE language_id=? GROUP BY alias_type",
                (lid,),
            ).fetchall()
            alias_by_type = {r['alias_type']: r['c'] for r in alias_rows}

            variant_count = conn.execute("SELECT COUNT(*) AS c FROM language_variants WHERE language_id=?", (lid,)).fetchone()['c']
            script_count = conn.execute("SELECT COUNT(*) AS c FROM language_scripts WHERE language_id=?", (lid,)).fetchone()['c']
            pron_count = conn.execute("SELECT COUNT(*) AS c FROM pronunciation_profiles WHERE language_id=?", (lid,)).fetchone()['c']
            translit_count = conn.execute("SELECT COUNT(*) AS c FROM transliteration_profiles WHERE language_id=?", (lid,)).fetchone()['c']
            phonology_count = conn.execute("SELECT COUNT(*) AS c FROM phonology_profiles WHERE language_id=?", (lid,)).fetchone()['c']
            concept_count = conn.execute("SELECT COUNT(*) AS c FROM concept_links WHERE target_type='language' AND target_id=?", (lid,)).fetchone()['c']

            # Lineage edges: both outbound and inbound
            lineage_edge_count = conn.execute(
                "SELECT COUNT(*) AS c FROM lineage_edges WHERE src_id=? OR dst_id=?",
                (lid, lid),
            ).fetchone()['c']

            # Custom lineage assertions for this language
            custom_lineage_count = conn.execute(
                "SELECT COUNT(*) AS c FROM custom_lineage_assertions WHERE src_id=? OR dst_id=?",
                (lid, lid),
            ).fetchone()['c']

            # Capability summary
            capability_rows = conn.execute(
                "SELECT capability_name, maturity FROM language_capabilities WHERE language_id=?", (lid,)
            ).fetchall()
            capabilities = {r['capability_name']: r['maturity'] for r in capability_rows}

            # Determine whether transliteration is even applicable:
            # Latin-script-only languages don't need transliteration profiles.
            script_ids = [r['script_id'] for r in conn.execute(
                "SELECT script_id FROM language_scripts WHERE language_id=?", (lid,)
            ).fetchall()]
            has_non_latin_script = any(s != 'Latn' for s in script_ids) if script_ids else False
            # Also check aliases_json and common_words for script hints if no language_scripts row
            if not script_ids:
                # Fall back to the family/branch heuristic for purely Latin languages
                lang_family = lang.get('family', '') or ''
                lang_branch = lang.get('branch', '') or ''
                latin_families = {'Indo-European', 'Austronesian', 'Niger-Congo', 'Algic'}
                has_non_latin_script = lang_family not in latin_families

            readiness = get_language_readiness(lid).get('items', []) if req.include_runtime else []

            items.append({
                'language_id': lid,
                'name': lang['name'],
                'iso639_3': lang['iso639_3'],
                'family': lang['family'],
                'branch': lang['branch'],
                'aliases': alias_count,
                'aliases_by_type': alias_by_type,
                'variants': variant_count,
                'scripts': script_count,
                'pronunciation_profiles': pron_count,
                'phonology_profiles': phonology_count,
                'transliteration_profiles': translit_count,
                'semantic_concepts': concept_count,
                'lineage_edges': lineage_edge_count,
                'custom_lineage_assertions': custom_lineage_count,
                'capabilities': capabilities,
                'runtime_capabilities': readiness,
                # Honest gap flags
                'missing_phonology': phonology_count == 0,
                'missing_transliteration': translit_count == 0 and has_non_latin_script,
                'missing_pronunciation': pron_count == 0,
                'missing_script': script_count == 0,
                'has_non_latin_script': has_non_latin_script,
            })

    total = len(items)
    summary = {
        'languages': total,
        'with_variants': sum(1 for x in items if x['variants'] > 0),
        'with_concepts': sum(1 for x in items if x['semantic_concepts'] > 0),
        'with_transliteration_profiles': sum(1 for x in items if x['transliteration_profiles'] > 0),
        'with_phonology_profiles': sum(1 for x in items if x['phonology_profiles'] > 0),
        'with_pronunciation_profiles': sum(1 for x in items if x['pronunciation_profiles'] > 0),
        'with_lineage_edges': sum(1 for x in items if x['lineage_edges'] > 0),
        'missing_phonology': sum(1 for x in items if x['missing_phonology']),
        'missing_transliteration': sum(1 for x in items if x['missing_transliteration']),
        'missing_pronunciation': sum(1 for x in items if x['missing_pronunciation']),
        'missing_script_mapping': sum(1 for x in items if x['missing_script']),
    }
    payload = {'ok': True, 'summary': summary, 'items': items}
    if req.output_path:
        Path(req.output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        report_id = f"coverage_{uuid.uuid4().hex[:10]}"
        with connect() as conn:
            conn.execute(
                "INSERT INTO coverage_reports (report_id, output_path, language_ids_json, summary_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (report_id, req.output_path, json.dumps(req.language_ids, ensure_ascii=False), json.dumps(summary, ensure_ascii=False), utcnow()),
            )
            conn.commit()
        payload['report_id'] = report_id
        payload['output_path'] = req.output_path
    return payload


def list_coverage_reports(limit: int = 20) -> dict:
    """List coverage report records, most recent first."""
    with connect() as conn:
        items = [dict(r) for r in conn.execute("SELECT * FROM coverage_reports ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]
    return {'ok': True, 'count': len(items), 'items': items}
