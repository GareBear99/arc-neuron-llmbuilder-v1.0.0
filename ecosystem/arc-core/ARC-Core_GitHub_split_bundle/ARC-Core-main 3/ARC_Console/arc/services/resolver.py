from __future__ import annotations
from arc.core.db import connect
from arc.core.schemas import utcnow
from arc.core.util import normalize_entity, guess_entity_type
import json

def resolve_entity(label: str) -> str:
    normalized = normalize_entity(label)
    entity_id = f"ent_{normalized.replace(' ', '_')[:48]}"
    now = utcnow()
    with connect() as conn:
        row = conn.execute("SELECT entity_id, aliases_json, first_seen FROM entities WHERE entity_id = ?", (entity_id,)).fetchone()
        if row:
            aliases = sorted(set(json.loads(row["aliases_json"]) + [label]))
            conn.execute(
                "UPDATE entities SET aliases_json = ?, last_seen = ? WHERE entity_id = ?",
                (json.dumps(aliases), now, entity_id),
            )
        else:
            conn.execute(
                "INSERT INTO entities (entity_id, label, entity_type, aliases_json, first_seen, last_seen, risk_score) VALUES (?, ?, ?, ?, ?, ?, 0)",
                (entity_id, label, guess_entity_type(label), json.dumps([label]), now, now),
            )
        conn.commit()
    return entity_id
