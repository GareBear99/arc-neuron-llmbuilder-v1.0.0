from __future__ import annotations
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import ManualLineageRequest, utcnow

ALLOWED_CUSTOM_STATUSES = {
    'user_asserted', 'needs_review', 'accepted_local', 'rejected', 'disputed'
}


def add_custom_lineage(req: ManualLineageRequest) -> dict:
    """Add a custom lineage assertion between two nodes."""
    now = utcnow()
    assertion_id = f"cla_{uuid.uuid4().hex[:12]}"
    status = req.status if req.status in ALLOWED_CUSTOM_STATUSES else 'user_asserted'
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO custom_lineage_assertions (
                assertion_id, src_id, dst_id, relation, confidence, disputed,
                source_name, source_ref, notes, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (assertion_id, req.src_id, req.dst_id, req.relation, req.confidence, int(req.disputed), req.source_name, req.source_ref, req.notes, status, now, now),
        )
        conn.commit()
    return {"ok": True, "assertion_id": assertion_id, "status": status}


def update_custom_lineage_status(assertion_id: str, status: str) -> dict:
    """Update the status of a custom lineage assertion (e.g., needs_review → accepted_local)."""
    if status not in ALLOWED_CUSTOM_STATUSES:
        return {"ok": False, "error": "invalid_status", "allowed_statuses": sorted(ALLOWED_CUSTOM_STATUSES)}
    now = utcnow()
    with connect() as conn:
        row = conn.execute('SELECT assertion_id FROM custom_lineage_assertions WHERE assertion_id = ?', (assertion_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "assertion_not_found", "assertion_id": assertion_id}
        conn.execute('UPDATE custom_lineage_assertions SET status = ?, updated_at = ? WHERE assertion_id = ?', (status, now, assertion_id))
        conn.commit()
    return {"ok": True, "assertion_id": assertion_id, "status": status}


def list_custom_lineage(src_id: str | None = None, dst_id: str | None = None, status: str | None = None) -> dict:
    """List custom lineage assertions, optionally filtered by src_id, dst_id, or status."""
    clauses=[]
    params=[]
    if src_id:
        clauses.append('src_id = ?')
        params.append(src_id)
    if dst_id:
        clauses.append('dst_id = ?')
        params.append(dst_id)
    if status:
        clauses.append('status = ?')
        params.append(status)
    where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    with connect() as conn:
        rows=[dict(r) for r in conn.execute(f"SELECT * FROM custom_lineage_assertions {where} ORDER BY updated_at DESC", params).fetchall()]
    return {"ok": True, "results": rows}
