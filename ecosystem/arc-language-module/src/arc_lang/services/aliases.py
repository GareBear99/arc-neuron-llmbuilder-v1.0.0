from __future__ import annotations
import json
from arc_lang.core.db import connect
from arc_lang.core.models import AliasUpsertRequest, utcnow


def upsert_language_alias(req: AliasUpsertRequest) -> dict:
    """Add or update a language alias (endonym, exonym, romanized, autonym, or alias type)."""
    now = utcnow()
    alias_id = f"alias_{req.language_id.replace(':','_')}_{req.alias_type}_{req.alias.lower().replace(' ','_')}"
    normalized = req.normalized_form or req.alias.casefold().strip()
    with connect() as conn:
        row = conn.execute("SELECT aliases_json FROM languages WHERE language_id=?", (req.language_id,)).fetchone()
        if not row:
            return {'ok': False, 'error': 'language_not_found', 'language_id': req.language_id}
        conn.execute(
            """
            INSERT INTO language_aliases (alias_id, language_id, alias, normalized_form, alias_type, script_id, region_hint, source_name, source_ref, confidence, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(alias_id) DO UPDATE SET alias=excluded.alias, normalized_form=excluded.normalized_form, alias_type=excluded.alias_type, script_id=excluded.script_id, region_hint=excluded.region_hint, source_name=excluded.source_name, source_ref=excluded.source_ref, confidence=excluded.confidence, notes=excluded.notes, updated_at=excluded.updated_at
            """,
            (alias_id, req.language_id, req.alias, normalized, req.alias_type, req.script_id, req.region_hint, req.source_name, req.source_ref, req.confidence, req.notes, now, now),
        )
        aliases = json.loads(row['aliases_json'])
        if req.alias not in aliases:
            aliases.append(req.alias)
            conn.execute("UPDATE languages SET aliases_json=?, updated_at=? WHERE language_id=?", (json.dumps(sorted(set(aliases)), ensure_ascii=False), now, req.language_id))
        conn.commit()
    return {'ok': True, 'alias_id': alias_id, 'language_id': req.language_id, 'alias': req.alias, 'alias_type': req.alias_type}


def list_language_aliases(language_id: str | None = None, q: str | None = None) -> dict:
    """List language aliases, optionally filtered by language_id or query string."""
    query = "SELECT * FROM language_aliases"
    params = []
    clauses = []
    if language_id:
        clauses.append('language_id=?')
        params.append(language_id)
    if q:
        clauses.append('(alias LIKE ? OR normalized_form LIKE ?)')
        like = f"%{q}%"
        params.extend([like, like.casefold()])
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY language_id, alias_type, alias'
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    return {'ok': True, 'count': len(rows), 'items': rows}
