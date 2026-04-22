from __future__ import annotations
import json
from arc.core.db import connect
from arc.core.schemas import NoteIn, new_id, utcnow
from arc.services.audit import append_receipt


def create_note(item: NoteIn, actor_role: str) -> dict:
    note_id = new_id("note")
    with connect() as conn:
        conn.execute(
            "INSERT INTO analyst_notes (note_id, created_at, actor_role, subject_type, subject_id, title, body, tags_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (note_id, utcnow(), actor_role, item.subject_type, item.subject_id, item.title, item.body, json.dumps(item.tags, sort_keys=True)),
        )
        conn.commit()
    append_receipt("note", note_id, actor_role, {"subject_type": item.subject_type, "subject_id": item.subject_id, "title": item.title})
    return get_note(note_id)


def get_note(note_id: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM analyst_notes WHERE note_id = ?", (note_id,)).fetchone()
        if not row:
            raise KeyError(note_id)
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json"))
        return item


def list_notes(subject_type: str | None = None, subject_id: str | None = None, limit: int = 100) -> list[dict]:
    with connect() as conn:
        if subject_type and subject_id:
            rows = conn.execute("SELECT * FROM analyst_notes WHERE subject_type = ? AND subject_id = ? ORDER BY created_at DESC LIMIT ?", (subject_type, subject_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM analyst_notes ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["tags"] = json.loads(item.pop("tags_json"))
            items.append(item)
        return items
