from __future__ import annotations
import csv
import json
import uuid
from pathlib import Path
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow


def _normalize_aliases(value: str | list[str] | None) -> list[str]:
    """Normalize an alias value (string, list, or JSON) to a clean list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [v.strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith('['):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            return []
    return [v.strip() for v in text.split('|') if v.strip()]


def _normalize_scripts(value: str | list[str] | None) -> list[str]:
    """Normalize a scripts value to a clean list of script IDs."""
    return _normalize_aliases(value)


def _slug(text: str) -> str:
    """Convert text to a URL-safe lowercase slug for node IDs."""
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in text).strip('_')


def _record_import_run(conn, source_name: str, source_kind: str, file_path: str, seen: int, upserted: int, notes: str, now: str) -> str:
    """Record an import run receipt in the database."""
    import_id = f"imp_{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO import_runs (import_id, source_name, source_kind, file_path, records_seen, records_upserted, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (import_id, source_name, source_kind, file_path, seen, upserted, notes, now),
    )
    return import_id


def _upsert_provenance(conn, record_type: str, record_id: str, source_name: str, source_ref: str | None, confidence: float, notes: str, now: str) -> None:
    """Upsert a provenance record for a seeded entity."""
    prov_id = f"prov_{record_type}_{record_id}_{source_name}".replace(":", "_").replace(" ", "_")
    conn.execute(
        """
        INSERT INTO provenance_records (provenance_id, record_type, record_id, source_name, source_ref, confidence, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(provenance_id) DO UPDATE SET source_ref=excluded.source_ref, confidence=excluded.confidence, notes=excluded.notes
        """,
        (prov_id, record_type, record_id, source_name, source_ref, confidence, notes, now),
    )


def _ensure_lineage_node(conn, node_type: str, name: str | None, parent_node_id: str | None, source_name: str, source_ref: str | None, confidence: float, now: str) -> str | None:
    """Ensure a lineage node (family/branch) exists in the DB, creating it if absent."""
    if not name:
        return None
    node_id = f"{node_type}:{_slug(name)}"
    conn.execute(
        """
        INSERT INTO lineage_nodes (node_id, node_type, name, parent_node_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET name=excluded.name, parent_node_id=COALESCE(excluded.parent_node_id, lineage_nodes.parent_node_id), updated_at=excluded.updated_at
        """,
        (node_id, node_type, name, parent_node_id, now, now),
    )
    _upsert_provenance(conn, 'lineage_node', node_id, source_name, source_ref, confidence, f'Imported {node_type} lineage node.', now)
    if parent_node_id:
        edge_id = f"edge_{node_id.replace(':','_')}_to_parent"
        conn.execute(
            """
            INSERT INTO lineage_edges (edge_id, src_id, dst_id, relation, confidence, disputed, source_ref, created_at)
            VALUES (?, ?, ?, 'child_of', ?, 0, ?, ?)
            ON CONFLICT(edge_id) DO UPDATE SET dst_id=excluded.dst_id, confidence=excluded.confidence, source_ref=excluded.source_ref
            """,
            (edge_id, node_id, parent_node_id, confidence, source_ref, now),
        )
    return node_id


def _detect_conflicts(conn, language_id: str, incoming_name: str, incoming_family: str | None) -> list[dict]:
    """Return list of conflict descriptions when incoming data disagrees with existing custom assertions."""
    conflicts: list[dict] = []
    custom = conn.execute(
        "SELECT assertion_id, src_id, dst_id, relation, status FROM custom_lineage_assertions WHERE src_id = ? OR dst_id = ?",
        (language_id, language_id),
    ).fetchall()
    for row in custom:
        conflicts.append({
            'conflict_type': 'custom_lineage_vs_import',
            'language_id': language_id,
            'assertion_id': row['assertion_id'],
            'relation': row['relation'],
            'status': row['status'],
            'note': f'Import source data for {language_id} conflicts with existing custom lineage assertion {row["assertion_id"]} (relation={row["relation"]}).',
        })
    return conflicts


def _ensure_language_row(conn, language_id: str, name: str, iso639_3: str | None = None, family: str | None = None, branch: str | None = None, parent_language_id: str | None = None, aliases: list[str] | None = None, common_words: list[str] | None = None, now: str | None = None, source_name: str = 'unknown', source_ref: str | None = None, confidence: float = 0.7) -> bool:
    """Returns True if this was a new insert, False if updated."""
    now = now or utcnow()
    aliases = aliases or []
    common_words = common_words or []
    family_node_id = _ensure_lineage_node(conn, 'family', family, None, source_name, source_ref, confidence, now) if family else None
    branch_node_id = _ensure_lineage_node(conn, 'branch', branch, family_node_id, source_name, source_ref, max(0.55, confidence - 0.05), now) if branch else None
    existing = conn.execute("SELECT aliases_json, common_words_json FROM languages WHERE language_id = ?", (language_id,)).fetchone()
    if existing:
        merged_aliases = sorted(set(json.loads(existing['aliases_json']) + aliases))
        merged_words = sorted(set(json.loads(existing['common_words_json']) + common_words))
        conn.execute(
            """
            UPDATE languages SET
                iso639_3 = COALESCE(?, iso639_3),
                name = COALESCE(?, name),
                family = COALESCE(?, family),
                branch = COALESCE(?, branch),
                parent_language_id = COALESCE(?, parent_language_id),
                family_node_id = COALESCE(?, family_node_id),
                branch_node_id = COALESCE(?, branch_node_id),
                aliases_json = ?,
                common_words_json = ?,
                updated_at = ?
            WHERE language_id = ?
            """,
            (iso639_3, name, family, branch, parent_language_id, family_node_id, branch_node_id, json.dumps(merged_aliases, ensure_ascii=False), json.dumps(merged_words, ensure_ascii=False), now, language_id),
        )
        is_new = False
    else:
        conn.execute(
            """
            INSERT INTO languages (language_id, iso639_3, name, family, branch, parent_language_id, family_node_id, branch_node_id, parent_node_id, aliases_json, common_words_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (language_id, iso639_3, name, family, branch, parent_language_id, family_node_id, branch_node_id, None, json.dumps(sorted(set(aliases)), ensure_ascii=False), json.dumps(sorted(set(common_words)), ensure_ascii=False), now, now),
        )
        is_new = True
    if branch_node_id:
        edge_id = f"edge_{language_id.replace(':','_')}_branch"
        conn.execute(
            """
            INSERT INTO lineage_edges (edge_id, src_id, dst_id, relation, confidence, disputed, source_ref, created_at)
            VALUES (?, ?, ?, 'member_of_branch', ?, 0, ?, ?)
            ON CONFLICT(edge_id) DO UPDATE SET dst_id=excluded.dst_id, confidence=excluded.confidence, source_ref=excluded.source_ref
            """,
            (edge_id, language_id, branch_node_id, confidence, source_ref, now),
        )
    elif family_node_id:
        edge_id = f"edge_{language_id.replace(':','_')}_family"
        conn.execute(
            """
            INSERT INTO lineage_edges (edge_id, src_id, dst_id, relation, confidence, disputed, source_ref, created_at)
            VALUES (?, ?, ?, 'member_of_family', ?, 0, ?, ?)
            ON CONFLICT(edge_id) DO UPDATE SET dst_id=excluded.dst_id, confidence=excluded.confidence, source_ref=excluded.source_ref
            """,
            (edge_id, language_id, family_node_id, confidence, source_ref, now),
        )
    if parent_language_id:
        edge_id = f"edge_{language_id.replace(':','_')}_parent"
        conn.execute(
            """
            INSERT INTO lineage_edges (edge_id, src_id, dst_id, relation, confidence, disputed, source_ref, created_at)
            VALUES (?, ?, ?, 'parent_of', ?, 0, ?, ?)
            ON CONFLICT(edge_id) DO UPDATE SET dst_id=excluded.dst_id, confidence=excluded.confidence, source_ref=excluded.source_ref
            """,
            (edge_id, language_id, parent_language_id, max(0.55, confidence - 0.1), source_ref, now),
        )
    return is_new


def import_glottolog_csv(path: str | Path, dry_run: bool = False) -> dict:
    """Import a Glottolog-style genealogy CSV.

    Parameters
    ----------
    path:
        Path to CSV file.  Required columns: language_id, name.
        Optional: family, branch, parent_language_id, lineage_confidence, source_ref.
    dry_run:
        When True, parse and validate all rows but make no database changes.
        Returns the same summary structure with ``dry_run=True`` and an empty
        ``import_id`` so callers can preview the effect before committing.
    """
    path = str(path)
    now = utcnow()
    seen = 0
    inserted = 0
    updated = 0
    conflicts: list[dict] = []
    with connect() as conn, open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            seen += 1
            language_id = row['language_id'].strip()
            name = row['name'].strip()
            family = (row.get('family') or '').strip() or None
            branch = (row.get('branch') or '').strip() or None
            parent_language_id = (row.get('parent_language_id') or '').strip() or None
            confidence = float(row.get('lineage_confidence') or 0.75)
            source_ref = (row.get('source_ref') or '').strip() or None
            row_conflicts = _detect_conflicts(conn, language_id, name, family)
            conflicts.extend(row_conflicts)
            if not dry_run:
                is_new = _ensure_language_row(conn, language_id=language_id, name=name, family=family, branch=branch, parent_language_id=parent_language_id, now=now, source_name='glottolog', source_ref=source_ref, confidence=confidence)
                _upsert_provenance(conn, 'language', language_id, 'glottolog', source_ref, confidence, 'Imported from Glottolog-style CSV row.', now)
                if is_new:
                    inserted += 1
                else:
                    updated += 1
        if not dry_run:
            import_id = _record_import_run(conn, 'glottolog', 'genealogy', path, seen, inserted + updated, f'Glottolog-style CSV import completed. inserted={inserted} updated={updated} conflicts={len(conflicts)}', now)
            conn.commit()
        else:
            import_id = ''
    return {
        'ok': True,
        'dry_run': dry_run,
        'source_name': 'glottolog',
        'import_id': import_id,
        'records_seen': seen,
        'records_inserted': inserted,
        'records_updated': updated,
        'records_upserted': inserted + updated,
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
    }


def import_iso639_csv(path: str | Path, dry_run: bool = False) -> dict:
    """Import an ISO 639-3-style identifier CSV.

    Required columns: language_id, iso639_3, name.
    Optional: aliases (pipe-separated or JSON array).

    dry_run: When True, parse all rows but make no database changes.
    """
    path = str(path)
    now = utcnow()
    seen = 0
    inserted = 0
    updated = 0
    conflicts: list[dict] = []
    with connect() as conn, open(path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            seen += 1
            language_id = row['language_id'].strip()
            iso639_3 = row['iso639_3'].strip()
            name = row['name'].strip()
            aliases = _normalize_aliases(row.get('aliases'))
            row_conflicts = _detect_conflicts(conn, language_id, name, None)
            conflicts.extend(row_conflicts)
            if not dry_run:
                is_new = _ensure_language_row(conn, language_id=language_id, iso639_3=iso639_3, name=name, aliases=aliases, now=now, source_name='iso639_3', source_ref=iso639_3, confidence=0.95)
                _upsert_provenance(conn, 'language', language_id, 'iso639_3', iso639_3, 0.95, 'Imported from ISO 639-3-style CSV row.', now)
                if is_new:
                    inserted += 1
                else:
                    updated += 1
        if not dry_run:
            import_id = _record_import_run(conn, 'iso639_3', 'identifiers', path, seen, inserted + updated, f'ISO 639-3-style CSV import completed. inserted={inserted} updated={updated} conflicts={len(conflicts)}', now)
            conn.commit()
        else:
            import_id = ''
    return {
        'ok': True,
        'dry_run': dry_run,
        'source_name': 'iso639_3',
        'import_id': import_id,
        'records_seen': seen,
        'records_inserted': inserted,
        'records_updated': updated,
        'records_upserted': inserted + updated,
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
    }


def import_cldr_json(path: str | Path, dry_run: bool = False) -> dict:
    """Import a CLDR-style locale/script JSON file.

    Expected structure: ``{"languages": [...]}`` where each entry has
    language_id, optional name, aliases (list), scripts (list), source_ref.

    dry_run: When True, parse all rows but make no database changes.
    """
    path = str(path)
    now = utcnow()
    seen = 0
    inserted = 0
    updated = 0
    conflicts: list[dict] = []
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    rows = payload.get('languages', [])
    with connect() as conn:
        for row in rows:
            seen += 1
            language_id = row['language_id'].strip()
            name = row.get('name', language_id).strip()
            aliases = _normalize_aliases(row.get('aliases'))
            scripts = _normalize_scripts(row.get('scripts'))
            source_ref = row.get('source_ref')
            row_conflicts = _detect_conflicts(conn, language_id, name, None)
            conflicts.extend(row_conflicts)
            if not dry_run:
                is_new = _ensure_language_row(conn, language_id=language_id, name=name, aliases=aliases, now=now, source_name='cldr', source_ref=source_ref, confidence=0.9)
                for script_id in scripts:
                    conn.execute('INSERT OR IGNORE INTO language_scripts (language_id, script_id) VALUES (?, ?)', (language_id, script_id))
                _upsert_provenance(conn, 'language', language_id, 'cldr', source_ref, 0.9, 'Imported from CLDR-style JSON mapping.', now)
                if is_new:
                    inserted += 1
                else:
                    updated += 1
        if not dry_run:
            import_id = _record_import_run(conn, 'cldr', 'scripts_locales', path, seen, inserted + updated, f'CLDR-style JSON import completed. inserted={inserted} updated={updated} conflicts={len(conflicts)}', now)
            conn.commit()
        else:
            import_id = ''
    return {
        'ok': True,
        'dry_run': dry_run,
        'source_name': 'cldr',
        'import_id': import_id,
        'records_seen': seen,
        'records_inserted': inserted,
        'records_updated': updated,
        'records_upserted': inserted + updated,
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
    }
