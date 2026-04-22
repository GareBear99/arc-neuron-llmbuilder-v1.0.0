from __future__ import annotations
from arc_lang.core.db import connect


def search_languages(query: str, limit: int = 20) -> dict:
    """Search languages by name, ISO code, family, branch, or any alias.

    Searches both the ``aliases_json`` column on the languages table (seed-time
    aliases) and the governed ``language_aliases`` table (runtime-added aliases,
    endonyms, exonyms, romanized forms).  Results are deduplicated and sorted by
    name.
    """
    q = f"%{query.strip().casefold()}%"
    with connect() as conn:
        # Primary search: language row fields + aliases_json column
        rows = conn.execute(
            """
            SELECT language_id, iso639_3, name, family, branch
            FROM languages
            WHERE lower(language_id) LIKE ?
               OR lower(name) LIKE ?
               OR lower(aliases_json) LIKE ?
               OR lower(COALESCE(family,'')) LIKE ?
               OR lower(COALESCE(branch,'')) LIKE ?
            ORDER BY name ASC
            LIMIT ?
            """,
            (q, q, q, q, q, limit),
        ).fetchall()
        primary_ids = {r['language_id'] for r in rows}

        # Secondary search: governed language_aliases table
        alias_rows = conn.execute(
            """
            SELECT DISTINCT la.language_id
            FROM language_aliases la
            WHERE lower(la.alias) LIKE ?
               OR lower(COALESCE(la.normalized_form,'')) LIKE ?
            LIMIT ?
            """,
            (q, q, limit),
        ).fetchall()
        alias_ids = {r['language_id'] for r in alias_rows} - primary_ids

        extra_rows: list = []
        if alias_ids:
            placeholders = ','.join('?' for _ in alias_ids)
            extra_rows = conn.execute(
                f"""
                SELECT language_id, iso639_3, name, family, branch
                FROM languages
                WHERE language_id IN ({placeholders})
                ORDER BY name ASC
                """,
                list(alias_ids),
            ).fetchall()

    combined = [dict(r) for r in rows] + [dict(r) for r in extra_rows]
    # Sort combined by name, deduplicate by language_id preserving order
    seen: set[str] = set()
    deduped = []
    for r in sorted(combined, key=lambda x: x['name']):
        if r['language_id'] not in seen:
            seen.add(r['language_id'])
            deduped.append(r)
    return {'ok': True, 'query': query, 'results': deduped[:limit]}

