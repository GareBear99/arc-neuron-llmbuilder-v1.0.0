from __future__ import annotations
import json
import uuid
from arc_lang.core.db import connect
from arc_lang.core.models import utcnow


def create_job_receipt(job_type: str, provider_name: str | None, request_payload: dict, response_payload: dict, status: str, notes: list[str] | None = None) -> dict:
    """Create and store a runtime job receipt (translation or speech request/response pair)."""
    receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO job_receipts (
                receipt_id, job_type, provider_name, status, request_payload_json,
                response_payload_json, notes_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                job_type,
                provider_name,
                status,
                json.dumps(request_payload, ensure_ascii=False),
                json.dumps(response_payload, ensure_ascii=False),
                json.dumps(notes or [], ensure_ascii=False),
                now,
            ),
        )
        conn.commit()
    return {"ok": True, "receipt_id": receipt_id, "job_type": job_type, "provider_name": provider_name, "status": status, "created_at": now}


def list_job_receipts(job_type: str | None = None, provider_name: str | None = None, limit: int = 50) -> dict:
    """List job receipts, optionally filtered by job_type and provider_name."""
    q = "SELECT receipt_id, job_type, provider_name, status, request_payload_json, response_payload_json, notes_json, created_at FROM job_receipts"
    clauses = []
    params = []
    if job_type:
        clauses.append("job_type = ?")
        params.append(job_type)
    if provider_name:
        clauses.append("provider_name = ?")
        params.append(provider_name)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    for row in rows:
        row["request_payload"] = json.loads(row.pop("request_payload_json"))
        row["response_payload"] = json.loads(row.pop("response_payload_json"))
        row["notes"] = json.loads(row.pop("notes_json"))
    return {"ok": True, "receipts": rows}
