
from __future__ import annotations
from arc_lang.core.db import connect
from arc_lang.core.models import LanguageVariantUpsertRequest, utcnow


def upsert_language_variant(req: LanguageVariantUpsertRequest) -> dict:
    """Create or update a language variant (dialect, register, orthography, or historical stage)."""
    now = utcnow()
    variant_id = f"variant_{req.language_id.replace(':','_')}_{req.variant_type}_{req.variant_name.casefold().replace(' ','_')}"
    with connect() as conn:
        lang = conn.execute("SELECT 1 FROM languages WHERE language_id=?", (req.language_id,)).fetchone()
        if not lang:
            return {'ok': False, 'error': 'language_not_found', 'language_id': req.language_id}
        conn.execute(
            """
            INSERT INTO language_variants (variant_id, language_id, variant_name, variant_type, region_hint, script_id, status, mutual_intelligibility, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(variant_id) DO UPDATE SET region_hint=excluded.region_hint, script_id=excluded.script_id, status=excluded.status, mutual_intelligibility=excluded.mutual_intelligibility, notes=excluded.notes, updated_at=excluded.updated_at
            """,
            (variant_id, req.language_id, req.variant_name, req.variant_type, req.region_hint, req.script_id, req.status, req.mutual_intelligibility, req.notes, now, now),
        )
        conn.commit()
    return {'ok': True, 'variant_id': variant_id, 'language_id': req.language_id, 'variant_name': req.variant_name}


def list_language_variants(language_id: str | None = None, variant_type: str | None = None) -> dict:
    """List language variants, optionally filtered by language_id and variant_type."""
    query = "SELECT * FROM language_variants"
    params = []
    clauses = []
    if language_id:
        clauses.append('language_id=?')
        params.append(language_id)
    if variant_type:
        clauses.append('variant_type=?')
        params.append(variant_type)
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY language_id, variant_type, variant_name'
    with connect() as conn:
        items = [dict(r) for r in conn.execute(query, params).fetchall()]
    return {'ok': True, 'count': len(items), 'items': items}
