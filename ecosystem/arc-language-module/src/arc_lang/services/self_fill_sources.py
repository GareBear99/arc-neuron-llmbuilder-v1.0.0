from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path
from typing import Iterable

from arc_lang.core.db import connect
from arc_lang.core.models import utcnow
from arc_lang.services.importers import _normalize_aliases, _normalize_scripts
from arc_lang.services.self_fill import _insert_candidate


def _canonical_language(conn, language_id: str) -> dict | None:
    row = conn.execute(
        "SELECT language_id, iso639_3, name, aliases_json FROM languages WHERE language_id = ?",
        (language_id,),
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["aliases"] = json.loads(item.get("aliases_json") or "[]")
    return item


def _candidate_exists(conn, language_id: str, surface_type: str, payload: dict) -> bool:
    needle = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    row = conn.execute(
        """
        SELECT candidate_id FROM self_fill_candidates
        WHERE language_id = ? AND surface_type = ? AND payload_json = ? AND status IN ('staged','reviewed','promoted')
        LIMIT 1
        """,
        (language_id, surface_type, needle),
    ).fetchone()
    return row is not None


def _insert_conflict(conn, scan_id: str, candidate_id: str | None, language_id: str | None, surface_type: str,
                     conflict_type: str, existing_ref: str | None, incoming_ref: str | None, details: dict) -> str:
    now = utcnow()
    conflict_id = f"sfcf_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO self_fill_conflicts
        (conflict_id, scan_id, candidate_id, language_id, surface_type, conflict_type, existing_ref, incoming_ref, details_json, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (conflict_id, scan_id, candidate_id, language_id, surface_type, conflict_type, existing_ref, incoming_ref,
         json.dumps(details, ensure_ascii=False, sort_keys=True), 'open', now, now),
    )
    return conflict_id


def _record_import_run(conn, source_name: str, source_kind: str, file_path: str, scan_id: str,
                       records_seen: int, candidates_staged: int, conflict_count: int, summary: dict) -> str:
    now = utcnow()
    import_run_id = f"sfir_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO self_fill_import_runs
        (import_run_id, source_name, source_kind, file_path, scan_id, records_seen, candidates_staged, conflict_count, summary_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (import_run_id, source_name, source_kind, file_path, scan_id, records_seen, candidates_staged, conflict_count,
         json.dumps(summary, ensure_ascii=False, sort_keys=True), now),
    )
    return import_run_id


def _open_scan(mode: str, source_name: str, file_path: str) -> str:
    scan_id = f"sfs_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            "INSERT INTO self_fill_scan_runs (scan_id, mode, language_ids_json, summary_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (scan_id, mode, json.dumps([], ensure_ascii=False), json.dumps({"source_name": source_name, "file_path": file_path}, ensure_ascii=False), utcnow()),
        )
        conn.commit()
    return scan_id


def _close_scan(scan_id: str, summary: dict) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE self_fill_scan_runs SET summary_json = ? WHERE scan_id = ?",
            (json.dumps(summary, ensure_ascii=False, sort_keys=True), scan_id),
        )
        conn.commit()


def _stage_aliases(conn, scan_id: str, language_id: str, aliases: Iterable[str], source_name: str, source_ref: str | None, conflicts: list[dict], staged: list[str]) -> None:
    canonical = _canonical_language(conn, language_id)
    alias_rows = {r['alias']: r['language_id'] for r in conn.execute("SELECT alias, language_id FROM language_aliases WHERE alias IN (%s)" % ','.join('?'*len(list(aliases))), tuple(aliases)).fetchall()} if aliases else {}
    canonical_aliases = set(canonical.get('aliases', []) if canonical else [])
    for alias in aliases:
        if not alias:
            continue
        payload = {
            "alias": alias,
            "alias_type": "alias",
            "normalized_form": alias.casefold().strip(),
            "script_id": None,
            "region_hint": None,
        }
        if canonical and alias in canonical_aliases:
            continue
        if alias in alias_rows and alias_rows[alias] != language_id:
            conflict_id = _insert_conflict(conn, scan_id, None, language_id, 'alias', 'alias_owned_by_other_language', alias_rows[alias], alias, {
                'alias': alias,
                'existing_language_id': alias_rows[alias],
                'incoming_language_id': language_id,
            })
            conflicts.append({'conflict_id': conflict_id, 'surface_type': 'alias', 'alias': alias})
            continue
        if _candidate_exists(conn, language_id, 'alias', payload):
            continue
        staged.append(_insert_candidate(conn, scan_id, language_id, 'alias', payload, 'approved source importer staged alias candidate', 0.78, source_name, source_ref))


def stage_iso_fixture_candidates(path: str | Path, source_name: str = 'iso639_fixture') -> dict:
    path = str(path)
    scan_id = _open_scan('source_import_iso', source_name, path)
    records_seen = 0
    staged: list[str] = []
    conflicts: list[dict] = []
    with connect() as conn, open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records_seen += 1
            language_id = row['language_id'].strip()
            aliases = _normalize_aliases(row.get('aliases'))
            _stage_aliases(conn, scan_id, language_id, aliases, source_name, row.get('iso639_3') or None, conflicts, staged)
        summary = {
            'source_name': source_name,
            'source_kind': 'iso639_csv',
            'records_seen': records_seen,
            'candidates_staged': len(staged),
            'conflict_count': len(conflicts),
            'scan_id': scan_id,
        }
        import_run_id = _record_import_run(conn, source_name, 'iso639_csv', path, scan_id, records_seen, len(staged), len(conflicts), summary)
        conn.commit()
    _close_scan(scan_id, {**summary, 'import_run_id': import_run_id})
    return {'ok': True, 'scan_id': scan_id, 'import_run_id': import_run_id, **summary, 'conflicts': conflicts}


def stage_glottolog_fixture_candidates(path: str | Path, source_name: str = 'glottolog_fixture') -> dict:
    path = str(path)
    scan_id = _open_scan('source_import_glottolog', source_name, path)
    records_seen = 0
    staged: list[str] = []
    conflicts: list[dict] = []
    with connect() as conn, open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records_seen += 1
            language_id = row['language_id'].strip()
            canonical = _canonical_language(conn, language_id)
            family = (row.get('family') or '').strip() or None
            branch = (row.get('branch') or '').strip() or None
            if canonical:
                if family and canonical.get('name') and row.get('name') and canonical['name'] != row['name'].strip():
                    conflict_id = _insert_conflict(conn, scan_id, None, language_id, 'language_lineage', 'name_mismatch', canonical['name'], row['name'].strip(), {
                        'canonical_name': canonical['name'], 'incoming_name': row['name'].strip(), 'family': family, 'branch': branch
                    })
                    conflicts.append({'conflict_id': conflict_id, 'surface_type': 'language_lineage', 'language_id': language_id})
                payload = {'capability_name': 'lineage_import_seen', 'maturity': 'seeded', 'provider': 'source_import', 'notes': f'family={family}; branch={branch}', 'confidence': 0.8}
                if not _candidate_exists(conn, language_id, 'capability', payload):
                    staged.append(_insert_candidate(conn, scan_id, language_id, 'capability', payload, 'approved source importer recorded lineage source coverage', 0.8, source_name, row.get('source_ref') or None))
        summary = {'source_name': source_name, 'source_kind': 'glottolog_csv', 'records_seen': records_seen, 'candidates_staged': len(staged), 'conflict_count': len(conflicts), 'scan_id': scan_id}
        import_run_id = _record_import_run(conn, source_name, 'glottolog_csv', path, scan_id, records_seen, len(staged), len(conflicts), summary)
        conn.commit()
    _close_scan(scan_id, {**summary, 'import_run_id': import_run_id})
    return {'ok': True, 'scan_id': scan_id, 'import_run_id': import_run_id, **summary, 'conflicts': conflicts}


def stage_cldr_fixture_candidates(path: str | Path, source_name: str = 'cldr_fixture') -> dict:
    path = str(path)
    scan_id = _open_scan('source_import_cldr', source_name, path)
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    records_seen = 0
    staged: list[str] = []
    conflicts: list[dict] = []
    with connect() as conn:
        for entry in payload.get('languages', []):
            records_seen += 1
            language_id = (entry.get('language_id') or '').strip()
            if not language_id:
                continue
            scripts = _normalize_scripts(entry.get('scripts'))
            for script_id in scripts:
                if script_id == 'Latn':
                    continue
                exists = conn.execute(
                    'SELECT profile_id FROM transliteration_profiles WHERE language_id = ? AND source_script = ? AND target_script = ? LIMIT 1',
                    (language_id, script_id, 'Latn')
                ).fetchone()
                payload_row = {
                    'source_script': script_id,
                    'target_script': 'Latn',
                    'scheme_name': f'cldr_{script_id.lower()}_to_latn',
                    'coverage': 'external_required',
                    'example_in': None,
                    'example_out': None,
                    'notes': 'approved CLDR importer staged transliteration bridge',
                }
                if exists or _candidate_exists(conn, language_id, 'transliteration_profile', payload_row):
                    continue
                staged.append(_insert_candidate(conn, scan_id, language_id, 'transliteration_profile', payload_row, 'approved CLDR importer staged transliteration bridge', 0.74, source_name, entry.get('locale') or None))
        summary = {'source_name': source_name, 'source_kind': 'cldr_json', 'records_seen': records_seen, 'candidates_staged': len(staged), 'conflict_count': len(conflicts), 'scan_id': scan_id}
        import_run_id = _record_import_run(conn, source_name, 'cldr_json', path, scan_id, records_seen, len(staged), len(conflicts), summary)
        conn.commit()
    _close_scan(scan_id, {**summary, 'import_run_id': import_run_id})
    return {'ok': True, 'scan_id': scan_id, 'import_run_id': import_run_id, **summary, 'conflicts': conflicts}


def list_self_fill_import_runs(limit: int = 50) -> dict:
    with connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM self_fill_import_runs ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()]
    for row in rows:
        row['summary'] = json.loads(row.pop('summary_json') or '{}')
    return {'ok': True, 'results': rows}


def list_self_fill_conflicts(status: str | None = None, limit: int = 100) -> dict:
    query = 'SELECT * FROM self_fill_conflicts'
    params: list[object] = []
    if status:
        query += ' WHERE status = ?'
        params.append(status)
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]
    for row in rows:
        row['details'] = json.loads(row.pop('details_json') or '{}')
    return {'ok': True, 'count': len(rows), 'results': rows}


def resolve_self_fill_conflict(conflict_id: str, decision: str, notes: str = '') -> dict:
    if decision not in {'accepted', 'rejected'}:
        return {'ok': False, 'error': 'invalid_decision', 'decision': decision}
    now = utcnow()
    with connect() as conn:
        row = conn.execute('SELECT conflict_id FROM self_fill_conflicts WHERE conflict_id = ?', (conflict_id,)).fetchone()
        if not row:
            return {'ok': False, 'error': 'conflict_not_found', 'conflict_id': conflict_id}
        conn.execute('UPDATE self_fill_conflicts SET status = ?, updated_at = ? WHERE conflict_id = ?', (decision, now, conflict_id))
        conn.commit()
    return {'ok': True, 'conflict_id': conflict_id, 'status': decision, 'notes': notes}


def run_approved_source_import_bootstrap() -> dict:
    root = Path(__file__).resolve().parents[3]
    examples = root / 'examples'
    results = {
        'iso': stage_iso_fixture_candidates(examples / 'iso6393_sample.csv'),
        'glottolog': stage_glottolog_fixture_candidates(examples / 'glottolog_sample.csv'),
        'cldr': stage_cldr_fixture_candidates(examples / 'cldr_sample.json'),
    }
    return {'ok': True, 'results': results}
