from __future__ import annotations
from arc.core.db import connect
from arc.core.schemas import WatchlistIn, new_id, utcnow
from arc.services.resolver import resolve_entity

def create_watchlist(item: WatchlistIn) -> dict:
    entity_id = resolve_entity(item.entity_ref)
    watchlist_id = new_id("watch")
    with connect() as conn:
        conn.execute(
            "INSERT INTO watchlists (watchlist_id, name, entity_id, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (watchlist_id, item.name, entity_id, item.note, utcnow()),
        )
        conn.commit()
    return {"watchlist_id": watchlist_id, "name": item.name, "entity_id": entity_id, "note": item.note}

def list_watchlists() -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM watchlists ORDER BY created_at DESC").fetchall()]
