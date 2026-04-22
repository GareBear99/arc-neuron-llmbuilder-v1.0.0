from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from arc.core.db import connect
from arc.core.schemas import EventIn, EventOut, new_id
from arc.core.util import fingerprint
from arc.core.risk import score_event
from arc.services.resolver import resolve_entity
from arc.services.graph import upsert_edge
from arc.services.audit import append_receipt


def _event_count_7d(conn, subject_entity: str) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM events WHERE ts >= ? AND subject = ?",
        (cutoff, subject_entity),
    ).fetchone()
    return int(row["c"])


def create_event(data: EventIn) -> EventOut:
    subject_entity = resolve_entity(data.subject)
    object_entity = resolve_entity(data.object) if data.object else None
    fp = fingerprint(data.event_type, data.source, data.subject, data.object, data.location, data.payload)
    event_id = new_id("evt")
    with connect() as conn:
        existing = conn.execute("SELECT * FROM events WHERE fingerprint = ?", (fp,)).fetchone()
        if existing:
            payload = json.loads(existing["payload_json"])
            return EventOut(
                id=existing["id"],
                event_type=existing["event_type"],
                source=existing["source"],
                subject=data.subject,
                object=data.object,
                location=existing["location"],
                confidence=existing["confidence"],
                severity=existing["severity"],
                payload=payload,
                ts=existing["ts"],
                fingerprint=existing["fingerprint"],
            )
        watchlisted = conn.execute("SELECT 1 FROM watchlists WHERE entity_id = ? LIMIT 1", (subject_entity,)).fetchone() is not None
        edge_count = conn.execute("SELECT COUNT(*) AS c FROM edges WHERE src_entity = ? OR dst_entity = ?", (subject_entity, subject_entity)).fetchone()["c"]
        count7 = _event_count_7d(conn, subject_entity)
        risk_score = score_event(data.confidence, data.severity, watchlisted, int(edge_count), count7)
        conn.execute(
            "INSERT INTO events (id, ts, event_type, source, subject, object, location, confidence, severity, fingerprint, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, data.ts, data.event_type, data.source, subject_entity, object_entity, data.location, data.confidence, data.severity, fp, json.dumps(data.payload, sort_keys=True)),
        )
        conn.execute("UPDATE entities SET risk_score = MAX(risk_score, ?) WHERE entity_id = ?", (risk_score, subject_entity))
        if object_entity:
            upsert_edge(subject_entity, object_entity, data.event_type, increment=max(1.0, data.confidence * 2), conn=conn)
        conn.commit()
    append_receipt("event", event_id, "observer", {"fingerprint": fp, "subject": subject_entity, "object": object_entity, "source": data.source})
    return EventOut(id=event_id, fingerprint=fp, **data.model_dump())


def list_events(limit: int = 50, q: str | None = None) -> list[dict]:
    with connect() as conn:
        if q:
            token = f"%{q.lower()}%"
            rows = conn.execute(
                """
                SELECT e.*,
                       es.label AS subject_label,
                       eo.label AS object_label
                FROM events e
                LEFT JOIN entities es ON es.entity_id = e.subject
                LEFT JOIN entities eo ON eo.entity_id = e.object
                WHERE lower(e.event_type) LIKE ?
                   OR lower(e.source) LIKE ?
                   OR lower(e.subject) LIKE ?
                   OR lower(ifnull(e.object, '')) LIKE ?
                   OR lower(ifnull(e.location, '')) LIKE ?
                   OR lower(e.payload_json) LIKE ?
                   OR lower(ifnull(es.label, '')) LIKE ?
                   OR lower(ifnull(eo.label, '')) LIKE ?
                ORDER BY e.ts DESC LIMIT ?
                """,
                (token, token, token, token, token, token, token, token, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            item.pop("subject_label", None)
            item.pop("object_label", None)
            result.append(item)
        return result
