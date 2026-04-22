from __future__ import annotations
from arc.core.db import connect
from arc.core.schemas import utcnow

def upsert_edge(src_entity: str, dst_entity: str, relation: str, increment: float = 1.0, conn=None) -> None:
    edge_id = f"edge_{src_entity}_{relation}_{dst_entity}"[:180]
    now = utcnow()
    owns_conn = conn is None
    if conn is None:
        conn = connect()
    row = conn.execute("SELECT weight FROM edges WHERE edge_id = ?", (edge_id,)).fetchone()
    if row:
        conn.execute(
            "UPDATE edges SET weight = ?, last_seen = ? WHERE edge_id = ?",
            (round(float(row["weight"]) + increment, 2), now, edge_id),
        )
    else:
        conn.execute(
            "INSERT INTO edges (edge_id, src_entity, dst_entity, relation, weight, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
            (edge_id, src_entity, dst_entity, relation, increment, now),
        )
    if owns_conn:
        conn.commit()
        conn.close()

def snapshot(limit: int = 250) -> dict:
    with connect() as conn:
        nodes = [dict(row) for row in conn.execute(
            "SELECT entity_id, label, entity_type, risk_score FROM entities ORDER BY risk_score DESC, last_seen DESC LIMIT ?", (limit,)
        ).fetchall()]
        edges = [dict(row) for row in conn.execute(
            "SELECT src_entity, dst_entity, relation, weight, last_seen FROM edges ORDER BY weight DESC, last_seen DESC LIMIT ?", (limit,)
        ).fetchall()]
    return {"nodes": nodes, "edges": edges}
