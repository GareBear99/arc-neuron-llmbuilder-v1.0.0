from __future__ import annotations
from arc_lang.core.db import connect
from arc_lang.core.models import RelationshipAssertionRequest, utcnow


def add_relationship_assertion(req: RelationshipAssertionRequest) -> dict:
    """Add a cross-lexeme relationship assertion (cognate, borrowing, false_friend, etc.)."""
    now = utcnow()
    assertion_id = f"rel_{req.relation}_{req.src_lexeme_id}_{req.dst_lexeme_id}".replace(':','_').replace(' ','_')
    with connect() as conn:
        s = conn.execute("SELECT lexeme_id FROM lexemes WHERE lexeme_id=?", (req.src_lexeme_id,)).fetchone()
        d = conn.execute("SELECT lexeme_id FROM lexemes WHERE lexeme_id=?", (req.dst_lexeme_id,)).fetchone()
        if not s or not d:
            return {'ok': False, 'error': 'lexeme_not_found', 'src_exists': bool(s), 'dst_exists': bool(d)}
        conn.execute(
            """
            INSERT INTO relationship_assertions (assertion_id, src_lexeme_id, dst_lexeme_id, relation, confidence, disputed, source_name, source_ref, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(assertion_id) DO UPDATE SET confidence=excluded.confidence, disputed=excluded.disputed, source_name=excluded.source_name, source_ref=excluded.source_ref, notes=excluded.notes, updated_at=excluded.updated_at
            """,
            (assertion_id, req.src_lexeme_id, req.dst_lexeme_id, req.relation, req.confidence, 1 if req.disputed else 0, req.source_name, req.source_ref, req.notes, now, now),
        )
        conn.commit()
    return {'ok': True, 'assertion_id': assertion_id, 'relation': req.relation}


def list_relationship_assertions(lexeme_id: str | None = None, relation: str | None = None) -> dict:
    """List relationship assertions, optionally filtered by lexeme_id and relation."""
    query = "SELECT * FROM relationship_assertions"
    params = []
    clauses = []
    if lexeme_id:
        clauses.append('(src_lexeme_id=? OR dst_lexeme_id=?)')
        params.extend([lexeme_id, lexeme_id])
    if relation:
        clauses.append('relation=?')
        params.append(relation)
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY relation, src_lexeme_id, dst_lexeme_id'
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    return {'ok': True, 'count': len(rows), 'items': rows}
