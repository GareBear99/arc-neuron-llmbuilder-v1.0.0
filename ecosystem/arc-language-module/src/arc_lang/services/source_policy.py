from __future__ import annotations
from arc_lang.core.db import connect
from arc_lang.core.models import SourceWeightUpdateRequest, utcnow

DEFAULTS = {
    'glottolog': 1.0,
    'iso639_3': 0.9,
    'cldr': 0.85,
    'common_seed': 0.6,
    'common_seed_local': 0.7,   # stronger local override of common seed
    'user_custom': 0.5,
    'user_submission': 0.45,
}


def seed_source_weights() -> dict:
    """Seed default source authority weights into the database (idempotent)."""
    now = utcnow()
    with connect() as conn:
        for name, weight in DEFAULTS.items():
            conn.execute(
                "INSERT INTO source_weights (source_name, authority_weight, notes, created_at, updated_at) VALUES (?, ?, '', ?, ?) ON CONFLICT(source_name) DO UPDATE SET authority_weight=excluded.authority_weight, updated_at=excluded.updated_at",
                (name, weight, now, now),
            )
        conn.commit()
    return {'ok': True, 'count': len(DEFAULTS)}


def set_source_weight(req: SourceWeightUpdateRequest) -> dict:
    """Set the authority weight for a source name."""
    now = utcnow()
    with connect() as conn:
        conn.execute(
            "INSERT INTO source_weights (source_name, authority_weight, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(source_name) DO UPDATE SET authority_weight=excluded.authority_weight, notes=excluded.notes, updated_at=excluded.updated_at",
            (req.source_name, req.authority_weight, req.notes, now, now),
        )
        conn.commit()
    return {'ok': True, 'source_name': req.source_name, 'authority_weight': req.authority_weight}


def list_source_weights() -> dict:
    """List all source authority weights, ordered by weight descending."""
    with connect() as conn:
        items = [dict(r) for r in conn.execute('SELECT * FROM source_weights ORDER BY authority_weight DESC, source_name').fetchall()]
    return {'ok': True, 'count': len(items), 'items': items}
