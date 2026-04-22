
from __future__ import annotations

from arc_lang.core.db import connect
from arc_lang.core.models import utcnow

DEFAULT_POLICIES = {
    "runtime_default_dry_run": "true",
    "allow_external_providers": "true",
    "allow_mutation_actions": "false",
    "allow_live_speech": "false",
}

TRUTHY = {"1", "true", "yes", "on"}


def _ensure_defaults() -> None:
    """Ensure default operator policies are present in the database (idempotent)."""
    with connect() as conn:
        for key, value in DEFAULT_POLICIES.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO operator_policies(policy_key, policy_value, notes, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, value, "default", utcnow()),
            )
        conn.commit()


def get_policy_snapshot() -> dict:
    """Return the current operator policy snapshot including all keys, string values, and boolean flags."""
    _ensure_defaults()
    with connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM operator_policies ORDER BY policy_key").fetchall()]
    values = {r["policy_key"]: r["policy_value"] for r in rows}
    bools = {k: str(v).strip().lower() in TRUTHY for k, v in values.items()}
    return {"ok": True, "policies": rows, "policy_values": values, "policy_flags": bools}


def get_policy_flag(policy_key: str, default: bool = False) -> bool:
    """Return a single operator policy flag as a boolean, with a default if not set."""
    snap = get_policy_snapshot()
    if policy_key not in snap["policy_values"]:
        return default
    return str(snap["policy_values"][policy_key]).strip().lower() in TRUTHY


def set_operator_policy(policy_key: str, policy_value: str, notes: str = "") -> dict:
    """Set an operator policy key-value pair."""
    _ensure_defaults()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO operator_policies(policy_key, policy_value, notes, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(policy_key) DO UPDATE SET
                policy_value=excluded.policy_value,
                notes=excluded.notes,
                updated_at=excluded.updated_at
            """,
            (policy_key, policy_value, notes, utcnow()),
        )
        conn.commit()
    return {"ok": True, "policy_key": policy_key, "policy_value": policy_value, "notes": notes}
