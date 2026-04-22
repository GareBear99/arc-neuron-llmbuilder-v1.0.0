from __future__ import annotations
import base64
import hashlib
import hmac
import json
import secrets
from pathlib import Path
from arc.core.config import KEY_DIR
from arc.core.db import connect
from arc.core.schemas import new_id, utcnow

SIGNING_KEY_PATH = KEY_DIR / "receipt_signing.key"
KEY_ID = "local-hmac-v1"


def _ensure_signing_key() -> bytes:
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    if SIGNING_KEY_PATH.exists():
        return SIGNING_KEY_PATH.read_bytes()
    key = secrets.token_bytes(32)
    SIGNING_KEY_PATH.write_bytes(key)
    return key


def _encode_signature(payload: str) -> str:
    key = _ensure_signing_key()
    digest = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def log(actor_role: str, action: str, target: str, detail: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO audit_log (audit_id, ts, actor_role, action, target, detail_json) VALUES (?, ?, ?, ?, ?, ?)",
            (new_id("aud"), utcnow(), actor_role, action, target, json.dumps(detail, sort_keys=True)),
        )
        conn.commit()


def append_receipt(record_type: str, record_id: str, actor_role: str, payload: dict) -> dict:
    with connect() as conn:
        prev = conn.execute("SELECT hash FROM receipt_chain ORDER BY ts DESC, receipt_id DESC LIMIT 1").fetchone()
        prev_hash = prev["hash"] if prev else "GENESIS"
        ts = utcnow()
        payload_json = json.dumps(payload, sort_keys=True)
        chain_payload = f"{prev_hash}|{ts}|{record_type}|{record_id}|{actor_role}|{payload_json}"
        hash_value = hashlib.sha256(chain_payload.encode("utf-8")).hexdigest()
        signature = _encode_signature(chain_payload)
        receipt_id = new_id("rcp")
        conn.execute(
            "INSERT INTO receipt_chain (receipt_id, ts, record_type, record_id, actor_role, payload_json, prev_hash, hash, signature, key_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (receipt_id, ts, record_type, record_id, actor_role, payload_json, prev_hash, hash_value, signature, KEY_ID),
        )
        conn.commit()
    return {"receipt_id": receipt_id, "hash": hash_value, "signature": signature, "key_id": KEY_ID}


def list_receipts(limit: int = 100) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM receipt_chain ORDER BY ts DESC, receipt_id DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload_json"])} for r in rows]


def verify_receipt_chain(limit: int | None = None) -> dict:
    with connect() as conn:
        query = "SELECT * FROM receipt_chain ORDER BY ts ASC, receipt_id ASC"
        params = ()
        if limit:
            query += " LIMIT ?"
            params = (limit,)
        rows = conn.execute(query, params).fetchall()
    prev_hash = "GENESIS"
    checked = 0
    key = _ensure_signing_key()
    for row in rows:
        payload_json = row["payload_json"]
        chain_payload = f"{prev_hash}|{row['ts']}|{row['record_type']}|{row['record_id']}|{row['actor_role']}|{payload_json}"
        expected_hash = hashlib.sha256(chain_payload.encode("utf-8")).hexdigest()
        expected_sig = base64.b64encode(hmac.new(key, chain_payload.encode("utf-8"), hashlib.sha256).digest()).decode("ascii")
        if row["prev_hash"] != prev_hash:
            return {"ok": False, "checked": checked, "reason": "prev_hash_mismatch", "receipt_id": row["receipt_id"]}
        if row["hash"] != expected_hash:
            return {"ok": False, "checked": checked, "reason": "hash_mismatch", "receipt_id": row["receipt_id"]}
        if row["signature"] != expected_sig:
            return {"ok": False, "checked": checked, "reason": "signature_mismatch", "receipt_id": row["receipt_id"]}
        prev_hash = row["hash"]
        checked += 1
    return {"ok": True, "checked": checked, "tail": prev_hash, "key_id": KEY_ID}
